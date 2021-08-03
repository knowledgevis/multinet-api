from typing import List

from faker import Faker
import pytest
from rest_framework.test import APIClient

from multinet.api.models import Network, Table, Workspace
from multinet.api.tests.factories import (
    NetworkFactory,
    PrivateWorkspaceFactory,
    PublicWorkspaceFactory,
)
from multinet.api.tests.utils import assert_limit_offset_results

from .fuzzy import INTEGER_ID_RE, TIMESTAMP_RE


@pytest.mark.django_db
def test_network_rest_list(
    network_factory: NetworkFactory,
    readable_workspace: Workspace,
    authenticated_api_client: APIClient,
):
    """
    Test that an authenticated user can see networks on a private workspace
    for which that user has reader permission.
    """
    fake = Faker()
    network_names: List[str] = [
        network_factory(name=fake.pystr(), workspace=readable_workspace).name for _ in range(3)
    ]

    r = authenticated_api_client.get(f'/api/workspaces/{readable_workspace.name}/networks/')
    r_json = r.json()

    # Test that we get the expected results from both django and arango
    arango_db = readable_workspace.get_arango_db()
    assert r_json['count'] == len(network_names)
    for network in r_json['results']:
        assert network['name'] in network_names
        assert arango_db.has_graph(network['name'])


@pytest.mark.django_db
def test_network_rest_list_public(
    network_factory: NetworkFactory,
    public_workspace_factory: PublicWorkspaceFactory,
    authenticated_api_client: APIClient,
):
    """Test that an authenticated user can see networks on a public workspace."""
    fake = Faker()
    public_workspace: Workspace = public_workspace_factory()
    network_names: List[str] = [
        network_factory(name=fake.pystr(), workspace=public_workspace).name for _ in range(3)
    ]
    r = authenticated_api_client.get(f'/api/workspaces/{public_workspace.name}/networks/')
    r_json = r.json()

    arango_db = public_workspace.get_arango_db()
    assert r_json['count'] == len(network_names)
    for network in r_json['results']:
        assert network['name'] in network_names
        assert arango_db.has_graph(network['name'])


@pytest.mark.django_db
def test_network_rest_list_private(
    network_factory: NetworkFactory,
    private_workspace_factory: PrivateWorkspaceFactory,
    authenticated_api_client: APIClient,
):
    """
    Test that an authenticated user can not see networks on a private workspace.
    For which they have no permissions.
    """
    fake = Faker()
    private_workspace: Workspace = private_workspace_factory()
    for _ in range(3):
        network_factory(name=fake.pystr(), workspace=private_workspace)

    r = authenticated_api_client.get(f'/api/workspaces/{private_workspace.name}/networks/')
    assert r.status_code == 404


@pytest.mark.django_db
def test_network_rest_create(
    writeable_workspace: Workspace,
    populated_edge_table: Table,
    populated_node_table: Table,
    authenticated_api_client: APIClient,
):
    network_name = 'network'
    r = authenticated_api_client.post(
        f'/api/workspaces/{writeable_workspace.name}/networks/',
        {'name': network_name, 'edge_table': populated_edge_table.name},
        format='json',
    )

    assert r.json() == {
        'name': network_name,
        'node_count': len(populated_node_table.get_rows()),
        'edge_count': len(populated_edge_table.get_rows()),
        'id': INTEGER_ID_RE,
        'created': TIMESTAMP_RE,
        'modified': TIMESTAMP_RE,
        'workspace': {
            'id': writeable_workspace.pk,
            'name': writeable_workspace.name,
            'created': TIMESTAMP_RE,
            'modified': TIMESTAMP_RE,
            'arango_db_name': writeable_workspace.arango_db_name,
            'public': False,
        },
    }

    # Django will raise an exception if this fails, implicitly validating that the object exists
    network: Network = Network.objects.get(name=network_name)

    # Assert that object was created in arango
    assert writeable_workspace.get_arango_db().has_graph(network.name)


@pytest.mark.django_db
def test_network_rest_create_forbidden(
    readable_workspace: Workspace,
    populated_edge_table: Table,
    populated_node_table: Table,
    authenticated_api_client: APIClient,
):
    network_name = 'network'
    r = authenticated_api_client.post(
        f'/api/workspaces/{readable_workspace.name}/networks/',
        {'name': network_name, 'edge_table': populated_edge_table.name},
        format='json',
    )
    assert r.status_code == 403


@pytest.mark.django_db
def test_network_rest_create_no_access(
    private_workspace_factory: PrivateWorkspaceFactory,
    populated_edge_table: Table,
    authenticated_api_client: APIClient,
):
    private_workspace = private_workspace_factory()
    network_name = 'network'
    r = authenticated_api_client.post(
        f'/api/workspaces/{private_workspace.name}/networks/',
        {'name': network_name, 'edge_table': populated_edge_table.name},
        format='json',
    )
    assert r.status_code == 404


@pytest.mark.django_db
def test_network_rest_retrieve(populated_network: Network, authenticated_api_client: APIClient):
    workspace = populated_network.workspace

    assert authenticated_api_client.get(
        f'/api/workspaces/{workspace.name}/networks/{populated_network.name}/'
    ).data == {
        'id': populated_network.pk,
        'name': populated_network.name,
        'node_count': populated_network.node_count,
        'edge_count': populated_network.edge_count,
        'created': TIMESTAMP_RE,
        'modified': TIMESTAMP_RE,
        'workspace': {
            'id': workspace.pk,
            'name': workspace.name,
            'created': TIMESTAMP_RE,
            'modified': TIMESTAMP_RE,
            'arango_db_name': workspace.arango_db_name,
            'public': False,
        },
    }


