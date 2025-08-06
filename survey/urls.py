from django.urls import path
from django.urls import re_path

from survey.views import ConfirmView
from survey.views import ResponseDetail
from survey.views import SurveyCompleted
from survey.views import SurveyDetail
from survey.views import SurveyListView
from survey.views import UserResponsesView

urlpatterns = [
    path("", SurveyListView.as_view(), name="survey-list"),
    path(
        "<int:id>/",
        SurveyDetail.as_view(),
        name="survey-detail",
    ),
    re_path(
        r"^(?P<id>\d+)/completed/",
        SurveyCompleted.as_view(),
        name="survey-completed",
    ),
    re_path(
        r"^(?P<id>\d+)-(?P<step>\d+)/",
        SurveyDetail.as_view(),
        name="survey-detail-step",
    ),
    path(
        "<int:survey_id>/responses/",
        UserResponsesView.as_view(),
        name="survey-user-responses",
    ),
    re_path(
        r"^response/(?P<response_id>\d+)/",
        ResponseDetail.as_view(),
        name="survey-response-detail",
    ),
    re_path(
        r"^response/(?P<response_id>\d+)-(?P<step>\d+)/",
        ResponseDetail.as_view(),
        name="survey-response-detail-step",
    ),
    re_path(
        r"^confirm/(?P<uuid>\w+)/",
        ConfirmView.as_view(),
        name="survey-confirmation",
    ),
]
