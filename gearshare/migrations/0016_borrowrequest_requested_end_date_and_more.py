# Generated by Django 4.2.20 on 2025-04-29 17:57

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("gearshare", "0015_merge_20250428_1925"),
    ]

    operations = [
        migrations.AddField(
            model_name="borrowrequest",
            name="requested_end_date",
            field=models.DateField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name="borrowrequest",
            name="requested_start_date",
            field=models.DateField(blank=True, null=True),
        ),
    ]
