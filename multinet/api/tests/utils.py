from typing import Dict, List, Optional

from rest_framework.test import APIClient


def get_field_value(data_file, s3ff_client):

    field_value = ""
    with open(data_file) as file_stream:
        field_value = s3ff_client.upload_file(
            file_stream,  # This can be any file-like object
            data_file.name,
            'api.Upload.blob',  # The "<app>.<model>.<field>" to upload to
        )['field_value']
    return field_value


def generate_arango_documents(n: int, num_fields: int = 3) -> List[Dict]:
    """Generate n number of test documents, each containing num_fields fields."""
    return [{f'foo{i}_{ii}': f'bar{i}_{ii}' for ii in range(num_fields)} for i in range(n)]


def assert_limit_offset_results(
    client: APIClient, url: str, result: List, params: Optional[Dict] = None
):
    """
    Assert that a limit/offset endpoint performs correct pagination.

    This is done by making the desired request with all of the relevant limit/offset permutations.
    """
    query_params = params or {}
    l_range = range(len(result))
    for limit in l_range:
        for offset in l_range:
            r = client.get(
                url,
                {**query_params, 'limit': limit, 'offset': offset},
            )

            r_json = r.json()
            assert r.status_code == 200
            assert r_json['count'] == limit or len(result)
            assert r_json['results'] == result[offset : (limit + offset if limit else None)]
