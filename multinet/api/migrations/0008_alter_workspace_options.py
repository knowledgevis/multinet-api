# Generated by Django 3.2.5 on 2021-07-28 18:52

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('api', '0007_auto_20210727_1549'),
    ]

    operations = [
        migrations.AlterModelOptions(
            name='workspace',
            options={'ordering': ['id'], 'permissions': [('workspace.own_workspace', 'Owns the workspace'), ('workspace.maintain_workspace', 'May grant all roles but owner on the workspace'), ('workspace.write_workspace', 'May write to and remove from the workspace'), ('workspace.read_workspace', 'May read and perform non-mutating queries on the workspace'), ('workspace.get_workspace', 'View the workspace and its tables and networks'), ('workspace.query_workspace', 'Write non-mutative queries on the workspace'), ('workspace.write_child_to_workspace', 'Create new tables and networks within a workspace'), ('workspace.remove_child_from_workspace', 'Delete tables and networks within a table'), ('workspace.rename_workspace', 'Rename a workspace'), ('workspace.delete_workspace', 'Delete a workspace itself'), ('workspace.grant_workspace', 'Assign roles on a workspace'), ('workspace.transfer_workspace', 'Transfer ownership of a workspace')]},
        ),
    ]
