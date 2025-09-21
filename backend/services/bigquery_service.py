from config import get_bq_client, DATASET
from google.cloud import bigquery

client = get_bq_client()

def fetch_single_record(table: str, company_id: str, columns: list, order_by: str = "created_at"):
    query = f"""
        SELECT {",".join(columns)}
        FROM `{client.project}.{DATASET}.{table}`
        WHERE company_id = @company_id
        ORDER BY {order_by} DESC
        LIMIT 1
    """

    job_config = bigquery.QueryJobConfig(
        query_parameters=[
            bigquery.ScalarQueryParameter("company_id", "STRING", company_id)
        ]
    )

    query_job = client.query(query, job_config=job_config)
    results = list(query_job.result())

    return dict(results[0]) if results else None


def insert_company_record(table: str, record: dict):
    table_id = f"{client.project}.{DATASET}.{table}"
    errors = client.insert_rows_json(table_id, [record])
    if errors:
        raise Exception(f"Insert failed: {errors}")
    return {"status": "success", "record": record}
