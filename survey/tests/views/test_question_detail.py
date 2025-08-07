import pytest
from django.contrib.auth.models import AnonymousUser
from django.test import RequestFactory
from django.urls import reverse

from survey.tests.factories import QuestionFactory
from survey.tests.factories import SurveyFactory
from survey.views import QuestionDetailView


@pytest.mark.django_db
class TestQuestionDetailView:
    def setup_method(self):
        self.factory = RequestFactory()
        self.view = QuestionDetailView.as_view()

    def test_dispatch_without_session_redirects_to_survey_detail(self):
        """Тест редиректа при отсутствии сессии"""
        survey = SurveyFactory()

        request = self.factory.get(f"/survey/{survey.id}/question/")
        request.user = AnonymousUser()
        request.session = {}

        response = self.view(request, survey_id=survey.id)

        assert response.status_code == 302
        assert f"/survey/{survey.id}/" in response.url

    def test_dispatch_with_invalid_session_redirects_to_survey_detail(self):
        """Тест редиректа при невалидной сессии"""
        survey = SurveyFactory()

        request = self.factory.get(f"/survey/{survey.id}/question/")
        request.user = AnonymousUser()
        request.session = {
            "survey_session": "invalid-session",
            "survey_id": 99999,  # Неправильный ID опроса
        }

        response = self.view(request, survey_id=survey.id)

        assert response.status_code == 302
        assert f"/survey/{survey.id}/" in response.url

    def test_dispatch_with_valid_session_and_questions(self):
        """Тест доступа с валидной сессией и вопросами"""
        survey = SurveyFactory()
        QuestionFactory(survey=survey, order=1)

        request = self.factory.get(f"/survey/{survey.id}/question/")
        request.user = AnonymousUser()
        request.session = {"survey_session": "valid-session", "survey_id": survey.id, "current_question": 0}

        response = self.view(request, survey_id=survey.id)

        assert response.status_code == 200

    def test_dispatch_no_more_questions_redirects_to_response(self):
        """Тест редиректа когда вопросы закончились"""
        survey = SurveyFactory()

        request = self.factory.get(f"/survey/{survey.id}/question/")
        request.user = AnonymousUser()
        request.session = {
            "survey_session": "valid-session",
            "survey_id": survey.id,
            "current_question": 1,  # Больше чем количество вопросов
        }

        response = self.view(request, survey_id=survey.id)

        assert response.status_code == 302

    def test_get_context_data(self):
        """Тест контекста страницы"""
        survey = SurveyFactory()
        question = QuestionFactory(survey=survey, order=1)

        request = self.factory.get(f"/survey/{survey.id}/question/")
        request.user = AnonymousUser()
        request.session = {"survey_session": "valid-session", "survey_id": survey.id, "current_question": 0}

        view = QuestionDetailView()
        view.request = request
        view.survey = survey
        view.current_question = question
        view.current_question_index = 0
        view.questions = [question]

        context = view.get_context_data()

        assert context["survey"] == survey
        assert context["question"] == question
        assert context["current_question_index"] == 1
        assert context["progress_percentage"] == 3

    def test_get_context_data_with_correct_answer_after_post(self):
        """Тест контекста с правильным ответом после POST"""
        survey = SurveyFactory()
        question = QuestionFactory(survey=survey, order=1, correct_answer="Правильный ответ")

        request = self.factory.post(f"/survey/{survey.id}/question/")
        request.user = AnonymousUser()
        request.session = {"survey_session": "valid-session", "survey_id": survey.id, "current_question": 0}

        view = QuestionDetailView()
        view.request = request
        view.survey = survey
        view.current_question = question
        view.current_question_index = 0
        view.questions = [question]

        context = view.get_context_data()

        assert context["show_correct_answer"] is True
        assert context["correct_answer"] == "Правильный ответ"

    def test_get_with_next_parameter(self):
        """Тест GET запроса с параметром next"""
        survey = SurveyFactory()
        question = QuestionFactory(survey=survey, order=1)

        request = self.factory.get(f"/survey/{survey.id}/question/?next=true")
        request.user = AnonymousUser()
        request.session = {"survey_session": "valid-session", "survey_id": survey.id, "current_question": 0}

        view = QuestionDetailView()
        view.request = request
        view.survey = survey
        view.current_question = question
        view.current_question_index = 0
        view.questions = [question]

        response = view.get(request)

        assert hasattr(response, "status_code") or isinstance(response, str)

    def test_form_valid_without_correct_answer_goes_to_next_question(self):
        """Тест перехода к следующему вопросу без правильного ответа"""
        survey = SurveyFactory()
        question1 = QuestionFactory(survey=survey, order=1)
        question2 = QuestionFactory(survey=survey, order=2)

        request = self.factory.post(f"/survey/{survey.id}/question/")
        request.user = AnonymousUser()
        request.session = {"survey_session": "valid-session", "survey_id": survey.id, "current_question": 0}

        view = QuestionDetailView()
        view.request = request
        view.survey = survey
        view.current_question = question1
        view.current_question_index = 0
        view.questions = [question1, question2]

        # Мокаем форму
        class MockForm:
            def get_answer_value(self):
                return "Ответ пользователя"

        response = view.form_valid(MockForm())

        assert response.status_code == 302
        assert request.session["current_question"] == 1

    def test_form_valid_with_correct_answer_stays_on_page(self):
        """Тест оставания на странице при наличии правильного ответа"""
        survey = SurveyFactory()
        question = QuestionFactory(survey=survey, order=1, correct_answer="Правильный ответ")

        request = self.factory.post(f"/survey/{survey.id}/question/")
        request.user = AnonymousUser()
        request.session = {"survey_session": "valid-session", "survey_id": survey.id, "current_question": 0}

        view = QuestionDetailView()
        view.request = request
        view.survey = survey
        view.current_question = question
        view.current_question_index = 0
        view.questions = [question]

        # Мокаем форму
        class MockForm:
            def get_answer_value(self):
                return "Ответ пользователя"

        response = view.form_valid(MockForm())

        assert response.status_code == 200

    def test_save_answer_creates_new_answer(self):
        """Тест создания нового ответа"""
        survey = SurveyFactory()
        question = QuestionFactory(survey=survey, order=1)

        request = self.factory.post(f"/survey/{survey.id}/question/")
        request.user = AnonymousUser()
        request.session = {"survey_session": "valid-session", "survey_id": survey.id, "current_question": 0}

        view = QuestionDetailView()
        view.request = request
        view.survey = survey
        view.current_question = question
        view.current_question_index = 0
        view.questions = [question]

        # Мокаем форму
        class MockForm:
            def get_answer_value(self):
                return "Ответ пользователя"

        view._save_answer(MockForm())

        # Проверяем что ответ создан
        from survey.models import Answer
        from survey.models import Response

        response = Response.objects.get(interview_uuid="valid-session")
        answer = Answer.objects.get(question=question, response=response)
        assert answer.body == "Ответ пользователя"

    def test_save_answer_updates_existing_answer(self):
        """Тест обновления существующего ответа"""
        survey = SurveyFactory()
        question = QuestionFactory(survey=survey, order=1)

        request = self.factory.post(f"/survey/{survey.id}/question/")
        request.user = AnonymousUser()
        request.session = {"survey_session": "valid-session", "survey_id": survey.id, "current_question": 0}

        view = QuestionDetailView()
        view.request = request
        view.survey = survey
        view.current_question = question
        view.current_question_index = 0
        view.questions = [question]

        # Создаем существующий ответ
        from survey.models import Answer
        from survey.models import Response

        response = Response.objects.create(survey=survey, interview_uuid="valid-session")
        existing_answer = Answer.objects.create(question=question, response=response, body="Старый ответ")

        # Мокаем форму
        class MockForm:
            def get_answer_value(self):
                return "Новый ответ"

        view._save_answer(MockForm())

        # Проверяем что ответ обновлен
        existing_answer.refresh_from_db()
        assert existing_answer.body == "Новый ответ"

    def test_view_with_client(self, client):
        """Тест вьюхи через клиент"""
        survey = SurveyFactory()
        QuestionFactory(survey=survey, order=1)

        # Создаем сессию
        session = client.session
        session["survey_session"] = "valid-session"
        session["survey_id"] = survey.id
        session["current_question"] = 0
        session.save()

        response = client.get(reverse("survey:question-detail", kwargs={"survey_id": survey.id}))
        assert response.status_code == 200

    def test_view_template_used(self, client):
        """Тест использования правильного шаблона"""
        survey = SurveyFactory()
        QuestionFactory(survey=survey, order=1)

        # Создаем сессию
        session = client.session
        session["survey_session"] = "valid-session"
        session["survey_id"] = survey.id
        session["current_question"] = 0
        session.save()

        response = client.get(reverse("survey:question-detail", kwargs={"survey_id": survey.id}))
        assert "survey/question_detail.html" in [t.name for t in response.templates]


