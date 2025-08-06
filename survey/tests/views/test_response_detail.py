import pytest
from django.contrib.auth.models import AnonymousUser
from django.http import Http404
from django.test import RequestFactory
from django.urls import reverse

from survey.tests.factories import AnswerFactory
from survey.tests.factories import QuestionFactory
from survey.tests.factories import ResponseFactory
from survey.tests.factories import SurveyFactory
from survey.tests.factories import UserFactory
from survey.views import ResponseDetailView


@pytest.mark.django_db
class TestResponseDetailView:
    def setup_method(self):
        self.factory = RequestFactory()
        self.view = ResponseDetailView.as_view()

    def test_get_show_results(self):
        """Тест отображения результатов"""
        survey = SurveyFactory()
        response = ResponseFactory(survey=survey)

        request = self.factory.get(f"/survey/{survey.id}/response/{response.id}/")
        request.user = AnonymousUser()
        request.session = {}

        view_response = self.view(request, response_id=response.id, survey_id=survey.id)

        assert view_response.status_code == 200

    def test_post_redirects_to_survey_list(self):
        """Тест редиректа POST запроса на список опросов"""
        survey = SurveyFactory()
        response = ResponseFactory(survey=survey)

        request = self.factory.post(f"/survey/{survey.id}/response/{response.id}/")
        request.user = AnonymousUser()
        request.session = {}

        view_response = self.view(request, response_id=response.id, survey_id=survey.id)

        assert view_response.status_code == 302
        assert "/survey/" in view_response.url

    def test_show_results_private_survey_anonymous_user_redirects_to_login(self):
        """Тест редиректа анонимного пользователя на логин для приватного опроса"""
        survey = SurveyFactory(need_logged_user=True)
        response = ResponseFactory(survey=survey)

        request = self.factory.get(f"/survey/{survey.id}/response/{response.id}/")
        request.user = AnonymousUser()
        request.session = {}

        view_response = self.view(request, response_id=response.id, survey_id=survey.id)

        assert view_response.status_code == 302
        assert "login" in view_response.url

    def test_show_results_private_survey_authenticated_user_access(self):
        """Тест доступа аутентифицированного пользователя к приватному опросу"""
        user = UserFactory()
        survey = SurveyFactory(need_logged_user=True)
        response = ResponseFactory(survey=survey)

        request = self.factory.get(f"/survey/{survey.id}/response/{response.id}/")
        request.user = user
        request.session = {}

        view_response = self.view(request, response_id=response.id, survey_id=survey.id)

        assert view_response.status_code == 200

    def test_show_results_authenticated_user_cannot_access_other_user_response(self):
        """Тест что пользователь не может видеть ответы других пользователей"""
        user1 = UserFactory()
        user2 = UserFactory()
        survey = SurveyFactory()
        response = ResponseFactory(survey=survey, user=user1)

        request = self.factory.get(f"/survey/{survey.id}/response/{response.id}/")
        request.user = user2
        request.session = {}

        with pytest.raises(Http404):
            self.view(request, response_id=response.id, survey_id=survey.id)

    def test_show_results_authenticated_user_can_access_own_response(self):
        """Тест что пользователь может видеть свои ответы"""
        user = UserFactory()
        survey = SurveyFactory()
        response = ResponseFactory(survey=survey, user=user)

        request = self.factory.get(f"/survey/{survey.id}/response/{response.id}/")
        request.user = user
        request.session = {}

        view_response = self.view(request, response_id=response.id, survey_id=survey.id)

        assert view_response.status_code == 200

    def test_show_results_anonymous_user_can_access_anonymous_response(self):
        """Тест что анонимный пользователь может видеть анонимные ответы"""
        survey = SurveyFactory(need_logged_user=False)
        response = ResponseFactory(survey=survey, user=None)

        request = self.factory.get(f"/survey/{survey.id}/response/{response.id}/")
        request.user = AnonymousUser()
        request.session = {}

        view_response = self.view(request, response_id=response.id, survey_id=survey.id)

        assert view_response.status_code == 200

    def test_show_results_clears_session_if_active(self):
        """Тест очистки активной сессии"""
        survey = SurveyFactory()
        response = ResponseFactory(survey=survey)

        request = self.factory.get(f"/survey/{survey.id}/response/{response.id}/")
        request.user = AnonymousUser()
        request.session = {"survey_session": "active-session", "survey_id": survey.id, "current_question": 1}

        view_response = self.view(request, response_id=response.id, survey_id=survey.id)

        assert view_response.status_code == 200
        # Проверяем что сессия очищена
        assert "survey_session" not in request.session
        assert "survey_id" not in request.session
        assert "current_question" not in request.session

    def test_build_results_context(self):
        """Тест построения контекста результатов"""
        survey = SurveyFactory()
        response = ResponseFactory(survey=survey)
        question = QuestionFactory(survey=survey, order=1, correct_answer="Правильный ответ")
        AnswerFactory(question=question, response=response, body="Ответ пользователя")

        request = self.factory.get(f"/survey/{survey.id}/response/{response.id}/")
        request.user = AnonymousUser()
        request.session = {}

        view = ResponseDetailView()
        view.request = request

        context = view._build_results_context(survey, response)

        assert context["survey"] == survey
        assert context["response"] == response
        assert "answers_data" in context
        assert context["correct_answers"] == 0  # Ответ неправильный
        assert context["correct_percentage"] == 0

    def test_build_results_context_with_correct_answer(self):
        """Тест контекста с правильным ответом"""
        survey = SurveyFactory()
        response = ResponseFactory(survey=survey)
        question = QuestionFactory(survey=survey, order=1, correct_answer="Правильный ответ")
        AnswerFactory(question=question, response=response, body="Правильный ответ")

        request = self.factory.get(f"/survey/{survey.id}/response/{response.id}/")
        request.user = AnonymousUser()
        request.session = {}

        view = ResponseDetailView()
        view.request = request

        context = view._build_results_context(survey, response)

        assert context["correct_answers"] == 1
        assert context["correct_percentage"] == 100

    def test_build_results_context_multiple_questions(self):
        """Тест контекста с несколькими вопросами"""
        survey = SurveyFactory()
        response = ResponseFactory(survey=survey)
        question1 = QuestionFactory(survey=survey, order=1, correct_answer="Ответ 1")
        question2 = QuestionFactory(survey=survey, order=2, correct_answer="Ответ 2")
        AnswerFactory(question=question1, response=response, body="Ответ 1")  # Правильный
        AnswerFactory(question=question2, response=response, body="Неправильный")  # Неправильный

        request = self.factory.get(f"/survey/{survey.id}/response/{response.id}/")
        request.user = AnonymousUser()
        request.session = {}

        view = ResponseDetailView()
        view.request = request

        context = view._build_results_context(survey, response)

        assert context["correct_answers"] == 1
        assert context["correct_percentage"] == 50

    def test_clear_session(self):
        """Тест очистки сессии"""
        request = self.factory.get("/")
        request.session = {
            "survey_session": "test-session",
            "survey_id": 1,
            "current_question": 0,
            "other_data": "should_remain",
        }

        view = ResponseDetailView()
        view._clear_session(request)

        # Проверяем что ключи сессии опроса удалены
        assert "survey_session" not in request.session
        assert "survey_id" not in request.session
        assert "current_question" not in request.session
        # Проверяем что другие данные остались
        assert "other_data" in request.session

    def test_view_with_client(self, client):
        """Тест вьюхи через клиент"""
        survey = SurveyFactory()
        response = ResponseFactory(survey=survey)

        view_response = client.get(
            reverse("survey:response-detail", kwargs={"response_id": response.id, "survey_id": survey.id})
        )

        assert view_response.status_code == 200

    def test_view_template_used(self, client):
        """Тест использования правильного шаблона"""
        survey = SurveyFactory()
        response = ResponseFactory(survey=survey)

        view_response = client.get(
            reverse("survey:response-detail", kwargs={"response_id": response.id, "survey_id": survey.id})
        )

        assert "survey/response_detail.html" in [t.name for t in view_response.templates]

    def test_nonexistent_response_raises_404(self, client):
        """Тест 404 для несуществующего ответа"""
        survey = SurveyFactory()

        response = client.get(reverse("survey:response-detail", kwargs={"response_id": 99999, "survey_id": survey.id}))

        assert response.status_code == 404

    def test_response_wrong_survey_raises_404(self, client):
        """Тест 404 для ответа с неправильным опросом"""
        survey1 = SurveyFactory()
        survey2 = SurveyFactory()
        response = ResponseFactory(survey=survey1)

        response_view = client.get(
            reverse("survey:response-detail", kwargs={"response_id": response.id, "survey_id": survey2.id})
        )

        assert response_view.status_code == 404
