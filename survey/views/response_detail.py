import logging

from django.conf import settings
from django.http import Http404
from django.shortcuts import get_object_or_404, redirect, render, reverse
from django.views.generic import View

from survey.forms import ResponseForm
from survey.models import Response

LOGGER = logging.getLogger(__name__)


class ResponseDetail(View):
    def get(self, request, *args, **kwargs):
        response_id = kwargs.get("response_id")
        step = kwargs.get("step", 0)

        # Получаем Response объект
        response = get_object_or_404(Response, pk=response_id)
        survey = response.survey

        # Проверяем, что пользователь имеет право просматривать этот Response
        if survey.need_logged_user and not request.user.is_authenticated:
            return redirect(f"{settings.LOGIN_URL}?next={request.path}")

        # Если пользователь авторизован, проверяем что это его Response
        if request.user.is_authenticated and response.user != request.user:
            # Для анонимных ответов разрешаем просмотр любому
            if response.user is not None:
                raise Http404("Response not found")

        # Выбираем шаблон
        if survey.template is not None and len(survey.template) > 4:
            template_name = survey.template
        else:
            if survey.is_all_in_one_page():
                template_name = "survey/one_page_survey.html"
            else:
                template_name = "survey/survey.html"

        # Создаем форму с предзаполненными данными из существующего Response
        form = ResponseForm(survey=survey, user=request.user, step=step, response_id=response_id)
        categories = form.current_categories()

        asset_context = {
            # If any of the widgets of the current form has a "date" class, flatpickr will be loaded into the template
            "flatpickr": any(field.widget.attrs.get("class") == "date" for _, field in form.fields.items())
        }
        context = {
            "response_form": form,
            "survey": survey,
            "categories": categories,
            "step": step,
            "asset_context": asset_context,
            "response": response,
            "is_response_edit": True,
        }

        return render(request, template_name, context)

    def post(self, request, *args, **kwargs):
        response_id = kwargs.get("response_id")
        response = get_object_or_404(Response, pk=response_id)
        survey = response.survey

        if survey.need_logged_user and not request.user.is_authenticated:
            return redirect(f"{settings.LOGIN_URL}?next={request.path}")

        # Проверяем права на редактирование
        if request.user.is_authenticated and response.user != request.user:
            if response.user is not None:
                raise Http404("Response not found")

        form = ResponseForm(
            request.POST, survey=survey, user=request.user, step=kwargs.get("step", 0), response_id=response_id
        )
        categories = form.current_categories()

        if not survey.editable_answers:
            LOGGER.info("Redirects to survey list after trying to edit non editable answer.")
            return redirect(reverse("survey-list"))

        context = {
            "response_form": form,
            "survey": survey,
            "categories": categories,
            "response": response,
            "is_response_edit": True,
        }
        if form.is_valid():
            return self.treat_valid_form(form, kwargs, request, survey, response)
        return self.handle_invalid_form(context, form, request, survey)

    @staticmethod
    def handle_invalid_form(context, form, request, survey):
        LOGGER.info("Non valid form: <%s>", form)
        if survey.template is not None and len(survey.template) > 4:
            template_name = survey.template
        else:
            if survey.is_all_in_one_page():
                template_name = "survey/one_page_survey.html"
            else:
                template_name = "survey/survey.html"
        return render(request, template_name, context)

    def treat_valid_form(self, form, kwargs, request, survey, response):
        session_key = "survey_response_{}".format(kwargs["response_id"])
        if session_key not in request.session:
            request.session[session_key] = {}
        for key, value in list(form.cleaned_data.items()):
            request.session[session_key][key] = value
            request.session.modified = True
        next_url = form.next_step_url_for_response(response.pk)
        saved_response = None
        if survey.is_all_in_one_page():
            saved_response = form.save()
        else:
            # when it's the last step
            if not form.has_next_step():
                save_form = ResponseForm(
                    request.session[session_key], survey=survey, user=request.user, response_id=response.pk
                )
                if save_form.is_valid():
                    saved_response = save_form.save()
                else:
                    LOGGER.warning("A step of the multipage form failed but should have been discovered before.")
        # if there is a next step
        if next_url is not None:
            return redirect(next_url)
        del request.session[session_key]
        if saved_response is None:
            return redirect(reverse("survey-list"))
        next_ = request.session.get("next", None)
        if next_ is not None:
            if "next" in request.session:
                del request.session["next"]
            return redirect(next_)
        return redirect(survey.redirect_url or "survey-confirmation", uuid=saved_response.interview_uuid)
