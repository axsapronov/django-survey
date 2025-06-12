# Generated manually for django-survey

from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("survey", "0014_survey_redirect_url"),
    ]

    operations = [
        migrations.AddField(
            model_name="survey",
            name="multiple_responses",
            field=models.BooleanField(default=False, verbose_name="Allow multiple responses from same user"),
        ),
    ]
