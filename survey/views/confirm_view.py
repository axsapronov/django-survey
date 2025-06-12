from django.views.generic import DetailView

from survey.models import Response


class ConfirmView(DetailView):
    model = Response
    template_name = "survey/confirm.html"
    slug_field = "interview_uuid"
    slug_url_kwarg = "uuid"
    context_object_name = "response"

    # TODO - оптимизировать запросы к базе данных

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        return context
