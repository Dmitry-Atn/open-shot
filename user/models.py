import urllib, hashlib, datetime
# Django imports
from django.db import models
from django.contrib.auth.models import User
from django.contrib.sites.models import Site
from django.contrib.sites.managers import CurrentSiteManager
from django.utils.functional import cached_property
from django.utils.translation import ugettext as _
from django.core.urlresolvers import reverse
# Friends' apps
from actstream.models import Follow
# Project's apps
from entities.models import Entity
from user.utils import create_avatar
from polyorg.models import Candidate, CandidateList

NOTIFICATION_PERIOD_CHOICES = (
    (u'N', _('No Email')),
    (u'D', _('Daily')),
    (u'W', _('Weekly')),
)
GENDER_CHOICES = (
    (u'M', _('Male')),
    (u'F', _('Female')),
)
VERIFICATION_STAGES = (
    (u'0', 'No verification needed'),
    (u'S', 'Verification process started'),
    (u'V', 'Verified'),
)


NEVER_SENT = datetime.datetime(1970,8,6)
MIN_EDITORS_PER_LOCALITY = 3

class ProfileManager(models.Manager):

    def need_editors(self, entity):
       return entity.profiles.count() < MIN_EDITORS_PER_LOCALITY


class Profile(models.Model):
    user = models.OneToOneField(User, related_name='profile')
    public_profile = models.BooleanField(default=True)
    gender = models.CharField(max_length=1, choices=GENDER_CHOICES, blank=True, null=True)
    bio = models.TextField(null=True,blank=True)
    description = lambda self: self.bio
    email_notification = models.CharField(max_length=1, choices=NOTIFICATION_PERIOD_CHOICES, blank=True, null=True, default='D')
    avatar_uri = models.URLField(null=True, blank=True)
    last_email_update = models.DateTimeField(default=NEVER_SENT)
    sites = models.ManyToManyField(Site)
    verification = models.CharField(max_length=1, choices=VERIFICATION_STAGES, default='0')
    on_site = CurrentSiteManager()

    objects = ProfileManager()

    def __unicode__(self):
        return self.user.get_full_name()

    @property
    def following(self):
        return map(lambda x: x.actor,
            Follow.objects.filter(user=self.user).prefetch_related('actor')
                  )

    def get_absolute_url(self):
        return reverse('public-profile', args=(self.user.username, ))

    def get_full_name(self):
        return self.user.get_full_name() or self.user.username

    @property
    def entities(self):
        try:
            return self.user.membership_set.values_list('entity', flat=True)
        except DoesNotExist: # does not have a locality set
            return None

    def is_candidate(self, entity):
        return self.user.candidate_set.filter(entity=entity).exists()

    @property
    def candidate_in(self):
        return self.user.candidate_set.values_list('entity', flat=True)

    def is_editor(self, entity):
        return self.user.membership_set(entity=entity, is_editor=True).exists()

    @property
    def editor_in(self):
        return self.user.membership_set.filter(is_editor=True).values_list('entity', flat=True)

    @cached_property
    def is_mayor_candidate(self):
        try:
            return Candidate.objects.only('for_mayor').get(user=self.user).for_mayor
        except:
            return False

    @cached_property
    def candidate_list(self):
        try:
            return Candidate.objects.only('candidate_list').get(user=self.user).candidate_list
        except:
            return None

    @cached_property
    def locality(self):
        try:
            return self.user.membership_set.get(entity__division__index=3).entity
        except DoesNotExist: # does not have a locality set
            return None

    def add_entity(self, entity, is_editor=False):
        Membership.objects.create(user=self.user, entity=entity, is_editor=is_editor)


class Membership(models.Model):
    user = models.ForeignKey(User)
    entity = models.ForeignKey(Entity)
    is_editor = models.BooleanField(default=False)
    can_answer = models.BooleanField(default=False)
    member_of = models.ForeignKey(CandidateList, null=True, blank=True)
