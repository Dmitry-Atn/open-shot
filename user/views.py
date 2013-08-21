from django.http import HttpResponse, HttpResponseForbidden, HttpResponseBadRequest, HttpResponseRedirect
from django.shortcuts import render, get_object_or_404
from django.core.urlresolvers import reverse
from django.contrib.auth.models import User
from django.contrib.auth.forms import AuthenticationForm
from django.contrib.auth import login as auth_login, logout as auth_logout, authenticate
from django.contrib.auth.decorators import login_required
from django.utils.translation import ugettext as _
from django.contrib import messages
from django.views.generic.edit import FormMixin, TemplateResponseMixin
from django.views.generic import View
from django.template.context import RequestContext
from django.views.decorators.http import require_POST

from .forms import *
from .models import *

from oshot.forms import EntityChoiceForm


def candidate_list(request, entity_slug=None, entity_id=None):
    """
    list candidates ordered by number of answers
    """
    if entity_id:
        entity = Entity.objects.get(pk=entity_id)
    elif entity_slug:
        entity = Entity.objects.get(slug=entity_slug)
    else:
        entity = None

    candidates = Profile.objects.get_candidates(entity).order_by('?')
    context = RequestContext(request, {'entity': entity,
                              'candidates': candidates,
                              })

    return render(request, "candidate/candidate_list.html", context)


def user_detail(request, username):
    user = get_object_or_404(User, username=username)
    questions = user.questions.all()
    answers = user.answers.all()
    profile = user.profile
    user.avatar_url = profile.avatar_url()
    user.bio = profile.bio
    user.url = profile.url
    entity_form = EntityChoiceForm(initial={'entity': profile.locality.id},
                                   auto_id=False)
    context = RequestContext(request, {"candidate": user,
                                       "answers": answers,
                                       "questions": questions,
                                       "entity": profile.locality,
                                       "base_template": get_base_template(profile),
                                       "entity_form": entity_form,
                                       })

    # todo: support members as well as candidates
    return render(request, "user/user_detail.html", context)

def get_base_template(profile):
    if profile.locality:
        return "place_base.html"
    else:
        return "base.html"


@login_required
@require_POST
def remove_candidate(request, candidate_id):
    profile = request.user.profile
    candidate_profile = get_object_or_404(User, pk=candidate_id).profile
    if profile.is_editor and profile.locality == candidate_profile.locality:
        candidate_profile.is_candidate = False
        candidate_profile.save()
    else:
        messages.error(request,
                       _('Sorry, you are not authorized to remove %s from the candidate list') \
                       % profile.user.get_full_name())

    return HttpResponseRedirect(request.POST.get("next", reverse("candidate_list", args=(profile.locality.slug,))))


@login_required
def edit_profile(request):
    profile = request.user.profile
    if request.method == "POST":
        form = ProfileForm(request.user, data=request.POST)
        if form.is_valid():
            user = form.save()

            local_home = reverse('qna',
                                 kwargs={'entity_id': user.profile.locality.id})
            next = request.POST.get('next', local_home)
            if next == '/':
                next = local_home

            return HttpResponseRedirect(next)
    elif request.method == "GET":
        user = request.user
        form = ProfileForm(request.user)

    context = RequestContext(request, {"form": form,
                                       "entity": profile.locality,
                                       "base_template": get_base_template(profile),
                                       })
    return render(request, "user/edit_profile.html", context)


class InvitationView(View, FormMixin, TemplateResponseMixin):
    template_name = 'user/accept_invitation.html'
    form_class = InvitationForm
    success_url = '/'

    @classmethod
    def get_user(self, invitation_key):
        return RegistrationProfile.objects.get(activation_key=invitation_key).user

    def get(self, request, invitation_key, **kwargs):
        user = self.get_user(invitation_key)
        if user:
            context = self.get_context_data(
                user=user,
                form=self.form_class(user),
            )
            return self.render_to_response(context)
        else:
            # TODO: add a nice message about an expired key
            return HttpResponseForbidden()

    def post(self, request, invitation_key, **kwargs):
        """
        Handles POST requests, instantiating a form instance with the passed
        POST variables and then checked for validity.
        """
        user = self.get_user(invitation_key)
        form_class = self.get_form_class()
        form = form_class(user, data=request.POST)
        if form.is_valid():
            user = RegistrationProfile.objects.activate_user(invitation_key)
            messages.success(request, _('Your profile has been updated, please login.'))
            return self.form_valid(form)
        else:
            return self.form_invalid(form)

    def form_valid(self, form):
        form.save()
        return HttpResponseRedirect(reverse('login'))

