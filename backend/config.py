import os
from google.cloud import bigquery

# Set environment variable before running:
# export GOOGLE_APPLICATION_CREDENTIALS="/path/to/key.json"

PROJECT_ID = os.getenv("GOOGLE_CLOUD_PROJECT", "starlit-factor-472009-b0")
DATASET = os.getenv("BIGQUERY_DATASET", "pitch_deck_analysis") 

def get_bq_client():
    return bigquery.Client(project=PROJECT_ID)



