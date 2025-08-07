import logging

from crispy_forms.helper import FormHelper
from crispy_forms.layout import HTML
from crispy_forms.layout import Button
from crispy_forms.layout import Div
from crispy_forms.layout import Field
from crispy_forms.layout import Layout
from crispy_forms.layout import Submit
from django import forms
from django.urls import reverse
from django.utils.translation import gettext_lazy as _

from survey.models import Answer
from survey.models import Question
from survey.models import Response

LOGGER = logging.getLogger(__name__)


def mark_option(option, value, correct_answers, user_answers):
    """Помечает опцию CSS классами в зависимости от правильности ответа"""
    if "attrs" not in option:
        option["attrs"] = {}

    if "class" not in option["attrs"]:
        option["attrs"]["class"] = ""

    if value in correct_answers:
        option["attrs"]["answer-valid"] = "true"

    if value in user_answers and value not in correct_answers:
        option["attrs"]["answer-invalid"] = "true"

    return option


class ValidatedRadioSelect(forms.RadioSelect):
    use_fieldset = False

    def __init__(self, correct_answers=None, user_answers=None, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.correct_answers = correct_answers or []
        self.user_answers = user_answers or []

    def create_option(self, name, value, label, selected, index, subindex=None, attrs=None):
        option = super().create_option(name, value, label, selected, index, subindex, attrs)
        option = mark_option(option, value, self.correct_answers, self.user_answers)
        return option


class ValidatedCheckboxSelectMultiple(forms.CheckboxSelectMultiple):
    use_fieldset = False

    def __init__(self, correct_answers=None, user_answers=None, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.correct_answers = correct_answers or []
        self.user_answers = user_answers or []

    def create_option(self, name, value, label, selected, index, subindex=None, attrs=None):
        option = super().create_option(name, value, label, selected, index, subindex, attrs)
        option = mark_option(option, value, self.correct_answers, self.user_answers)
        return option


class ValidatedSelect(forms.Select):
    use_fieldset = False

    def __init__(self, correct_answers=None, user_answers=None, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.correct_answers = correct_answers or []
        self.user_answers = user_answers or []

    def create_option(self, name, value, label, selected, index, subindex=None, attrs=None):
        option = super().create_option(name, value, label, selected, index, subindex, attrs)
        option = mark_option(option, value, self.correct_answers, self.user_answers)
        return option


# Формы для пошагового прохождения опроса
class SurveyIntroForm(forms.Form):
    """Форма для вводной страницы опроса"""

    start_survey = forms.BooleanField(required=True, widget=forms.HiddenInput, initial=True)


class QuestionAnswerForm(forms.Form):
    """Форма для ответа на вопрос"""

    def __init__(self, question, response=None, survey=None, current_question_index=None, *args, **kwargs):
        self.question = question
        self.response: Response = response
        self.survey = survey
        self.current_question_index = current_question_index
        self.show_correct_answer = kwargs.pop("show_correct_answer", False)
        self.correct_answer = kwargs.pop("correct_answer", None)
        self.read_only = kwargs.pop("read_only", False)

        # Автоматически включаем read-only режим, если передан корректный ответ
        if self.correct_answer and not self.read_only:
            self.read_only = True

        self.question_answers = []
        self.user_answers = []
        if self.response and self.question.correct_answer:
            self.question_answers = [choice.strip() for choice in self.question.get_clean_correct_answer()]

        try:
            existing_answer = Answer.objects.get(response=self.response, question=self.question)
            self.user_answers = existing_answer.values
        except Answer.DoesNotExist:
            pass

        # Создаем виджеты с учетом валидации
        self.is_correct_answer = set(self.user_answers) == set(self.question_answers)
        self.has_answer = bool(self.user_answers)

        super().__init__(*args, **kwargs)
        self._build_fields()

    def _build_fields(self):
        """Строит поля формы в зависимости от типа вопроса"""
        field_name = f"question_{self.question.id}"

        c_payload = {}
        if self.has_answer:
            c_payload = {
                "correct_answers": self.question_answers,
                "user_answers": self.user_answers,
            }
        w_payload = {}

        # if self.read_only:
        #     w_payload["disabled"] = "disabled"
        #     w_payload["readonly"] = "readonly"

        # Создаем виджеты с правильными атрибутами
        widgets = {
            Question.RADIO: ValidatedRadioSelect(attrs={"class": "form-check-input", **w_payload}, **c_payload),
            Question.SELECT: ValidatedSelect(attrs={"class": "form-select", **w_payload}, **c_payload),
            Question.SELECT_MULTIPLE: ValidatedCheckboxSelectMultiple(
                attrs={"class": "form-check-input", **w_payload}, **c_payload
            ),
            Question.TEXT: forms.Textarea(attrs={"rows": 4, "class": "form-control"}),
            Question.SHORT_TEXT: forms.TextInput(attrs={"class": "form-control"}),
            Question.INTEGER: forms.NumberInput(attrs={"class": "form-control"}),
            Question.FLOAT: forms.NumberInput(attrs={"class": "form-control", "step": "0.01"}),
            Question.DATE: forms.DateInput(attrs={"class": "form-control", "type": "date"}),
        }
        widget = widgets.get(self.question.type, forms.TextInput(attrs={"class": "form-control"}))

        fields = {
            Question.TEXT: forms.CharField,
            Question.SHORT_TEXT: forms.CharField,
            Question.RADIO: forms.ChoiceField,
            Question.SELECT: forms.ChoiceField,
            Question.SELECT_MULTIPLE: forms.MultipleChoiceField,
            Question.INTEGER: forms.IntegerField,
            Question.FLOAT: forms.FloatField,
            Question.DATE: forms.DateField,
        }

        field_payload = {}
        if self.question.type in [Question.RADIO, Question.SELECT, Question.SELECT_MULTIPLE]:
            field_payload = {
                "choices": [(choice.strip(), choice.strip()) for choice in self.question.get_clean_choices()],
            }

        self.fields[field_name] = fields[self.question.type](
            label=self.question.text,
            widget=widget,
            required=self.question.required,
            **field_payload,
        )

        # Настраиваем FormHelper для crispy forms
        self.helper = FormHelper()
        self.helper.form_method = "post"
        self.helper.form_class = "space-e"
        self.helper.form_id = "form-question"

        layout_items = [
            Field(
                field_name,
                css_class=f"form-option-group {'inactive' if self.has_answer else ''}",
                wrapper_class="input-style-1",
            ),
            Div(
                self._prepare_submit_button(),
                css_class="mt-4",
            ),
        ]

        if self.question.hint and not self.has_answer:
            layout_items.insert(
                1,
                Div(
                    self._prepare_hint_button(),
                    css_class="mt-6",
                ),
            )

        if self.question.explanation and self.has_answer:
            layout_items.insert(
                1,
                Div(
                    self._prepare_explanation_button(),
                    css_class="mt-6",
                ),
            )

        self.helper.layout = Layout(*layout_items)

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

    def _prepare_hint_button(self):
        """Создает кнопку с аккордеоном для отображения подсказки вопроса"""
        return self._prepare_spoiler_button(_("Hint"), "hint", "ti ti-bell")

    def _prepare_explanation_button(self):
        """Создает кнопку с аккордеоном для отображения объяснения вопроса"""
        return self._prepare_spoiler_button(
            _("Explanation"),
            "explanation",
            "ti ti-help-circle",
            collapsed=self.is_correct_answer,
        )

    def _prepare_submit_button(self):
        if self.has_answer and self.current_question_index == self.survey.total_questions:
            button_text = _("Finish survey and go to results")
            next_url = self.response.get_absolute_url()
            submit_button = Button(
                "finish_survey",
                button_text,
                css_class="btn btn-success btn-lg w-100",
                onclick=f"window.location.href='{next_url}'",
                css_id="finish-survey-btn",
            )
        elif not self.has_answer:
            button_text = _("Check your answer")
            submit_button = Submit(
                "action_add",
                button_text,
                css_class="btn btn-primary btn-lg w-100",
                css_id="submit-answer-btn",
            )
        elif self.has_answer:
            button_text = _("Next question")
            next_url = reverse("survey:question-detail", kwargs={"survey_id": self.survey.id}) + "?next=true"
            submit_button = Button(
                "next_question",
                button_text,
                css_class="btn btn-success btn-lg w-100",
                onclick=f"window.location.href='{next_url}'",
                css_id="next-question-btn",
            )

        return submit_button

    def _prepare_spoiler_button(self, name: str, field: str, icon: str, collapsed: bool = True):
        content = getattr(self.question, field)
        accordion_id = f"accordion-{field}"
        element_id = f"{field}-{self.question.id}"

        # TODO добавить логику скрытия/открытия по умолчанию

        element = f"""
        <div class="accordion markdown" id="{accordion_id}">
            <div class="accordion-item">

                <div class="accordion-header">

                    <button
                        class="btn btn-ghost btn-secondary w-100 d-flex align-items-center"
                        type="button"
                        data-bs-toggle="collapse"
                        data-bs-target="#{element_id}"
                        aria-expanded="false"
                        aria-controls="{element_id}">
                        <span class="d-flex align-items-center">
                            <i class="icon {icon} me-2"></i>{name}
                        </span>
                    </button>

                </div>

                <div
                    id="{element_id}"
                    class="accordion-collapse collapse {"show" if not collapsed else ""}"
                    data-bs-parent="#{accordion_id}">

                    <div class="accordion-body mt-3">{content}</div>

                </div>

            </div>
        </div>
        """

        return HTML(element)
