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

from .forms import *
from .models import *

def candidate_list(request):
    """
    list candidates ordered by number of answers
    """
    candidates = Profile.objects.candidates()
    return render(request, "user/candidate_list.html", {"candidates": candidates})

def user_detail(request, slug):
    user = get_object_or_404(User, username=slug)
    questions = user.questions.all()
    answers = user.answers.all()
    profile = user.profile
    user.avatar_url = profile.avatar_url()
    user.bio = profile.bio
    user.url = profile.url

    # todo: support members as well as candidates
    return render(request, "user/candidate_detail.html", 
            {"candidate": user, "answers": answers, "questions": questions})

@login_required
def edit_profile(request):
    profile = request.user.profile
    if request.method == "POST":
        form = ProfileForm(request.user, data=request.POST)
        if form.is_valid():
            user = form.save()
            return HttpResponseRedirect(user.get_absolute_url())
    elif request.method == "GET":
        user = request.user
        form = ProfileForm(request.user)
        ''' initial = {
                    'username': user.username,
                    'email': user.email,
                    'first_name': user.first_name,
                    'last_name': user.last_name,
                    'bio': user.profile.bio,
                    'email_notification': user.profile.email_notification,
                    'url': user.profile.url,
                    'avatar_uri': user.profile.avatar_url(),
                    })
        '''

    return render(request, "user/edit_profile.html", {"form": form})

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
            return self.form_valid(form)
        else:
            return self.form_invalid(form)

    def form_valid(self, form):
        form.save()
        return HttpResponseRedirect(reverse('login'))

