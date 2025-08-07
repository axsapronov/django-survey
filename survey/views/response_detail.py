import logging

from django.conf import settings
from django.http import Http404
from django.shortcuts import get_object_or_404
from django.shortcuts import redirect
from django.shortcuts import render
from django.views.generic import View

from survey.models import Response

LOGGER = logging.getLogger(__name__)


class ResponseDetailView(View):
    template_name = "survey/response_detail.html"

    def get(self, request, *args, **kwargs):
        response_id = kwargs.get("response_id")
        survey_id = kwargs.get("survey_id")

        # Показываем результаты опроса
        return self._show_results(request, response_id, survey_id)

    def post(self, request, *args, **kwargs):
        # POST запросы не поддерживаются для просмотра результатов
        return redirect("survey:survey-list")

    def _show_results(self, request, response_id, survey_id):
        """Показывает результаты опроса"""
        # Получаем Response объект
        response = get_object_or_404(Response, pk=response_id, survey_id=survey_id)
        survey = response.survey

        # Проверяем права доступа
        if survey.need_logged_user and not request.user.is_authenticated:
            return redirect(f"{settings.LOGIN_URL}?next={request.path}")

        if request.user.is_authenticated and response.user != request.user:
            if response.user is not None:
                raise Http404("Response not found")

        # Проверяем, есть ли активная сессия для этого опроса
        session_key = request.session.get("survey_session")
        session_survey_id = request.session.get("survey_id")

        # Если есть активная сессия, очищаем её
        if session_key and session_survey_id == survey_id:
            self._clear_session(request)

        context = self._build_results_context(survey, response)
        return render(request, self.template_name, context)

    def _build_results_context(self, survey, response):
        """Строит контекст для страницы результатов"""
        # Получаем все ответы с информацией о правильности
        answers_data = []
        for answer in response.answers.select_related("question").order_by("question__order"):
            answers_data.append(
                {
                    "question": answer.question,
                    "answer": answer,
                    "is_correct": answer.is_correct,
                    "correct_answer": answer.question.correct_answer if answer.question.correct_answer else None,
                }
            )

        return {
            "survey": survey,
            "response": response,
            "answers_data": answers_data,
            "correct_answers": response.correct_answers_count,
            "correct_percentage": response.correct_answers_percentage,
            "incorrect_percentage": 100 - response.correct_answers_percentage,
        }

    def _clear_session(self, request):
        """Очищает данные сессии опроса"""
        session_keys = ["survey_session", "survey_id", "current_question"]
        for key in session_keys:
            if key in request.session:
                del request.session[key]
