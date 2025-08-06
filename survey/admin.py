from django.contrib import admin
from django.utils.html import mark_safe
from django.utils.translation import gettext_lazy as _
from django.utils.translation import ngettext

from survey.models import Answer
from survey.models import Category
from survey.models import Question
from survey.models import Response
from survey.models import Survey


@admin.action(description=_("Mark selected surveys as published"))
def make_published(modeladmin, request, queryset):
    """
    Mark the given survey as published
    """
    count = queryset.update(is_published=True)
    message = ngettext(
        "%(count)d survey was successfully marked as published.",
        "%(count)d surveys were successfully marked as published",
        count,
    ) % {"count": count}
    modeladmin.message_user(request, message)


class QuestionInline(admin.StackedInline):
    model = Question
    ordering = ("order", "category")
    extra = 1
    fields = (
        "text",
        "type",
        "order",
        "required",
        "category",
        "choices",
        "correct_answer",
    )

    def get_formset(self, request, survey_obj, *args, **kwargs):
        formset = super().get_formset(request, survey_obj, *args, **kwargs)
        if survey_obj:
            formset.form.base_fields["category"].queryset = survey_obj.categories.all()
        return formset


class CategoryInline(admin.TabularInline):
    model = Category
    extra = 0


@admin.register(Survey)
class SurveyAdmin(admin.ModelAdmin):
    list_display = (
        "name",
        "id",
        "is_published",
        "need_logged_user",
        "multiple_responses",
        "template",
        "page",
        "total_questions_display",
    )
    list_filter = (
        "is_published",
        "need_logged_user",
        "multiple_responses",
    )
    search_fields = ("name", "description")
    inlines = [CategoryInline, QuestionInline]
    actions = [make_published]

    @admin.display(description="Page")
    def page(self, obj):
        url = obj.get_absolute_url()
        return mark_safe(f"<a target='_blank'  href='{url}'>Page</a>")

    @admin.display(description=_("Total questions"))
    def total_questions_display(self, obj):
        return obj.total_questions


class AnswerBaseInline(admin.StackedInline):
    fields = (
        "question",
        "body",
        "is_correct",
        "correct_answer_display",
    )
    readonly_fields = (
        "question",
        "is_correct",
        "correct_answer_display",
    )
    extra = 0
    model = Answer

    @admin.display(description=_("Is correct"), boolean=True)
    def is_correct(self, obj):
        return obj.is_correct

    @admin.display(description=_("Correct answer"))
    def correct_answer_display(self, obj):
        if obj.question and obj.question.correct_answer:
            return obj.question.correct_answer
        return _("Not set")


@admin.register(Response)
class ResponseAdmin(admin.ModelAdmin):
    list_display = (
        "interview_uuid",
        "survey",
        "user",
        "created",
        "correct_answers_display",
    )
    list_filter = ("survey", "created")
    date_hierarchy = "created"
    inlines = [AnswerBaseInline]
    search_fields = ("interview_uuid", "user__username")
    readonly_fields = (
        "survey",
        "user",
        "interview_uuid",
        "created",
        "updated",
        "correct_answers_display",
    )

    def get_queryset(self, request):
        return super().get_queryset(request).prefetch_related("answers__question")

    @admin.display(description=_("Correct answers"))
    def correct_answers_display(self, obj):
        return f"{obj.correct_answers_count} / {obj.total_answers_count}"


@admin.register(Question)
class QuestionAdmin(admin.ModelAdmin):
    list_display = (
        "text",
        "survey",
        "type",
        "order",
        "required",
        "category",
    )
    list_filter = (
        "type",
        "required",
        "category",
    )
    search_fields = (
        "text",
        "survey__name",
    )
    inlines = [AnswerBaseInline]


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = (
        "name",
        "survey",
        "order",
        "description",
    )
    list_filter = ("survey",)
    search_fields = (
        "name",
        "survey__name",
    )


@admin.register(Answer)
class AnswerAdmin(admin.ModelAdmin):
    list_display = (
        "question_text",
        "response_survey_name",
        "response_user_username",
        "body",
        "created",
    )
    list_filter = ("created",)
    search_fields = (
        "question__text",
        "response__interview_uuid",
    )

    raw_id_fields = (
        "question",
        "response",
    )

    def get_queryset(self, request):
        return (
            super()
            .get_queryset(request)
            .prefetch_related(
                "question",
                "response",
                "response__user",
                "response__survey",
            )
        )

    @admin.display(description=_("Question"))
    def question_text(self, obj):
        return obj.question.text if obj.question else ""

    @admin.display(description=_("Survey"))
    def response_survey_name(self, obj):
        return obj.response.survey.name if obj.response and obj.response.survey else ""

    @admin.display(description=_("User"))
    def response_user_username(self, obj):
        return obj.response.user.username if obj.response and obj.response.user else ""
