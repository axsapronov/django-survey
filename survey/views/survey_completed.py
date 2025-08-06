from django.conf import settings
from django.shortcuts import redirect
from django.views.generic import TemplateView

from survey.decorators import survey_available


class SurveyCompleted(TemplateView):
    template_name = "survey/completed.html"

    @survey_available
    def get(self, request, *args, **kwargs):
        """GET запрос - проверяем аутентификацию и отображаем страницу"""
        survey = kwargs.get("survey")

        if survey.need_logged_user and not request.user.is_authenticated:
            return redirect(f"{settings.LOGIN_URL}?next={request.path}")

        return super().get(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = {}
        survey = kwargs.get("survey")
        context["survey"] = survey
        return context
