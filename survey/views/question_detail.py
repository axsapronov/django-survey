from django.shortcuts import get_object_or_404
from django.shortcuts import redirect
from django.views.generic import FormView

from survey.forms import QuestionAnswerForm
from survey.models import Answer
from survey.models import Response
from survey.models import Survey


class QuestionDetailView(FormView):
    """View для ответа на конкретный вопрос"""

    template_name = "survey/question_detail.html"

    def dispatch(self, request, *args, **kwargs):
        self.survey = get_object_or_404(Survey, pk=self.kwargs["survey_id"])

        # Проверяем сессию
        if not self._check_session():
            return redirect(self.survey.get_absolute_url())

        # Получаем текущий вопрос
        self.current_question_index = self.request.session.get("current_question", 0)
        self.questions = list(self.survey.questions.order_by("order"))

        if self.current_question_index >= len(self.questions):
            response, _ = self._get_or_create_response()
            return redirect(response.get_absolute_url())

        self.current_question = self.questions[self.current_question_index]

        return super().dispatch(request, *args, **kwargs)

    def _check_session(self):
        """Проверяет валидность сессии"""
        session_key = self.request.session.get("survey_session")
        survey_id = self.request.session.get("survey_id")

        if not session_key or survey_id != self.survey.id:
            return False

        return True

    def get_form_class(self):
        # Получаем или создаем Response для передачи в форму
        response, _ = self._get_or_create_response()

        return lambda *args, **kwargs: QuestionAnswerForm(
            self.current_question,
            response=response,
            survey=self.survey,
            current_question_index=self.current_question_index + 1,
            read_only=self.request.method == "POST",
            *args,
            **kwargs,
        )

    def get_form_kwargs(self):
        """Передает дополнительные параметры в форму"""
        kwargs = super().get_form_kwargs()

        # Передаем параметры для отображения правильного ответа
        if self.request.method == "POST" and self.current_question.correct_answer:
            kwargs["show_correct_answer"] = True
            kwargs["correct_answer"] = self.current_question.display_correct_answer

        return kwargs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["survey"] = self.survey
        context["question"] = self.current_question
        context["current_question_index"] = self.current_question_index + 1

        context["progress_percentage"] = int((self.current_question_index) / self.survey.total_questions * 100) or 3

        # Показываем правильный ответ только после POST запроса
        if self.request.method == "POST" and self.current_question.correct_answer:
            context["correct_answer"] = self.current_question.display_correct_answer
            context["show_correct_answer"] = True

        return context

    def form_valid(self, form):
        # Сохраняем ответ
        self._save_answer(form)

        # Если есть правильный ответ, показываем его и остаемся на этой странице
        if self.current_question.correct_answer:
            self.show_correct_answer = True
            self.correct_answer = self.current_question.display_correct_answer
            context = self.get_context_data()
            context["show_correct_answer"] = True
            context["correct_answer"] = self.correct_answer
            return self.render_to_response(context)

        # Иначе переходим к следующему вопросу
        return self._go_to_next_question()

    def get(self, request, *args, **kwargs):
        """Обрабатывает GET запросы"""
        # Если показывается правильный ответ, переходим к следующему вопросу
        if request.GET.get("next") == "true":
            return self._go_to_next_question()

        return super().get(request, *args, **kwargs)

    def _go_to_next_question(self):
        """Переходит к следующему вопросу или завершает опрос"""
        # Переходим к следующему вопросу
        self.request.session["current_question"] = self.current_question_index + 1

        # Проверяем, есть ли еще вопросы
        if self.current_question_index + 1 >= len(self.questions):
            response, _ = self._get_or_create_response()
            return redirect(response.get_absolute_url())

        return redirect("survey:question-detail", survey_id=self.survey.id)

    def _save_answer(self, form):
        """Сохраняет ответ пользователя"""
        # Получаем или создаем Response
        response, created = self._get_or_create_response()

        # Получаем значение ответа
        answer_value = form.get_answer_value()

        if answer_value is not None:
            # Преобразуем в строку для сохранения
            if isinstance(answer_value, list):
                body = str(answer_value)
            else:
                body = str(answer_value)

            # Создаем или обновляем ответ
            answer, created = Answer.objects.get_or_create(
                question=self.current_question, response=response, defaults={"body": body}
            )

            if not created:
                answer.body = body
                answer.save()

    def _get_or_create_response(self):
        """Получает или создает Response для текущей сессии"""
        session_key = self.request.session.get("survey_session")

        # Ищем существующий Response
        try:
            response = Response.objects.get(interview_uuid=session_key)
        except Response.DoesNotExist:
            # Создаем новый Response
            response = Response.objects.create(
                survey=self.survey,
                user=self.request.user if self.request.user.is_authenticated else None,
                interview_uuid=session_key,
            )

        return response, True
