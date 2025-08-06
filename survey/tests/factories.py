import random
import uuid
from datetime import timedelta

from django.contrib.auth.models import User
from django.utils.timezone import now
from factory import Faker
from factory import LazyAttribute
from factory import SubFactory
from factory.declarations import SubFactory
from factory.django import DjangoModelFactory

from survey.models import Answer
from survey.models import Category
from survey.models import Question
from survey.models import Response
from survey.models import Survey


class UserFactory(DjangoModelFactory):
    class Meta:
        model = User

    username = Faker("user_name")
    email = Faker("email")
    first_name = Faker("first_name")
    last_name = Faker("last_name")
    is_active = True


class SurveyFactory(DjangoModelFactory):
    class Meta:
        model = Survey

    name = Faker("sentence", nb_words=3)
    description = Faker("text", max_nb_chars=200)
    is_published = True
    need_logged_user = False
    editable_answers = True
    multiple_responses = False
    display_method = Survey.ALL_IN_ONE_PAGE
    publish_date = LazyAttribute(lambda x: now().date())
    expire_date = LazyAttribute(lambda x: now().date() + timedelta(days=30))


class CategoryFactory(DjangoModelFactory):
    class Meta:
        model = Category

    name = Faker("word")
    description = Faker("text", max_nb_chars=100)
    survey = SubFactory(SurveyFactory)


class QuestionFactory(DjangoModelFactory):
    class Meta:
        model = Question

    text = Faker("sentence", nb_words=5)
    order = LazyAttribute(lambda x: random.randint(1, 100))
    required = True
    survey = SubFactory(SurveyFactory)
    type = Question.TEXT
    choices = ""
    correct_answer = ""


class ResponseFactory(DjangoModelFactory):
    class Meta:
        model = Response

    survey = SubFactory(SurveyFactory)
    user = None
    interview_uuid = LazyAttribute(lambda x: str(uuid.uuid4()))


class AnswerFactory(DjangoModelFactory):
    class Meta:
        model = Answer

    question = SubFactory(QuestionFactory)
    response = SubFactory(ResponseFactory)
    body = Faker("sentence", nb_words=3)
