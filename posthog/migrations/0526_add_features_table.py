# Generated by Django 3.2.18 on 2023-06-22 11:08

from django.db import migrations, models
from django.utils import timezone


class Migration(migrations.Migration):
    dependencies = [
        ("posthog", "0525_hog_function_transpiled"),
    ]

    operations = [
        migrations.CreateModel(
            name="Feature",
            fields=[
                ("id", models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("team", models.ForeignKey(on_delete=models.deletion.CASCADE, to="posthog.team")),
                ("name", models.CharField(blank=True, max_length=400)),
                ("description", models.TextField(blank=True)),
                ("issue_url", models.URLField(blank=True)),
                ("created_at", models.DateTimeField(default=timezone.now)),
                ("updated_at", models.DateTimeField(auto_now=True)),
            ],
        ),
        migrations.AddField(
            model_name="featureflag",
            name="feature",
            field=models.ForeignKey(to="posthog.feature"),
        ),
        migrations.AddField(
            model_name="featureflag",
            name="feature",
            field=models.ForeignKey(to="posthog.feature"),
        ),
        migrations.AddField(
            model_name="experiment",
            name="feature",
            field=models.ForeignKey(to="posthog.feature"),
        ),
    ]
