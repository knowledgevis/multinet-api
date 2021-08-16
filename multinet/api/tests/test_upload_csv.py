import csv
import pathlib
from typing import Dict
import uuid

from django.contrib.auth.models import User
import pytest
from rest_framework.response import Response

from multinet.api.models.upload import Upload
from multinet.api.models.workspace import Workspace, WorkspaceRole, WorkspaceRoleChoice
from multinet.api.tasks.process.utils import str_to_number
from multinet.api.tests.fuzzy import (
    INTEGER_ID_RE,
    TIMESTAMP_RE,
    dict_to_fuzzy_arango_doc,
    s3_file_field_re,
    workspace_re,
)
from multinet.api.tests.utils import get_field_value

data_dir = pathlib.Path(__file__).parent / 'data'


@pytest.fixture
def airports_csv(workspace: Workspace, user: User, authenticated_api_client, s3ff_client) -> Dict:
    workspace.set_user_permission(user, WorkspaceRoleChoice.WRITER)

    data_file = data_dir / 'airports.csv'
    field_value = get_field_value(data_file, s3ff_client)
    # Model creation request
    table_name = f't{uuid.uuid4().hex}'
    r: Response = authenticated_api_client.post(
        f'/api/workspaces/{workspace.name}/uploads/csv/',
        {
            'field_value': field_value,
            'edge': False,
            'table_name': table_name,
            'columns': {
                'latitude': 'number',
                'longitude': 'number',
                'altitude': 'number',
                'timezone': 'number',
                'year built': 'number',
            },
        },
        format='json',
    )
    WorkspaceRole.objects.filter(workspace=workspace, user=user).delete()
    return {
        'response': r,
        'table_name': table_name,
        'data_file': data_file,
    }


@pytest.mark.django_db
def test_create_upload_model_csv(workspace: Workspace, user: User, airports_csv):
    """Test just the response of the model creation, not the task itself."""
    r = airports_csv['response']
    data_file = airports_csv['data_file']

    assert r.status_code == 200
    assert r.json() == {
        'id': INTEGER_ID_RE,
        'workspace': workspace_re(workspace),
        'blob': s3_file_field_re(data_file.name),
        'user': user.username,
        'data_type': Upload.DataType.CSV,
        'error_messages': None,
        'status': Upload.UploadStatus.PENDING,
        'created': TIMESTAMP_RE,
        'modified': TIMESTAMP_RE,
    }


@pytest.mark.django_db
def test_create_upload_model_invalid_columns(
    workspace: Workspace, user: User, authenticated_api_client
):
    workspace.set_user_permission(user, WorkspaceRoleChoice.WRITER)
    r: Response = authenticated_api_client.post(
        f'/api/workspaces/{workspace.name}/uploads/csv/',
        {
            # Not an issue to specify invalid field_value, as that's checked after columns,
            # so the request will return before that is checked
            'field_value': 'field_value',
            'edge': False,
            'table_name': 'table',
            'columns': {'foo': 'invalid'},
        },
        format='json',
    )

    assert r.status_code == 400
    assert r.json() == {'columns': {'foo': ['"invalid" is not a valid choice.']}}


@pytest.mark.django_db
@pytest.mark.parametrize('permission,status_code', [(None, 404), (WorkspaceRoleChoice.READER, 403)])
def test_create_upload_model_csv_invalid_permissions(
    workspace: Workspace,
    user: User,
    authenticated_api_client,
    s3ff_client,
    permission: WorkspaceRoleChoice,
    status_code: int,
):
    """Test that a user with insufficient permissions is forbidden from a POST request."""
    if permission is not None:
        workspace.set_user_permission(user, permission)
    data_file = data_dir / 'airports.csv'
    field_value = get_field_value(data_file, s3ff_client)
    table_name = f't{uuid.uuid4().hex}'
    r: Response = authenticated_api_client.post(
        f'/api/workspaces/{workspace.name}/uploads/csv/',
        {
            'field_value': field_value,
            'edge': False,
            'table_name': table_name,
            'columns': {
                'latitude': 'number',
                'longitude': 'number',
                'altitude': 'number',
                'timezone': 'number',
                'year built': 'number',
            },
        },
        format='json',
    )
    assert r.status_code == status_code


@pytest.mark.django_db
def test_create_upload_model_invalid_field_value(
    workspace: Workspace, user: User, authenticated_api_client
):
    workspace.set_user_permission(user, WorkspaceRoleChoice.WRITER)
    r: Response = authenticated_api_client.post(
        f'/api/workspaces/{workspace.name}/uploads/csv/',
        {
            'field_value': 'field_value',
            'edge': False,
            'table_name': 'table',
        },
        format='json',
    )

    assert r.status_code == 400
    assert r.json() == {'field_value': ['field_value is not a valid signed string.']}


@pytest.mark.django_db
def test_upload_valid_csv_task_response(
    workspace: Workspace, user: User, authenticated_api_client, airports_csv
):
    """Test just the response of the model creation, not the task itself."""
    # Get upload info
    workspace.set_user_permission(user, WorkspaceRoleChoice.WRITER)
    r = airports_csv['response']
    data_file = airports_csv['data_file']
    table_name = airports_csv['table_name']

    # Since we're running with celery_task_always_eager=True, this job is finished
    r: Response = authenticated_api_client.get(
        f'/api/workspaces/{workspace.name}/uploads/{r.json()["id"]}/'
    )

    r_json = r.json()
    assert r.status_code == 200
    assert r_json['status'] == Upload.UploadStatus.FINISHED
    assert r_json['error_messages'] is None

    # Check that table is created
    r: Response = authenticated_api_client.get(
        f'/api/workspaces/{workspace.name}/tables/{table_name}/'
    )
    assert r.status_code == 200

    # Check that data was ingested correctly
    r: Response = authenticated_api_client.get(
        f'/api/workspaces/{workspace.name}/tables/{table_name}/rows/'
    )

    assert r.status_code == 200
    r_json = r.json()
    results = r_json['results']

    # Get source data rows
    with open(data_file) as file_stream:
        rows = [row for row in csv.DictReader(file_stream)]

    # Check rows themselves
    assert r_json['count'] == len(rows)
    for i, row in enumerate(rows):
        result = results[i]

        # Convert these keys so we can compare documents
        for key in ['latitude', 'longitude', 'altitude', 'timezone', 'year built']:
            row[key] = str_to_number(row[key])

        # Assert documents match
        assert result == dict_to_fuzzy_arango_doc(row)
