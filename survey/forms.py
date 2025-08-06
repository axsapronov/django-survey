import logging
import uuid

from django import forms
from django.conf import settings
from django.utils.text import slugify

from survey.models import Answer
from survey.models import Question
from survey.models import Response
from survey.widgets import ImageSelectWidget

LOGGER = logging.getLogger(__name__)


class QuestionForm(forms.Form):
    """
    Форма для обработки одного вопроса.
    Сохраняет ответ сразу после валидации.
    """

    FIELDS = {
        Question.TEXT: forms.CharField,
        Question.SHORT_TEXT: forms.CharField,
        Question.SELECT_MULTIPLE: forms.MultipleChoiceField,
        Question.INTEGER: forms.IntegerField,
        Question.FLOAT: forms.FloatField,
        Question.DATE: forms.DateField,
    }

    WIDGETS = {
        Question.TEXT: forms.Textarea,
        Question.SHORT_TEXT: forms.TextInput,
        Question.RADIO: forms.RadioSelect,
        Question.SELECT: forms.Select,
        Question.SELECT_IMAGE: ImageSelectWidget,
        Question.SELECT_MULTIPLE: forms.CheckboxSelectMultiple,
    }

    def __init__(self, question, response, *args, **kwargs):
        """
        Инициализация формы для одного вопроса.

        Args:
            question: Объект Question
            response: Объект Response (может быть None для нового ответа)
            *args, **kwargs: Стандартные аргументы формы
        """
        self.question = question
        self.response = response
        super().__init__(*args, **kwargs)

        # Добавляем поле для вопроса
        self.add_question_field()

        # Если есть существующий ответ, заполняем начальными данными
        if self.response:
            self.set_initial_data()

    def add_question_field(self):
        """Добавляет поле для текущего вопроса"""
        kwargs = {"label": self.question.text, "required": self.question.required}

        # Добавляем choices для вопросов с выбором
        if self.question.type in [Question.RADIO, Question.SELECT, Question.SELECT_MULTIPLE, Question.SELECT_IMAGE]:
            choices = self.question.get_choices()
            if self.question.type in [Question.SELECT, Question.SELECT_IMAGE]:
                choices = tuple([("", "-------------")]) + choices
            kwargs["choices"] = choices

        # Добавляем widget
        if self.question.type in self.WIDGETS:
            kwargs["widget"] = self.WIDGETS[self.question.type]()

        # Создаем поле
        if self.question.type in self.FIELDS:
            field = self.FIELDS[self.question.type](**kwargs)
        else:
            field = forms.ChoiceField(**kwargs)

        # Добавляем CSS класс для даты
        if self.question.type == Question.DATE:
            field.widget.attrs["class"] = "date"

        # Добавляем атрибут категории
        field.widget.attrs["category"] = self.question.category.name if self.question.category else ""

        # Используем имя поля в формате question_<id> для совместимости со старыми тестами
        self.fields[f"question_{self.question.pk}"] = field

    def set_initial_data(self):
        """Устанавливает начальные данные из существующего ответа"""
        try:
            existing_answer = Answer.objects.get(response=self.response, question=self.question)

            field_name = f"question_{self.question.pk}"

            if self.question.type == Question.SELECT_MULTIPLE:
                # Для множественного выбора нужно преобразовать строку в список
                if (
                    existing_answer.body
                    and existing_answer.body.startswith("[")
                    and existing_answer.body.endswith("]")
                ):
                    # Извлекаем значения из строки вида "['value1', 'value2']"
                    values_str = existing_answer.body[1:-1]
                    if values_str:
                        values = []
                        for part in values_str.split(settings.CHOICES_SEPARATOR):
                            # Извлекаем значение между кавычками
                            if "'" in part:
                                value = part.split("'")[1]
                                values.append(slugify(value))
                        self.fields[field_name].initial = values
                else:
                    # Одно значение
                    if existing_answer.body:
                        self.fields[field_name].initial = [slugify(existing_answer.body)]
            else:
                # Для остальных типов вопросов
                if self.question.type in [Question.RADIO, Question.SELECT, Question.SELECT_IMAGE]:
                    # Для вопросов с выбором нужно найти slug
                    if existing_answer.body:
                        choices = dict(self.question.get_choices())
                        # Ищем ключ по значению
                        for key, value in choices.items():
                            if value == existing_answer.body:
                                self.fields[field_name].initial = key
                                break
                else:
                    # Для текстовых и числовых вопросов
                    self.fields[field_name].initial = existing_answer.body

        except Answer.DoesNotExist:
            pass

    def save(self, commit=True):
        """
        Сохраняет ответ в базу данных.

        Returns:
            Answer: Сохраненный объект ответа
        """
        if not self.is_valid():
            raise ValueError("Form is not valid")

        # Получаем или создаем Response
        if self.response is None:
            # Создаем новый Response
            user = None
            if hasattr(self, "user") and self.user.is_authenticated:
                user = self.user
            self.response = Response.objects.create(
                survey=self.question.survey,
                user=user,
                interview_uuid=uuid.uuid4().hex,
            )

        # Получаем значение ответа из поля question_<id>
        field_name = f"question_{self.question.pk}"
        answer_value = self.cleaned_data[field_name]

        # Преобразуем значение в зависимости от типа вопроса
        if self.question.type in [Question.RADIO, Question.SELECT, Question.SELECT_MULTIPLE, Question.SELECT_IMAGE]:
            choices = dict(self.question.get_choices())
            if self.question.type == Question.SELECT_MULTIPLE:
                # Для множественного выбора
                selected_values = []
                for val in answer_value:
                    if val in choices:
                        selected_values.append(choices[val])
                body_value = str(selected_values)
            else:
                # Для одиночного выбора
                body_value = choices.get(answer_value, str(answer_value))
        else:
            body_value = str(answer_value)

        # Получаем или создаем Answer
        answer, created = Answer.objects.get_or_create(
            response=self.response, question=self.question, defaults={"body": body_value}
        )

        if not created:
            # Обновляем существующий ответ
            answer.body = body_value
            answer.save()

        return answer

    def get_previous_answer_info(self):
        """
        Получает информацию о предыдущем ответе для отображения его правильности.

        Returns:
            dict: Информация о предыдущем ответе или None
        """
        if not self.response:
            return None

        try:
            previous_answer = Answer.objects.get(response=self.response, question=self.question)

            return {
                "question_text": self.question.text,
                "user_answer": previous_answer.display_value,
                "is_correct": previous_answer.is_correct,
                "correct_answer": self.question.display_correct_answer,
                "question_type": self.question.type,
            }
        except Answer.DoesNotExist:
            return None