@pytest.mark.django_db
def test_network_rest_retrieve_public(
    public_populated_network: Network, authenticated_api_client: APIClient
):
    workspace = public_populated_network.workspace
    assert authenticated_api_client.get(
        f'/api/workspaces/{workspace.name}/networks/{public_populated_network.name}/'
    ).data == {
        'id': public_populated_network.pk,
        'name': public_populated_network.name,
        'node_count': public_populated_network.node_count,
        'edge_count': public_populated_network.edge_count,
        'created': TIMESTAMP_RE,
        'modified': TIMESTAMP_RE,
        'workspace': {
            'id': workspace.pk,
            'name': workspace.name,
            'created': TIMESTAMP_RE,
            'modified': TIMESTAMP_RE,
            'arango_db_name': workspace.arango_db_name,
            'public': True,
        },
    }


@pytest.mark.django_db
def test_network_rest_retrieve_no_access(
    private_populated_network: Network, authenticated_api_client: APIClient
):
    workspace = private_populated_network.workspace
    r = authenticated_api_client.get(
        f'/api/workspaces/{workspace.name}/networks/{private_populated_network.name}/'
    )
    assert r.status_code == 404


@pytest.mark.django_db
def test_network_rest_delete(
    writeable_populated_network: Network, authenticated_api_client: APIClient
):
    """Tests deleting a network on a workspace for which the user is a writer."""
    workspace: Workspace = writeable_populated_network.workspace

    r = authenticated_api_client.delete(
        f'/api/workspaces/{workspace.name}/networks/{writeable_populated_network.name}/'
    )

    assert r.status_code == 204

    # Assert relevant objects are deleted
    assert not Network.objects.filter(name=workspace.name).exists()
    assert not workspace.get_arango_db().has_graph(writeable_populated_network.name)


@pytest.mark.django_db
def test_network_rest_delete_unauthorized(populated_network: Network, api_client: APIClient):
    """Tests deleting a network from a workspace with an unauthorized request."""
    workspace: Workspace = populated_network.workspace

    r = api_client.delete(f'/api/workspaces/{workspace.name}/networks/{populated_network.name}/')

    assert r.status_code == 401

    # Assert relevant objects are not deleted
    assert Network.objects.filter(name=populated_network.name).exists()
    assert workspace.get_arango_db().has_graph(populated_network.name)


@pytest.mark.django_db
def test_network_rest_delete_forbidden(
    readable_workspace: Workspace,
    network_factory: NetworkFactory,
    authenticated_api_client: APIClient,
):
    """
    Tests deleting a network on a workspace for which the user does not have sufficient permissions.
    """
    network: Table = network_factory(workspace=readable_workspace)
    r = authenticated_api_client.delete(
        f'/api/workspaces/{readable_workspace.name}/networks/{network.name}/'
    )

    assert r.status_code == 403

    # Assert relevant objects are not deleted
    assert Network.objects.filter(name=network.name).exists()
    assert readable_workspace.get_arango_db().has_graph(network.name)


@pytest.mark.django_db
def test_network_rest_delete_no_access(
    private_populated_network: Network, authenticated_api_client: APIClient
):
    """Test deleting a network from a workspace for which the user has no access at all."""
    workspace: Workspace = private_populated_network.workspace
    r = authenticated_api_client.delete(
        f'/api/workspaces/{workspace.name}/networks/{private_populated_network.name}/'
    )
    assert r.status_code == 404

    # Assert relevant objects are not deleted
    assert Network.objects.filter(name=private_populated_network.name).exists()
    assert workspace.get_arango_db().has_graph(private_populated_network.name)


@pytest.mark.django_db
def test_network_rest_retrieve_nodes(
    populated_network: Network, authenticated_api_client: APIClient
):
    workspace: Workspace = populated_network.workspace
    nodes = list(populated_network.nodes())

    assert_limit_offset_results(
        authenticated_api_client,
        f'/api/workspaces/{workspace.name}/networks/{populated_network.name}/nodes/',
        nodes,
    )


@pytest.mark.django_db
def test_network_rest_retrieve_nodes_no_access(
    private_populated_network: Network, authenticated_api_client: APIClient
):
    workspace: Workspace = private_populated_network.workspace
    r = authenticated_api_client.get(
        f'/api/workspaces/{workspace.name}/networks/{private_populated_network.name}/nodes/',
        {'limit': 0, 'offset': 0},
    )
    assert r.status_code == 404


@pytest.mark.django_db
def test_network_rest_retrieve_edges(
    populated_network: Network, authenticated_api_client: APIClient
):
    workspace: Workspace = populated_network.workspace
    edges = list(populated_network.edges())

    assert_limit_offset_results(
        authenticated_api_client,
        f'/api/workspaces/{workspace.name}/networks/{populated_network.name}/edges/',
        edges,
    )


@pytest.mark.django_db
def test_network_rest_retrieve_edges_no_access(
    private_populated_network: Network, authenticated_api_client: APIClient
):
    workspace: Workspace = private_populated_network.workspace
    r = authenticated_api_client.get(
        f'/api/workspaces/{workspace.name}/networks/{private_populated_network.name}/edges/',
        {'limit': 0, 'offset': 0},
    )
    assert r.status_code == 404
