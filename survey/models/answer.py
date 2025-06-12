"""
These type-specific answer models use a text field to allow for flexible
field sizes depending on the actual question this answer corresponds to any
"required" attribute will be enforced by the form.
"""

import logging

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models
from django.utils.text import slugify
from django.utils.translation import gettext_lazy as _

from .question import Question
from .response import Response

LOGGER = logging.getLogger(__name__)


class Answer(models.Model):
    question = models.ForeignKey(Question, on_delete=models.CASCADE, verbose_name=_("Question"), related_name="answers")
    response = models.ForeignKey(Response, on_delete=models.CASCADE, verbose_name=_("Response"), related_name="answers")
    created = models.DateTimeField(_("Creation date"), auto_now_add=True)
    updated = models.DateTimeField(_("Update date"), auto_now=True)
    body = models.TextField(_("Content"), blank=True, null=True)

    def __init__(self, *args, **kwargs):
        try:
            question = Question.objects.get(pk=kwargs["question_id"])
        except KeyError:
            question = kwargs.get("question")
        body = kwargs.get("body")
        if question and body:
            self.check_answer_body(question, body)
        super().__init__(*args, **kwargs)

    @property
    def values(self):
        if self.body is None:
            return [None]
        if not self.body.startswith("[") or not self.body.endswith("]"):
            return [self.body]
        return [x.replace("'", "") for x in self.body[1:-1].split(settings.CHOICES_SEPARATOR)]

    @property
    def display_value(self):
        if self.question.type in [Question.RADIO, Question.SELECT, Question.SELECT_MULTIPLE]:
            return ", ".join(self.values)
        return self.body

    def _validate_value(self, value, question_type, choices=None):
        """
        Общий метод для валидации значения в зависимости от типа вопроса.

        Args:
            value: Значение для проверки
            question_type: Тип вопроса
            choices: Список допустимых вариантов ответа (для вопросов с выбором)

        Returns:
            bool: True если значение валидно

        Raises:
            ValidationError: Если значение невалидно
        """
        if not value:
            return True

        if question_type in [Question.RADIO, Question.SELECT, Question.SELECT_MULTIPLE]:
            if choices and value not in choices:
                msg = f"Impossible answer '{value}' should be in {choices}"
                raise ValidationError(msg)
            return True

        if question_type == Question.INTEGER:
            try:
                int(value)
                return True
            except ValueError as e:
                msg = "Answer is not an integer"
                raise ValidationError(msg) from e

        if question_type == Question.FLOAT:
            try:
                float(value)
                return True
            except ValueError as e:
                msg = "Answer is not a number"
                raise ValidationError(msg) from e

        return True

    def check_answer_body(self, question, body):
        """Валидация ответа при создании"""
        if question.type in [Question.RADIO, Question.SELECT, Question.SELECT_MULTIPLE]:
            choices = question.get_clean_choices()
            answers = []
            if body:
                if body[0] == "[":
                    for i, part in enumerate(body.split("'")):
                        if i % 2 == 1:
                            answers.append(part)
                else:
                    answers = [body]
            for answer in answers:
                self._validate_value(answer, question.type, choices)
        else:
            self._validate_value(body, question.type)

    @property
    def is_correct(self) -> bool:
        """
        Checks the correctness of the answer depending on the question type.
        If the question has a correct_answer defined, compares with it.
        Otherwise uses the default logic for checking answer validity.

        Returns:
            bool: True if the answer is correct, False otherwise
        """
        if not self.body:
            return not self.question.required

        if self.question.correct_answer:
            return self._check_against_correct_answer()

        return True

    def _check_against_correct_answer(self) -> bool:
        """
        Сравнивает ответ пользователя с корректным ответом, заданным в вопросе.
        """
        try:
            answer_values = self.values
            correct_answers = self.question.get_clean_correct_answer()

            if not correct_answers:
                return False

            # Для текстовых вопросов
            if self.question.type in [Question.TEXT, Question.SHORT_TEXT]:
                user_answer = answer_values[0].strip().lower() if answer_values else ""
                correct_answer = correct_answers[0].strip().lower()
                return user_answer == correct_answer

            # Для числовых вопросов
            if self.question.type in [Question.INTEGER, Question.FLOAT]:
                try:
                    user_value = float(answer_values[0]) if answer_values else None
                    correct_value = float(correct_answers[0])
                    if self.question.type == Question.INTEGER:
                        return int(user_value) == int(correct_value)
                    return abs(user_value - correct_value) < 1e-9
                except (ValueError, IndexError):
                    return False

            # Для вопросов с выбором
            if self.question.type in [Question.RADIO, Question.SELECT, Question.SELECT_IMAGE]:
                if not answer_values or len(correct_answers) != 1:
                    return False
                user_answer = slugify(answer_values[0].lower(), allow_unicode=True)
                correct_answer = slugify(correct_answers[0].lower(), allow_unicode=True)
                return user_answer == correct_answer

            # Для вопросов с множественным выбором
            if self.question.type == Question.SELECT_MULTIPLE:
                user_answers = set(slugify(val.lower(), allow_unicode=True) for val in answer_values)
                correct_answers_set = set(slugify(ans.lower(), allow_unicode=True) for ans in correct_answers)
                return user_answers == correct_answers_set

            # Для даты
            if self.question.type == Question.DATE:
                user_answer = answer_values[0].strip() if answer_values else ""
                correct_answer = correct_answers[0].strip()
                return user_answer == correct_answer

            return False

        except Exception:
            LOGGER.exception("Error checking answer against correct answer")
            return False

    def __str__(self):
        return f"{self.__class__.__name__} to '{self.question}' : '{self.body}'"
