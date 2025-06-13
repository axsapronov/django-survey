
from django.utils import timezone

from django.views.generic import ListView

from survey.models import Survey


class SurveyListView(ListView):
    model = Survey

    def get_queryset(self):
        queryset = Survey.objects.filter(
            is_published=True,
            expire_date__gte=timezone.now().date(),
            publish_date__lte=timezone.now().date(),
        )
        if not self.request.user.is_authenticated:
            queryset = queryset.filter(need_logged_user=False)
        return queryset
