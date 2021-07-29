# Generated by Django 3.2.5 on 2021-07-28 20:10

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('api', '0008_alter_workspace_options'),
    ]

    operations = [
        migrations.AlterModelOptions(
            name='workspace',
            options={'ordering': ['id'], 'permissions': [('workspace.own_workspace', 'Owns the workspace'), ('workspace.maintain_workspace', 'May grant all roles but owner on the workspace'), ('workspace.write_workspace', 'May write to and remove from the workspace'), ('workspace.read_workspace', 'May read and perform non-mutating queries on the workspace')]},
        ),
    ]
