# Generated by Django 5.2 on 2025-05-14 16:05

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("system", "0003_chatbotintegrationlog"),
    ]

    operations = [
        migrations.AddField(
            model_name="systemsettings",
            name="stripe_publishable_key",
            field=models.TextField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name="systemsettings",
            name="stripe_secret_key",
            field=models.TextField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name="systemsettings",
            name="stripe_webhook_secret",
            field=models.TextField(blank=True, null=True),
        ),
    ]