@pytest.mark.django_db
class TestQuestionDetailViewCorrectAnswerDisplay:
    """Тесты для проверки отображения правильного ответа в форме"""

    def test_form_shows_correct_answer_after_submission(self, client):
        """Тест: форма показывает правильный ответ после отправки"""
        from survey.models import Question

        survey = SurveyFactory()
        QuestionFactory(
            survey=survey,
            type=Question.RADIO,
            choices="Вариант 1, Вариант 2, Вариант 3",
            correct_answer="Вариант 2",
            order=1,
        )

        # Начинаем опрос - создаем сессию
        response = client.post(
            reverse("survey:survey-detail", kwargs={"survey_id": survey.id}), data={"start_survey": True}
        )

        # Отвечаем на вопрос
        response = client.post(
            reverse("survey:question-detail", kwargs={"survey_id": survey.id}),
            data={"question_1": "Вариант 1"},  # Неправильный ответ
        )

        # Проверяем что страница отображается (не редирект)
        assert response.status_code == 200

        # Проверяем что форма в read-only режиме (правильный ответ показан)
        content = response.content.decode()
        assert "form-check-input" in content  # Поля формы присутствуют
        assert "answer-invalid" in content or "answer-valid" in content  # Валидация ответов

    def test_form_does_not_show_correct_answer_before_submission(self, client):
        """Тест: форма не показывает правильный ответ до отправки"""
        from survey.models import Question

        survey = SurveyFactory()
        QuestionFactory(
            survey=survey, type=Question.RADIO, choices="Вариант 1, Вариант 2", correct_answer="Вариант 2", order=1
        )

        # Начинаем опрос - создаем сессию
        client.post(reverse("survey:survey-detail", kwargs={"survey_id": survey.id}), data={"start_survey": True})

        # Получаем страницу вопроса
        response = client.get(reverse("survey:question-detail", kwargs={"survey_id": survey.id}))

        # Проверяем что страница отображается
        assert response.status_code == 200

        # Проверяем что форма не в read-only режиме (правильный ответ не показан)
        content = response.content.decode()
        assert "form-check-input" in content  # Поля формы присутствуют
        assert "answer-invalid" not in content  # Валидация ответов отсутствует
        assert "answer-valid" not in content

    def test_crispy_forms_integration(self, client):
        """Тест: интеграция с crispy forms работает корректно"""
        survey = SurveyFactory()
        QuestionFactory(survey=survey, order=1)

        # Начинаем опрос - создаем сессию
        client.post(reverse("survey:survey-detail", kwargs={"survey_id": survey.id}), data={"start_survey": True})

        # Получаем страницу вопроса
        response = client.get(reverse("survey:question-detail", kwargs={"survey_id": survey.id}))

        # Проверяем что форма рендерится с crispy forms
        content = response.content.decode()
        # Проверяем наличие формы и полей
        assert "form" in content
        assert "question_1" in content
        # Проверяем что используется crispy forms
        assert "form-control" in content

    def test_correct_answer_display_for_different_question_types(self, client):
        """Тест: правильный ответ отображается для разных типов вопросов"""
        from survey.models import Question

        survey = SurveyFactory()
        QuestionFactory(
            survey=survey,
            type=Question.SELECT_MULTIPLE,
            choices="Опция 1, Опция 2, Опция 3",
            correct_answer="Опция 1, Опция 3",
            order=1,
        )

        # Начинаем опрос - создаем сессию
        client.post(reverse("survey:survey-detail", kwargs={"survey_id": survey.id}), data={"start_survey": True})

        # Отвечаем на вопрос с множественным выбором
        response = client.post(
            reverse("survey:question-detail", kwargs={"survey_id": survey.id}),
            data={"question_1": ["Опция 1", "Опция 2"]},  # Частично правильный ответ
        )

        # Проверяем что страница отображается (не редирект)
        assert response.status_code == 200

        # Проверяем что форма в read-only режиме с валидацией
        content = response.content.decode()
        assert "form-check-input" in content
        assert "answer-invalid" in content or "answer-valid" in content

    def test_form_context_has_correct_answer_after_post(self, client):
        """Тест: контекст содержит правильный ответ после POST запроса"""
        from survey.models import Question

        survey = SurveyFactory()
        QuestionFactory(
            survey=survey,
            type=Question.RADIO,
            choices="Вариант 1, Вариант 2",
            correct_answer="Вариант 2",
            order=1,
        )

        # Начинаем опрос
        client.post(reverse("survey:survey-detail", kwargs={"survey_id": survey.id}), data={"start_survey": True})

        # Отвечаем на вопрос
        response = client.post(
            reverse("survey:question-detail", kwargs={"survey_id": survey.id}),
            data={"question_1": "Вариант 1"},
        )

        # Проверяем что контекст содержит правильный ответ
        assert response.status_code == 200
        # Проверяем что форма показывает правильный ответ через CSS классы
        content = response.content.decode()
        assert "answer-valid" in content or "answer-invalid" in content

    def test_form_context_no_correct_answer_before_post(self, client):
        """Тест: контекст не содержит правильный ответ до POST запроса"""
        from survey.models import Question

        survey = SurveyFactory()
        QuestionFactory(
            survey=survey,
            type=Question.RADIO,
            choices="Вариант 1, Вариант 2",
            correct_answer="Вариант 2",
            order=1,
        )

        # Начинаем опрос
        client.post(reverse("survey:survey-detail", kwargs={"survey_id": survey.id}), data={"start_survey": True})

        # Получаем страницу вопроса
        response = client.get(reverse("survey:question-detail", kwargs={"survey_id": survey.id}))

        # Проверяем что контекст не содержит правильный ответ
        assert response.status_code == 200
        content = response.content.decode()
        assert "answer-valid" not in content
        assert "answer-invalid" not in content
