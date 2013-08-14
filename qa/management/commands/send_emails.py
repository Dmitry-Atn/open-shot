# -*- coding: utf-8 -*-
import urlparse
from datetime import datetime,timedelta
import re

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from django.contrib.auth.models import User
from django.core.mail import EmailMultiAlternatives
from django.utils.html import strip_tags
from django.template.loader import render_to_string
from django.utils import translation
from django.utils.translation import ugettext as _
from django.core.urlresolvers import reverse

from flatblocks.models import FlatBlock

from user.models import invite_user
from qa.models import Question
from user.models import Profile, NEVER_SENT
from oshot.utils import get_root_url

class Command(BaseCommand):
    args = '[username1 username2 ...]'
    help = 'send email updates to users that want it'

    diffs = dict(D=timedelta(0, 23*3600),
                 W=timedelta(0, (23+6*24)*3600))

    fresh_content_re = re.compile("(new-content)|(updated-content)")

    def handle (self, *args, **options):
        translation.activate(settings.LANGUAGE_CODE)
        now = datetime.now()
        self.stdout.write("> sending updates at %s" % now)
        if len(args):
            qs = Profile.on_site.filter(user__email=args)
        else:
            qs = Profile.on_site.all()
        # TODO: get only new questions and questions with new answers
        context = {'questions': Question.on_site.all().order_by('-updated_at'),
                   'header': "Hello there!",
                   'ROOT_URL': get_root_url(),
                   }
        for profile in qs:
            user = profile.user
            last_sent = profile.last_email_update
            try:
                freq = self.diffs[user.profile.email_notification]
            except KeyError:
                continue

            if not user.is_active:
                ''' send an invitation email '''
                reg_profile = user.registrationprofile_set.all()[0]
                if reg_profile.activation_key_expired() and last_sent==NEVER_SENT:
                    key = reg_profile.activation_key
                    context['key'] = key
                    context['activation_url'] = root_url + reverse('accept-invitation', args=(key,))
                    # reset the key duration, giving the user more time
                    user.date_joined = now
                    user.save()
                else:
                    continue
            elif now-last_sent < freq:
                # don't exceed the frequency!
                continue

            context['is_active'] = user.is_active
            context['last_sent'] = last_sent
            context['header'] = "email.update_header"
            context['footer'] = 'email.footer'
            html_content = render_to_string("qa/email_update.html", context)
            ''' send the email only when there's fresh content '''
            fresh_content = self.fresh_content_re.search(html_content)
            if not fresh_content:
                self.stdout.write("--- nothing fresh for %(username)s at %(email)s is_active=%(is_active)s" % user.__dict__)
                continue

            subject = '%s | %s' % (site.name,
                    FlatBlock.objects.get(slug="email.update_header").header.rstrip())
            # TODO: create a link for the update and send it to shaib
            text_content = 'Sorry, we only support html based email'
            # create the email, and attach the HTML version as well.
            msg = EmailMultiAlternatives(subject, text_content,
                    settings.DEFAULT_FROM_EMAIL, [user.email])
            msg.attach_alternative(html_content, "text/html")
            msg.send()
            self.stdout.write(">>> sent update to %(username)s at %(email)s is_active=%(is_active)s" % user.__dict__)
            profile.last_email_update = now
            profile.save()
