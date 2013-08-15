from django.conf import settings
from django.contrib.auth.models import User, AnonymousUser, Permission
from django.contrib.sites.models import Site
from social_auth.tests.client import SocialClient
from django.test.client import Client
from django.core.urlresolvers import reverse

from django.test import TestCase

from entities.models import Domain, Division, Entity
from .models import *

class UserTest(TestCase):
    user = {
        'first_name': 'Django',
        'last_name': 'Reinhardt',
        'verified': True,
        'name': 'Django Reinhardt',
        'locale': 'en_US',
        'hometown': {
            'id': '12345678',
            'name': 'Any Town, Any State'
        },
        'expires': '4812',
        'updated_time': '2012-01-29T19:27:32+0000',
        'access_token': 'dummyToken',
        'link': 'http://www.facebook.com/profile.php?id=1234',
        'location': {
            'id': '108659242498155',
            'name': 'Chicago, Illinois'
        },
        'gender': 'male',
        'timezone': -6,
        'id': '1234',
        'email': 'user@domain.com'
    }
    def setUp(self):
        domain = Domain.objects.create(name="test")
        division = Division.objects.create(name="localities", domain=domain)
        self.entity = Entity.objects.create(name="the moon", division=division)
        self.user = User.objects.create_user("user",
                                "user@example.com", "pass")
        self.user.profile.locality = self.entity
        self.user.profile.save()
        self.candidate = User.objects.create_user("candidate",
                                "candidate@example.com", "pass")
        self.candidate.profile.locality = self.entity
        self.candidate.profile.is_candidate = True
        self.candidate.profile.save()

    def test_remove_candidate(self):
        c = Client()
        rc_url = reverse('remove_candidate', args=(self.candidate.id, ))
        response  = c.post(rc_url)
        self.assertRedirects(response, "%s?next=%s"  % (reverse("login"), rc_url))
        self.assertTrue(self.candidate.profile.is_candidate)
        self.assertTrue(c.login(username="user", password="pass"))
        response  = c.post(rc_url)
        self.assertRedirects(response, reverse("candidate_list", args=(self.entity.slug,)))
        self.assertIn('messages', response.cookies.keys())
        self.user.profile.is_editor = True
        self.user.profile.save()
        response  = c.post(rc_url)
        self.assertRedirects(response, reverse("candidate_list", args=(self.entity.slug,)))
        profile = User.objects.get(pk=self.candidate.id).profile
        self.assertFalse(profile.is_candidate)
        profile.is_candidate = True
        profile.save()

    def test_edit_profile(self):
        c = Client()
        clist_url = reverse('edit_profile')
        response = c.get(clist_url)
        self.assertEquals(response.status_code, 302)
        self.assertTrue(c.login(username="user", password="pass"))
        response = c.get(clist_url)
        self.assertEquals(response.status_code, 200)
        self.assertEquals(response.context['base_template'], 'place_base.html')
        self.user.profile.locality = None
        self.user.profile.save()
        response = c.get(clist_url)
        self.assertEquals(response.status_code, 200)
        self.assertEquals(response.context['base_template'], 'base.html')
        self.user.profile.locality = self.entity
        self.user.profile.save()

    def test_avatar(self):
        avatar_url = self.user.profile.avatar_url()
        self.assertTrue(avatar_url.startswith('http://www.gravatar.com/avatar/'))
        self.user.profile.avatar_uri = 'http://myavatar.com'
        self.user.profile.save()
        avatar_url = self.user.profile.avatar_url()
        self.assertEquals(avatar_url, 'http://myavatar.com')

    def test_candidate_list(self):
        c = Client()
        clist_url = reverse('candidate_list', kwargs={'entity_slug':self.entity.slug})
        response = c.get(clist_url)
        self.assertEquals(response.status_code, 200)
        self.assertTemplateUsed(response, "candidate/candidate_list.html")
        self.assertEquals(len(response.context['candidates']), 1)
        self.user.profile.is_candidate = True
        self.user.profile.save()
        response = c.get(clist_url)
        self.assertEquals(len(response.context['candidates']), 2)
        self.user.profile.is_candidate = False
        self.user.profile.save()
        response = c.get(clist_url)
        self.assertEquals(len(response.context['candidates']), 1)

    def test_user_detail(self):
        c = Client()
        response = c.get(reverse('user_detail', kwargs={'username': "user"}))
        self.assertEquals(response.status_code, 200)
        self.assertEquals(response.context['entity'], self.entity)
        self.assertTemplateUsed(response, "user/user_detail.html")

    # TODO: remove the invitation
    '''
    def test_invitation(self):
        user = invite_user(username = "john",
                            email = "john@example.com",
                            first_name = "John",
                            last_name = "Doe",
                            site = Site.objects.get(pk=settings.SITE_ID)
                            )
        user = User.objects.get(username = "john")
        self.assertEquals(user.email, "john@example.com")
        self.assertEquals(user.get_full_name(), "John Doe")
        reg_profile = user.registrationprofile_set.all()
        self.assertEquals(reg_profile.count(), 1)
        reg_profile = reg_profile[0]
        c = Client()
        response = c.get(reverse('accept-invitation', kwargs={'invitation_key': reg_profile.activation_key}))
        self.assertEquals(response.status_code, 200)
        response = c.post(reverse('accept-invitation',
            kwargs={'invitation_key': reg_profile.activation_key}), 
            )
        self.assertFormError(response, "form", None, None)
        self.assertFormError(response, "form", "password1", None)
    '''

    def tearDown(self):
        User.objects.all().delete()
