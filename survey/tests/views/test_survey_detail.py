import pytest
from django.contrib.auth.models import AnonymousUser
from django.http import Http404
from django.test import RequestFactory
from django.urls import reverse

from survey.tests.factories import SurveyFactory
from survey.tests.factories import UserFactory
from survey.views import SurveyDetailView


@pytest.mark.django_db
class TestSurveyDetailView:
    def setup_method(self):
        self.factory = RequestFactory()
        self.view = SurveyDetailView.as_view()

    def test_dispatch_published_survey(self):
        """Тест доступа к опубликованному опросу"""
        survey = SurveyFactory(is_published=True, need_logged_user=False)

        request = self.factory.get(f"/survey/{survey.id}/")
        request.user = AnonymousUser()

        response = self.view(request, survey_id=survey.id)

        assert response.status_code == 200

    def test_dispatch_unpublished_survey_raises_404(self):
        """Тест что неопубликованный опрос вызывает 404"""
        survey = SurveyFactory(is_published=False, need_logged_user=False)

        request = self.factory.get(f"/survey/{survey.id}/")
        request.user = AnonymousUser()

        with pytest.raises(Http404):
            self.view(request, survey_id=survey.id)

    def test_dispatch_private_survey_anonymous_user_redirects_to_login(self):
        """Тест редиректа анонимного пользователя на логин для приватного опроса"""
        survey = SurveyFactory(is_published=True, need_logged_user=True)

        request = self.factory.get(f"/survey/{survey.id}/")
        request.user = AnonymousUser()

        response = self.view(request, survey_id=survey.id)

        assert response.status_code == 302
        assert "login" in response.url

    def test_dispatch_private_survey_authenticated_user_access(self):
        """Тест доступа аутентифицированного пользователя к приватному опросу"""
        user = UserFactory()
        survey = SurveyFactory(is_published=True, need_logged_user=True)

        request = self.factory.get(f"/survey/{survey.id}/")
        request.user = user

        response = self.view(request, survey_id=survey.id)

        assert response.status_code == 200

    def test_get_context_data(self):
        """Тест контекста страницы"""
        survey = SurveyFactory(is_published=True, need_logged_user=False)

        request = self.factory.get(f"/survey/{survey.id}/")
        request.user = AnonymousUser()

        view = SurveyDetailView()
        view.request = request
        view.survey = survey

        context = view.get_context_data()

        assert context["survey"] == survey

    def test_form_valid_creates_session_and_redirects(self):
        """Тест создания сессии при валидной форме"""
        survey = SurveyFactory(is_published=True, need_logged_user=False)

        request = self.factory.post(f"/survey/{survey.id}/", {"start_survey": "true"})
        request.user = AnonymousUser()
        request.session = {}

        response = self.view(request, survey_id=survey.id)

        assert response.status_code == 302
        assert "survey_session" in request.session
        assert "survey_id" in request.session
        assert "current_question" in request.session
        assert request.session["survey_id"] == survey.id
        assert request.session["current_question"] == 0

    def test_view_with_client(self, client):
        """Тест вьюхи через клиент"""
        survey = SurveyFactory(is_published=True, need_logged_user=False)

        response = client.get(reverse("survey:survey-detail", kwargs={"survey_id": survey.id}))
        assert response.status_code == 200

    def test_view_template_used(self, client):
        """Тест использования правильного шаблона"""
        survey = SurveyFactory(is_published=True, need_logged_user=False)

        response = client.get(reverse("survey:survey-detail", kwargs={"survey_id": survey.id}))
        assert "survey/survey_detail.html" in [t.name for t in response.templates]

    def test_nonexistent_survey_raises_404(self, client):
        """Тест 404 для несуществующего опроса"""
        response = client.get(reverse("survey:survey-detail", kwargs={"survey_id": 99999}))
        assert response.status_code == 404
