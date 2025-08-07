import logging

from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404
from django.utils.decorators import method_decorator
from django.views.generic import ListView

from survey.models import Response
from survey.models import Survey

LOGGER = logging.getLogger(__name__)


@method_decorator(login_required, name="dispatch")
class ResponseListView(ListView):
    """Отображает список Response пользователя для опросов с множественным прохождением"""

    model = Response

    def get_queryset(self):
        self.survey = get_object_or_404(Survey, pk=self.kwargs.get("survey_id"))
        return Response.objects.filter(
            survey=self.survey,
            user=self.request.user,
        )

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["survey"] = self.survey
        return context
