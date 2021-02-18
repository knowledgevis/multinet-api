# Generated by Django 3.1.6 on 2021-02-16 18:33

from django.db import migrations, models
import django_extensions.db.fields


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ('api', '0001_default_site'),
    ]

    operations = [
        migrations.CreateModel(
            name='Workspace',
            fields=[
                (
                    'id',
                    models.AutoField(
                        auto_created=True, primary_key=True, serialize=False, verbose_name='ID'
                    ),
                ),
                (
                    'created',
                    django_extensions.db.fields.CreationDateTimeField(
                        auto_now_add=True, verbose_name='created'
                    ),
                ),
                (
                    'modified',
                    django_extensions.db.fields.ModificationDateTimeField(
                        auto_now=True, verbose_name='modified'
                    ),
                ),
                ('name', models.CharField(max_length=300, unique=True)),
                ('arango_db_name', models.CharField(max_length=300, unique=True)),
            ],
            options={
                'ordering': ['id'],
                'permissions': [('owner', 'Owns the workspace')],
            },
        ),
    ]
