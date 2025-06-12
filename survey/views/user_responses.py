import logging

from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect
from django.utils.decorators import method_decorator
from django.views.generic import ListView

from survey.models import Response, Survey

LOGGER = logging.getLogger(__name__)


@method_decorator(login_required, name="dispatch")
class UserResponsesView(ListView):
    """Отображает список Response пользователя для опросов с множественным прохождением"""

    model = Response
    template_name = "survey/user_responses.html"
    context_object_name = "user_responses"

    def get_queryset(self):
        self.survey = get_object_or_404(Survey, pk=self.kwargs.get("survey_id"))
        return Response.objects.filter(survey=self.survey, user=self.request.user).order_by("-created")

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["survey"] = self.survey

        return context

    def get(self, request, *args, **kwargs):
        response = super().get(request, *args, **kwargs)

        # Проверяем что опрос разрешает множественные прохождения
        if not self.survey.multiple_responses:
            # Если не разрешает, перенаправляем на обычную страницу опроса
            return redirect("survey-detail", id=self.survey.id)

        return response
