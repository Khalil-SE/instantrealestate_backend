# Generated by Django 5.2 on 2025-05-21 20:46

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("subscriptions", "0005_subscriptionhistory_hosted_invoice_url_and_more"),
    ]

    operations = [
        migrations.AddField(
            model_name="subscriptionplan",
            name="description",
            field=models.TextField(blank=True),
        ),
    ]
