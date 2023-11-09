# Generated by Django 4.2.6 on 2023-11-08 10:29

from django.db import migrations, models
import django_countries.fields


class Migration(migrations.Migration):

    dependencies = [
        ('users', '0007_country_customuser_gender_customuser_location'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='customuser',
            name='location',
        ),
        migrations.AddField(
            model_name='customuser',
            name='country',
            field=models.CharField(blank=True, default='', null=True, verbose_name=django_countries.fields.CountryField),
        ),
        migrations.DeleteModel(
            name='Country',
        ),
    ]
