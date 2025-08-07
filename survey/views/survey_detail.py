import uuid

from django.http import Http404
from django.shortcuts import get_object_or_404
from django.shortcuts import redirect
from django.utils.translation import gettext_lazy as _
from django.views.generic import FormView

from survey.forms import SurveyIntroForm
from survey.models import Survey


class SurveyDetailView(FormView):
    """Вводная страница опроса с описанием"""

    template_name = "survey/survey_detail.html"
    form_class = SurveyIntroForm

    def dispatch(self, request, *args, **kwargs):
        self.survey = get_object_or_404(Survey, pk=self.kwargs["survey_id"])

        # Проверяем доступность опроса
        if not self.survey.is_published:
            raise Http404(_("Survey is not available"))

        if self.survey.need_logged_user and not request.user.is_authenticated:
            return redirect("login")

        return super().dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["object"] = context["survey"] = self.survey
        return context

    def form_valid(self, form):
        # Создаем новую сессию для прохождения опроса
        session_key = str(uuid.uuid4())
        self.request.session["survey_session"] = session_key
        self.request.session["survey_id"] = self.survey.id
        self.request.session["current_question"] = 0

        return redirect("survey:question-detail", survey_id=self.survey.id)