# Формы для пошагового прохождения опроса
class SurveyIntroForm(forms.Form):
    """Форма для вводной страницы опроса"""

    start_survey = forms.BooleanField(required=True, widget=forms.HiddenInput, initial=True)


class QuestionAnswerForm(forms.Form):
    """Форма для ответа на вопрос"""

    def __init__(self, question, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.question = question
        self._build_fields()

    def _build_fields(self):
        """Строит поля формы в зависимости от типа вопроса"""
        field_name = f"question_{self.question.id}"

        if self.question.type == Question.TEXT:
            self.fields[field_name] = forms.CharField(
                label=self.question.text,
                widget=forms.Textarea(attrs={"rows": 4, "class": "form-control"}),
                required=self.question.required,
            )
        elif self.question.type == Question.SHORT_TEXT:
            self.fields[field_name] = forms.CharField(
                label=self.question.text,
                widget=forms.TextInput(attrs={"class": "form-control"}),
                required=self.question.required,
            )
        elif self.question.type == Question.RADIO:
            choices = [(choice.strip(), choice.strip()) for choice in self.question.get_clean_choices()]
            self.fields[field_name] = forms.ChoiceField(
                label=self.question.text,
                choices=choices,
                widget=forms.RadioSelect(attrs={"class": "form-check-input"}),
                required=self.question.required,
            )
        elif self.question.type == Question.SELECT:
            choices = [(choice.strip(), choice.strip()) for choice in self.question.get_clean_choices()]
            self.fields[field_name] = forms.ChoiceField(
                label=self.question.text,
                choices=choices,
                widget=forms.Select(attrs={"class": "form-select"}),
                required=self.question.required,
            )
        elif self.question.type == Question.SELECT_MULTIPLE:
            choices = [(choice.strip(), choice.strip()) for choice in self.question.get_clean_choices()]
            self.fields[field_name] = forms.MultipleChoiceField(
                label=self.question.text,
                choices=choices,
                widget=forms.CheckboxSelectMultiple(attrs={"class": "form-check-input"}),
                required=self.question.required,
            )
        elif self.question.type == Question.INTEGER:
            self.fields[field_name] = forms.IntegerField(
                label=self.question.text,
                widget=forms.NumberInput(attrs={"class": "form-control"}),
                required=self.question.required,
            )
        elif self.question.type == Question.FLOAT:
            self.fields[field_name] = forms.FloatField(
                label=self.question.text,
                widget=forms.NumberInput(attrs={"class": "form-control", "step": "0.01"}),
                required=self.question.required,
            )
        elif self.question.type == Question.DATE:
            self.fields[field_name] = forms.DateField(
                label=self.question.text,
                widget=forms.DateInput(attrs={"class": "form-control", "type": "date"}),
                required=self.question.required,
            )
        else:
            # По умолчанию текстовое поле
            self.fields[field_name] = forms.CharField(
                label=self.question.text,
                widget=forms.TextInput(attrs={"class": "form-control"}),
                required=self.question.required,
            )

    def get_answer_value(self):
        """Возвращает значение ответа в правильном формате"""
        field_name = f"question_{self.question.id}"
        if field_name not in self.cleaned_data:
            return None

        value = self.cleaned_data[field_name]

        # Для множественного выбора преобразуем в список
        if self.question.type == Question.SELECT_MULTIPLE:
            if isinstance(value, list):
                return value
            return [value] if value else []

        return value
