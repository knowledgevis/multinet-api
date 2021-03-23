import pytest
from rest_framework.test import APIClient

from multinet.api.models import Network, Table, Workspace

from .fuzzy import INTEGER_ID_RE, TIMESTAMP_RE


@pytest.mark.django_db
def test_network_rest_create(
    owned_workspace: Workspace,
    populated_edge_table: Table,
    populated_node_table: Table,
    authenticated_api_client: APIClient,
):
    network_name = 'network'
    r = authenticated_api_client.post(
        f'/api/workspaces/{owned_workspace.name}/networks/',
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
            'id': owned_workspace.pk,
            'name': owned_workspace.name,
            'created': TIMESTAMP_RE,
            'modified': TIMESTAMP_RE,
            'arango_db_name': owned_workspace.arango_db_name,
        },
    }

    # Django will raise an exception if this fails, implicitly validating that the object exists
    network: Network = Network.objects.get(name=network_name)

    # Assert that object was created in arango
    assert owned_workspace.get_arango_db().has_graph(network.name)


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
        },
    }


@pytest.mark.django_db
def test_network_rest_delete(populated_network: Network, authenticated_api_client: APIClient):
    workspace: Workspace = populated_network.workspace

    r = authenticated_api_client.delete(
        f'/api/workspaces/{workspace.name}/networks/{populated_network.name}/'
    )

    assert r.status_code == 204

    # Assert relevant objects are deleted
    assert Network.objects.filter(name=workspace.name).first() is None
    assert not workspace.get_arango_db().has_graph(populated_network.name)


@pytest.mark.django_db
def test_network_rest_retrieve_nodes(
    populated_network: Network, authenticated_api_client: APIClient
):
    workspace: Workspace = populated_network.workspace
    r = authenticated_api_client.get(
        f'/api/workspaces/{workspace.name}/networks/{populated_network.name}/nodes/'
    )

    assert r.json() == {
        'count': populated_network.node_count,
        'next': None,
        'previous': None,
        'results': list(populated_network.nodes()),
    }


@pytest.mark.django_db
def test_network_rest_retrieve_edges(
    populated_network: Network, authenticated_api_client: APIClient
):
    workspace: Workspace = populated_network.workspace
    r = authenticated_api_client.get(
        f'/api/workspaces/{workspace.name}/networks/{populated_network.name}/edges/'
    )

    assert r.json() == {
        'count': populated_network.edge_count,
        'next': None,
        'previous': None,
        'results': list(populated_network.edges()),
    }
