from django.apps import AppConfig
from django.utils.translation import gettext_lazy as _


class DjangoSurveyAndReportConfig(AppConfig):
    name = "survey"
    label = "survey"
    verbose_name = _("Survey")
