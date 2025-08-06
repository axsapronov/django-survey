import pytest
from django.contrib.auth.models import AnonymousUser
from django.test import RequestFactory
from django.urls import reverse
from django.utils import timezone

from survey.tests.factories import SurveyFactory
from survey.tests.factories import UserFactory
from survey.views import SurveyListView


@pytest.mark.django_db
class TestSurveyListView:
    def setup_method(self):
        self.factory = RequestFactory()
        self.view = SurveyListView.as_view()

    def test_get_queryset_published_surveys(self):
        """Тест получения опубликованных опросов"""
        # Создаем опубликованный опрос
        survey = SurveyFactory(
            is_published=True,
            publish_date=timezone.now().date(),
            expire_date=timezone.now().date() + timezone.timedelta(days=1),
            need_logged_user=False,
        )

        request = self.factory.get("/")
        request.user = AnonymousUser()

        view = SurveyListView()
        view.request = request
        queryset = view.get_queryset()

        assert survey in queryset
        assert queryset.count() == 1

    def test_get_queryset_unpublished_surveys_excluded(self):
        """Тест исключения неопубликованных опросов"""
        # Создаем неопубликованный опрос
        survey = SurveyFactory(
            is_published=False,
            publish_date=timezone.now().date(),
            expire_date=timezone.now().date() + timezone.timedelta(days=1),
        )

        request = self.factory.get("/")
        request.user = AnonymousUser()

        view = SurveyListView()
        view.request = request
        queryset = view.get_queryset()

        assert survey not in queryset
        assert queryset.count() == 0

    def test_get_queryset_expired_surveys_excluded(self):
        """Тест исключения просроченных опросов"""
        # Создаем просроченный опрос
        survey = SurveyFactory(
            is_published=True,
            publish_date=timezone.now().date() - timezone.timedelta(days=2),
            expire_date=timezone.now().date() - timezone.timedelta(days=1),
        )

        request = self.factory.get("/")
        request.user = AnonymousUser()

        view = SurveyListView()
        view.request = request
        queryset = view.get_queryset()

        assert survey not in queryset
        assert queryset.count() == 0

    def test_get_queryset_future_surveys_excluded(self):
        """Тест исключения опросов с будущей датой публикации"""
        # Создаем опрос с будущей датой публикации
        survey = SurveyFactory(
            is_published=True,
            publish_date=timezone.now().date() + timezone.timedelta(days=1),
            expire_date=timezone.now().date() + timezone.timedelta(days=2),
        )

        request = self.factory.get("/")
        request.user = AnonymousUser()

        view = SurveyListView()
        view.request = request
        queryset = view.get_queryset()

        assert survey not in queryset
        assert queryset.count() == 0

    def test_get_queryset_authenticated_user_sees_all_surveys(self):
        """Тест что аутентифицированный пользователь видит все опросы"""
        user = UserFactory()

        # Создаем опросы требующие и не требующие авторизации
        public_survey = SurveyFactory(
            is_published=True,
            publish_date=timezone.now().date(),
            expire_date=timezone.now().date() + timezone.timedelta(days=1),
            need_logged_user=False,
        )
        private_survey = SurveyFactory(
            is_published=True,
            publish_date=timezone.now().date(),
            expire_date=timezone.now().date() + timezone.timedelta(days=1),
            need_logged_user=True,
        )

        request = self.factory.get("/")
        request.user = user

        view = SurveyListView()
        view.request = request
        queryset = view.get_queryset()

        assert public_survey in queryset
        assert private_survey in queryset
        assert queryset.count() == 2

    def test_get_queryset_anonymous_user_sees_only_public_surveys(self):
        """Тест что анонимный пользователь видит только публичные опросы"""
        # Создаем опросы требующие и не требующие авторизации
        public_survey = SurveyFactory(
            is_published=True,
            publish_date=timezone.now().date(),
            expire_date=timezone.now().date() + timezone.timedelta(days=1),
            need_logged_user=False,
        )
        private_survey = SurveyFactory(
            is_published=True,
            publish_date=timezone.now().date(),
            expire_date=timezone.now().date() + timezone.timedelta(days=1),
            need_logged_user=True,
        )

        request = self.factory.get("/")
        request.user = AnonymousUser()

        view = SurveyListView()
        view.request = request
        queryset = view.get_queryset()

        assert public_survey in queryset
        assert private_survey not in queryset
        assert queryset.count() == 1

    def test_view_response_status_code(self, client):
        """Тест статус кода ответа вьюхи"""
        # Создаем опубликованный опрос
        SurveyFactory(
            is_published=True,
            publish_date=timezone.now().date(),
            expire_date=timezone.now().date() + timezone.timedelta(days=1),
            need_logged_user=False,
        )

        response = client.get(reverse("survey:survey-list"))
        assert response.status_code == 200

    def test_view_template_used(self, client):
        """Тест использования правильного шаблона"""
        response = client.get(reverse("survey:survey-list"))
        assert "survey/survey_list.html" in [t.name for t in response.templates]
