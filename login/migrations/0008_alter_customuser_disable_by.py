# Generated by Django 5.2 on 2025-04-11 17:15

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('login', '0007_customuser_department'),
    ]

    operations = [
        migrations.AlterField(
            model_name='customuser',
            name='disable_by',
            field=models.CharField(blank=True, max_length=50, null=True),
        ),
    ]
