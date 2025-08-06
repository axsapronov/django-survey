from django.urls import path

from survey.views import ResponseDetailView
from survey.views import ResponseListView
from survey.views import SurveyDetailView
from survey.views import SurveyListView
from survey.views.question_detail import QuestionDetailView

app_name = "survey"
urlpatterns = [
    path("", SurveyListView.as_view(), name="survey-list"),
    path("<int:survey_id>/", SurveyDetailView.as_view(), name="survey-detail"),
    path("<int:survey_id>/question/", QuestionDetailView.as_view(), name="question-detail"),
    path("<int:survey_id>/response/", ResponseListView.as_view(), name="response-list"),
    path("<int:survey_id>/response/<int:response_id>/", ResponseDetailView.as_view(), name="response-detail"),
]
