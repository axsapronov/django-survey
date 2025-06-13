try:
    from django.conf.urls import url
except ImportError:
    # Django 4.0 replaced url by something else
    # See https://stackoverflow.com/a/70319607/2519059
    from django.urls import re_path as url

from survey.views import ConfirmView, ResponseDetail, SurveyCompleted, SurveyDetail, SurveyListView, UserResponsesView
from survey.views.survey_result import serve_result_csv

urlpatterns = [
    url(r"^$", SurveyListView.as_view(), name="survey-list"),
    url(r"^(?P<id>\d+)/$", SurveyDetail.as_view(), name="survey-detail"),
    url(r"^csv/(?P<primary_key>\d+)/", serve_result_csv, name="survey-result"),
    url(r"^(?P<id>\d+)/completed/", SurveyCompleted.as_view(), name="survey-completed"),
    url(r"^(?P<id>\d+)-(?P<step>\d+)/", SurveyDetail.as_view(), name="survey-detail-step"),
    url(r"^(?P<survey_id>\d+)/responses/$", UserResponsesView.as_view(), name="survey-user-responses"),
    url(r"^response/(?P<response_id>\d+)/", ResponseDetail.as_view(), name="survey-response-detail"),
    url(r"^response/(?P<response_id>\d+)-(?P<step>\d+)/", ResponseDetail.as_view(), name="survey-response-detail-step"),
    url(r"^confirm/(?P<uuid>\w+)/", ConfirmView.as_view(), name="survey-confirmation"),
]
