# Generated by Django 4.2.20 on 2025-04-28 02:23

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("gearshare", "0010_borrowrequest_delete_request"),
    ]

    operations = [
        migrations.AddField(
            model_name="borrowrequest",
            name="due_date",
            field=models.DateField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name="borrowrequest",
            name="is_approved",
            field=models.BooleanField(default=False),
        ),
        migrations.AddField(
            model_name="item",
            name="category",
            field=models.CharField(
                choices=[
                    ("camping", "Camping"),
                    ("climbing", "Climbing"),
                    ("water", "Water Sports"),
                    ("hiking", "Hiking"),
                    ("other", "Other"),
                ],
                default="other",
                max_length=20,
            ),
        ),
        migrations.AddField(
            model_name="item",
            name="last_updated",
            field=models.DateTimeField(auto_now=True),
        ),
        migrations.AddField(
            model_name="item",
            name="usage_count",
            field=models.PositiveIntegerField(default=0),
        ),
        migrations.AlterField(
            model_name="item",
            name="condition",
            field=models.CharField(
                choices=[
                    ("new", "New"),
                    ("good", "Good"),
                    ("fair", "Fair"),
                    ("poor", "Needs Repair"),
                    ("unusable", "Unusable"),
                ],
                default="good",
                max_length=20,
            ),
        ),
        migrations.AlterField(
            model_name="item",
            name="status",
            field=models.CharField(
                choices=[
                    ("available", "Available"),
                    ("checked_out", "Checked Out"),
                    ("reserved", "Reserved"),
                    ("maintenance", "Under Maintenance"),
                    ("lost", "Lost/Damaged"),
                ],
                default="available",
                max_length=20,
            ),
        ),
    ]
