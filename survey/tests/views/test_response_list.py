import pytest
from django.test import RequestFactory
from django.urls import reverse

from survey.tests.factories import ResponseFactory
from survey.tests.factories import SurveyFactory
from survey.tests.factories import UserFactory
from survey.views import ResponseListView


@pytest.mark.django_db
class TestResponseListView:
    def setup_method(self):
        self.factory = RequestFactory()
        self.view = ResponseListView.as_view()

    def test_get_queryset_user_responses(self):
        """Тест получения ответов пользователя"""
        user = UserFactory()
        survey = SurveyFactory()
        user_response = ResponseFactory(survey=survey, user=user)
        other_user_response = ResponseFactory(survey=survey, user=UserFactory())

        request = self.factory.get(f"/survey/{survey.id}/responses/")
        request.user = user

        view = ResponseListView()
        view.request = request
        view.survey = survey
        view.kwargs = {"survey_id": survey.id}

        queryset = view.get_queryset()

        assert user_response in queryset
        assert other_user_response not in queryset
        assert queryset.count() == 1

    def test_get_queryset_ordered_by_created_desc(self):
        """Тест сортировки ответов по дате создания (новые сначала)"""
        user = UserFactory()
        survey = SurveyFactory()
        old_response = ResponseFactory(survey=survey, user=user)
        new_response = ResponseFactory(survey=survey, user=user)

        request = self.factory.get(f"/survey/{survey.id}/responses/")
        request.user = user

        view = ResponseListView()
        view.request = request
        view.survey = survey
        view.kwargs = {"survey_id": survey.id}

        queryset = view.get_queryset()

        assert list(queryset) == [new_response, old_response]

    def test_get_context_data(self):
        """Тест контекста страницы"""
        user = UserFactory()
        survey = SurveyFactory()

        request = self.factory.get(f"/survey/{survey.id}/responses/")
        request.user = user

        view = ResponseListView()
        view.request = request
        view.survey = survey
        view.object_list = []

        context = view.get_context_data()

        assert context["survey"] == survey
        assert "object_list" in context

    def test_get_with_multiple_responses_allowed(self):
        """Тест доступа к странице когда множественные ответы разрешены"""
        user = UserFactory()
        survey = SurveyFactory(multiple_responses=True)

        request = self.factory.get(f"/survey/{survey.id}/responses/")
        request.user = user

        response = self.view(request, survey_id=survey.id)

        assert response.status_code == 200

    def test_view_with_client_authenticated_user(self, client):
        """Тест вьюхи через клиент для аутентифицированного пользователя"""
        user = UserFactory()
        survey = SurveyFactory(multiple_responses=True)

        client.force_login(user)
        response = client.get(reverse("survey:response-list", kwargs={"survey_id": survey.id}))

        assert response.status_code == 200

    def test_view_with_client_anonymous_user_redirects_to_login(self, client):
        """Тест редиректа анонимного пользователя на логин"""
        survey = SurveyFactory(multiple_responses=True)

        response = client.get(reverse("survey:response-list", kwargs={"survey_id": survey.id}))

        assert response.status_code == 302
        assert "login" in response.url

    def test_view_template_used(self, client):
        """Тест использования правильного шаблона"""
        user = UserFactory()
        survey = SurveyFactory(multiple_responses=True)

        client.force_login(user)
        response = client.get(reverse("survey:response-list", kwargs={"survey_id": survey.id}))

        assert "survey/response_list.html" in [t.name for t in response.templates]

    def test_nonexistent_survey_raises_404(self, client):
        """Тест 404 для несуществующего опроса"""
        user = UserFactory()
        client.force_login(user)

        response = client.get(reverse("survey:response-list", kwargs={"survey_id": 99999}))
        assert response.status_code == 404

    def test_user_sees_only_own_responses(self, client):
        """Тест что пользователь видит только свои ответы"""
        user1 = UserFactory()
        user2 = UserFactory()
        survey = SurveyFactory(multiple_responses=True)

        # Создаем ответы для разных пользователей
        response1 = ResponseFactory(survey=survey, user=user1)
        response2 = ResponseFactory(survey=survey, user=user2)

        client.force_login(user1)
        response = client.get(reverse("survey:response-list", kwargs={"survey_id": survey.id}))

        assert response.status_code == 200
        # Проверяем что в контексте только ответы user1
        assert response1 in response.context["object_list"]
        assert response2 not in response.context["object_list"]

    def test_post_request_not_allowed(self, client):
        """Тест что POST запросы не поддерживаются"""
        user = UserFactory()
        survey = SurveyFactory(multiple_responses=True)

        client.force_login(user)
        response = client.post(reverse("survey:response-list", kwargs={"survey_id": survey.id}))

        assert response.status_code == 405  # Method Not Allowed
