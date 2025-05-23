# Generated by Django 4.2.20 on 2025-04-29 20:30

from django.db import migrations, models
import django.db.models.deletion
import django.utils.timezone
import gearshare.models


class Migration(migrations.Migration):

    dependencies = [
        ("gearshare", "0019_item_due_date"),
    ]

    operations = [
        migrations.AlterModelOptions(
            name="borrowrequest",
            options={"ordering": ["-request_date"]},
        ),
        migrations.AlterModelOptions(
            name="collectionrequest",
            options={"ordering": ["-request_date"]},
        ),
        migrations.RemoveField(
            model_name="borrowrequest",
            name="due_date",
        ),
        migrations.AlterField(
            model_name="borrowrequest",
            name="requested_end_date",
            field=models.DateField(default=gearshare.models.default_end_date),
        ),
        migrations.AlterField(
            model_name="borrowrequest",
            name="requested_start_date",
            field=models.DateField(default=django.utils.timezone.now),
        ),
        migrations.AlterField(
            model_name="item",
            name="user",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="borrowed_items",
                to="gearshare.profile",
            ),
        ),
    ]
