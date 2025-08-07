import uuid
from datetime import timedelta
from functools import cached_property

from django.conf import settings
from django.db import models
from django.urls import reverse
from django.utils.timezone import now
from django.utils.translation import gettext_lazy as _
from meta.models import ModelMeta


def in_duration_day():
    return now() + timedelta(days=getattr(settings, "DEFAULT_SURVEY_PUBLISHING_DURATION", 7))


def get_default_survey_slug():
    return str(uuid.uuid4())


class Survey(ModelMeta, models.Model):
    ALL_IN_ONE_PAGE = 0
    BY_QUESTION = 1
    BY_CATEGORY = 2

    DISPLAY_METHOD_CHOICES = [
        (BY_QUESTION, _("By question")),
        (BY_CATEGORY, _("By category")),
        (ALL_IN_ONE_PAGE, _("All in one page")),
    ]

    order = models.PositiveIntegerField(
        verbose_name=_("Order"),
        default=100,
    )
    name = models.CharField(_("Name"), max_length=400)

    short_description = models.TextField(
        verbose_name=_("Short description"),
        max_length=255,
        blank=True,
        default="",
    )

    description = models.TextField(
        verbose_name=_("Description"),
        blank=True,
        default="",
    )

    # TODO - add
    # category = models.ForeignKey(
    #     "Category",
    #     on_delete=models.SET_NULL,
    #     null=True,
    #     blank=True,
    #     verbose_name=_("Category"),
    # )

    # TODO - добавить скорринг логику

    is_published = models.BooleanField(_("Users can see it and answer it"), default=True)
    need_logged_user = models.BooleanField(_("Only authenticated users can see it and answer it"))
    editable_answers = models.BooleanField(_("Users can edit their answers afterwards"), default=True)
    multiple_responses = models.BooleanField(_("Allow multiple responses from same user"), default=False)
    display_method = models.SmallIntegerField(
        _("Display method"), choices=DISPLAY_METHOD_CHOICES, default=ALL_IN_ONE_PAGE
    )
    template = models.CharField(_("Template"), max_length=255, null=True, blank=True)
    publish_date = models.DateField(_("Publication date"), blank=True, null=False, default=now)
    expire_date = models.DateField(_("Expiration date"), blank=True, null=False, default=in_duration_day)
    redirect_url = models.URLField(_("Redirect URL"), blank=True)

    gift_before = models.TextField(_("Gift before survey"), blank=True, null=True)
    gift_after = models.TextField(_("Gift after survey"), blank=True, null=True)

    properties = models.JSONField(
        default=dict,
        blank=True,
        verbose_name=_("Properties"),
        help_text=_("Additional information"),
    )

    _metadata = {
        "title": "name",
        "description": "short_description",
        "published_time": "publish_date",
        "modified_time": "publish_date",
    }

    class Meta:
        verbose_name = _("Survey")
        verbose_name_plural = _("Surveys")

    def __str__(self):
        return str(self.name)

    @property
    def safe_name(self):
        return self.name.replace(" ", "_").encode("utf-8").decode("ISO-8859-1")

    def latest_answer_date(self):
        """Return the latest answer date.

        Return None is there is no response."""
        min_ = None
        for response in self.responses.all():
            if min_ is None or min_ < response.updated:
                min_ = response.updated
        return min_

    def get_absolute_url(self):
        return reverse("survey:survey-detail", kwargs={"survey_id": self.pk})

    def non_empty_categories(self):
        return [x for x in list(self.categories.order_by("order", "id")) if x.questions.count() > 0]

    def is_all_in_one_page(self):
        return self.display_method == self.ALL_IN_ONE_PAGE

    @cached_property
    def total_questions(self) -> int:
        """
        Returns the total number of questions in the survey.

        Returns:
            int: The total number of questions
        """
        return self.questions.count()

    @property
    def template_name(self):
        if self.template is not None and len(self.template) > 4:
            return self.template

        if self.is_all_in_one_page():
            return "survey/survey_detail_one_page.html"
        else:
            return "survey/survey_detail.html"
