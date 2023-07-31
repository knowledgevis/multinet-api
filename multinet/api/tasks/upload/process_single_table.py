from typing import Any, Dict, Iterable, Optional
from multinet.api.models import Table, TableTypeAnnotation
from .utils import processor_dict

def process_row(row: Dict[str, Any], cols: Dict[str, TableTypeAnnotation.Type], primary_key: Optional[str] = None, edge_source: Optional[str] = None, edge_target: Optional[str] = None, node_table_name: Optional[str] = None) -> Dict:
    new_row = dict(row)

    # Check for primary key or source and target, if missing, skip row
    if not (new_row.get(primary_key) or (new_row.get(edge_source) and new_row.get(edge_target))):
        return None

    # Convert _key to _key
    if primary_key:
        new_row['_key'] = str(new_row.pop(primary_key))

    # Convert edge source and edge target to _from and _to
    if edge_source and edge_target:
        new_row['_from'] = str(new_row.pop(edge_source))
        new_row['_to'] = str(new_row.pop(edge_target))

        # If we don't have a node_table_name, skip the row
        if ('/' not in new_row['_from'] and not node_table_name) or ('/' not in new_row['_to'] and not node_table_name):
            return None

        # Add node_table_name to _from and _to if not already present
        if '/' not in new_row['_from'] and node_table_name:
            new_row['_from'] = f'{node_table_name}/{new_row["_from"]}'
        
        if '/' not in new_row['_to'] and node_table_name:
            new_row['_to'] = f'{node_table_name}/{new_row["_to"]}'

        # Sanity check that the _from and _to are formatted with the node table name
        if node_table_name and (new_row['_to'].split('/')[0] != node_table_name or new_row['_from'].split('/')[0] != node_table_name):
            return None
        
        # Sanity check that we don't have more than 1 slash in the _from and _to
        if len(new_row['_from'].split('/')) > 2 or len(new_row['_to'].split('/')) > 2:
            return None
        

    for col_key, col_type in cols.items():
        entry = row.get(col_key)

        # If null entry, skip
        if entry is None:
            continue

        process_func = processor_dict.get(col_type)
        if process_func is not None:
            try:
                new_row[col_key] = process_func(entry)
            except ValueError:
                # If error processing row, keep as string
                pass

    return new_row

def process_single_table(
    row_data: Iterable[Dict[str, Any]],
    table_name: str,
    workspace: str,
    edge: bool,
    column_types: Dict[str, TableTypeAnnotation.Type],
    node_table_name: Optional[str] = None,
):
    # Create new table
    table: Table = Table.objects.create(
        name=table_name,
        edge=edge,
        workspace=workspace,
    )

    # Reverse the cols dict to find the primary key, source, and target (if they exist)
    reversed_cols = {v: k for k, v in column_types.items()}
    primary_key = reversed_cols.get(TableTypeAnnotation.Type.PRIMARY)
    edge_source = reversed_cols.get(TableTypeAnnotation.Type.SOURCE)
    edge_target = reversed_cols.get(TableTypeAnnotation.Type.TARGET)

    # Create type annotation dict where we replace primary key with _key, and source and target with _from and _to
    type_annotation_cols = dict(column_types)
    if primary_key:
        type_annotation_cols['_key'] = type_annotation_cols.pop(primary_key)

    if edge_source and edge_target:
        type_annotation_cols['_from'] = type_annotation_cols.pop(edge_source)
        type_annotation_cols['_to'] = type_annotation_cols.pop(edge_target)

    # Create type annotations
    TableTypeAnnotation.objects.bulk_create(
        [TableTypeAnnotation(table=table, column=col_key, type=col_type) for col_key, col_type in type_annotation_cols.items()]
    )

    # Process rows and upload
    processed_rows = []
    for row in row_data:
        # Process rows using original column types
        new_row = process_row(row, column_types, primary_key, edge_source, edge_target, node_table_name)
        if new_row is None:
            continue

        processed_rows.append(new_row)

        # Batch insert 100000 rows at a time
        if len(processed_rows) == 100000:
            table.put_rows(processed_rows)
            processed_rows = []

    # Insert remaining rows that didn't fit into the batch
    table.put_rows(processed_rows)

