import itertools

from django.contrib.auth.models import User
from faker import Faker
from guardian.shortcuts import assign_perm, get_user_perms
import pytest
from pytest_factoryboy import register
from rest_framework.test import APIClient
from s3_file_field.testing import S3FileFieldTestClient

from multinet.api.models import Network, Table, Workspace
from multinet.api.tests.utils import generate_arango_documents
from multinet.api.utils.arango import arango_system_db
from multinet.api.utils.workspace_permissions import WorkspacePermission

from .factories import (
    NetworkFactory,
    PrivateWorkspaceFactory,
    PublicWorkspaceFactory,
    TableFactory,
    UserFactory,
    WorkspaceFactory,
)


@pytest.fixture
def api_client() -> APIClient:
    return APIClient()


@pytest.fixture
def authenticated_api_client(user: User) -> APIClient:
    client = APIClient()
    client.force_authenticate(user=user)
    return client


@pytest.fixture()
def s3ff_client(authenticated_api_client):
    return S3FileFieldTestClient(
        authenticated_api_client,  # The test APIClient instance
        '/api/s3-upload',  # The (relative) path mounted in urlpatterns
    )


@pytest.fixture
def public_workspace(workspace: Workspace) -> Workspace:
    workspace.public = True
    workspace.save()
    return workspace


@pytest.fixture
def owned_workspace(user: User, workspace: Workspace) -> Workspace:
    """Return a workspace with the `user` fixture as an owner."""
    assign_perm(WorkspacePermission.owner.name, user, workspace)
    return workspace


@pytest.fixture
def writeable_workspace(user: User, workspace: Workspace) -> Workspace:
    """Return a workspace with the `user` fixture as a writer"""
    workspace.set_user_permission(user, WorkspacePermission.writer)
    return workspace


@pytest.fixture
def readable_workspace(user: User, workspace: Workspace) -> Workspace:
    """Return a workspace with the `user` fixture as a reader."""
    workspace.set_user_permission(user, WorkspacePermission.reader)
    print("User in fixture: " + str(user))
    print("User perms in fixture: " + str(list(get_user_perms(user, workspace))))
    return workspace


@pytest.fixture
def populated_node_table(workspace: Workspace) -> Table:
    table: Table = Table.objects.create(name=Faker().pystr(), edge=False, workspace=workspace)

    nodes = generate_arango_documents(5)
    table.put_rows(nodes)

    return table


@pytest.fixture
def populated_edge_table(workspace: Workspace, populated_node_table: Table) -> Table:
    table: Table = Table.objects.create(name=Faker().pystr(), edge=True, workspace=workspace)

    nodes = list(populated_node_table.get_rows())
    edges = [{'_from': a['_id'], '_to': b['_id']} for a, b in itertools.combinations(nodes, 2)]
    table.put_rows(edges)

    return table


@pytest.fixture
def populated_network(readable_workspace: Workspace, populated_edge_table: Table) -> Network:
    node_tables = list(populated_edge_table.find_referenced_node_tables().keys())
    network_name = Faker().pystr()
    return Network.create_with_edge_definition(
        name=network_name,
        workspace=readable_workspace,
        edge_table=populated_edge_table.name,
        node_tables=node_tables,
    )


@pytest.fixture
def public_populated_network(public_workspace: Workspace, populated_edge_table: Table) -> Network:
    node_tables = list(populated_edge_table.find_referenced_node_tables().keys())
    network_name = Faker().pystr()
    return Network.create_with_edge_definition(
        name=network_name,
        workspace=public_workspace,
        edge_table=populated_edge_table.name,
        node_tables=node_tables,
    )


@pytest.fixture
def private_populated_network(workspace: Workspace, populated_edge_table: Table) -> Network:
    node_tables = list(populated_edge_table.find_referenced_node_tables().keys())
    network_name = Faker().pystr()
    return Network.create_with_edge_definition(
        name=network_name,
        workspace=workspace,
        edge_table=populated_edge_table.name,
        node_tables=node_tables,
    )


@pytest.fixture
def writeable_populated_network(
    writeable_workspace: Workspace, populated_edge_table: Table
) -> Network:
    node_tables = list(populated_edge_table.find_referenced_node_tables().keys())
    network_name = Faker().pystr()
    return Network.create_with_edge_definition(
        name=network_name,
        workspace=writeable_workspace,
        edge_table=populated_edge_table.name,
        node_tables=node_tables,
    )


def pytest_configure():
    # Register which databases exist before the function is run.
    pytest.before_session_arango_databases = set(arango_system_db().databases())


def pytest_sessionfinish(session, exitstatus):
    # Remove any databases created since the session start. This is needed because pytest's
    # `pytest.mark.django_db` decorator doesn't run the model save/delete methods, meaning the sync
    # between arangodb and django doesn't happen.

    for db in arango_system_db().databases():
        if db not in pytest.before_session_arango_databases:
            arango_system_db().delete_database(db, ignore_missing=True)


register(UserFactory)
register(WorkspaceFactory)
register(PublicWorkspaceFactory)
register(PrivateWorkspaceFactory)
register(NetworkFactory)
register(TableFactory)
