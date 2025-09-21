# Copyright 2025 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""Financial Analyst agent for finding the financial data about the company"""

from google.adk import Agent
from . import prompt
from google.cloud import bigquery
from google.oauth2 import service_account
import os
from typing import Dict, List, Any
import logging
import json
from .models import FAOutput
# from .tools import duckduckgo_search

# Initialize logger
logger = logging.getLogger(__name__)

# Load environment variables
PROJECT_ID = os.getenv('GOOGLE_CLOUD_PROJECT', 'starlit-factor-472009-b0')
BUCKET_NAME = os.getenv('BUCKET_NAME', 'pitch-deck-analysis-bucket')
BIGQUERY_DATASET = os.getenv('BIGQUERY_DATASET', 'pitch_deck_analysis')
BIGQUERY_TABLE = os.getenv('BIGQUERY_TABLE', 'financial_analysis_agent')
CREDENTIALS_PATH = os.getenv('GOOGLE_APPLICATION_CREDENTIALS')

def insert_in_big_query(analysis: Dict[str, Any]):
    """
    Save financial analysis results to BigQuery database for storage and future reference.
    
    This tool stores the complete financial analysis data including company metrics,
    funding information, growth data, and financial health indicators in a structured
    BigQuery table for persistent storage and querying.
    
    Args:
        analysis (Dict[str, Any]): A dictionary containing the financial analysis results
            with the following expected structure:
            - company_name: Name of the analyzed company
            - analysis_date: Date when analysis was performed  
            - key_financial_metrics: Dictionary containing total_funding, current_valuation, arr, revenue, loss
            - growth_metrics: Dictionary with revenue_growth, yoy_growth, loss_reduction, employee_growth
            - financial_health: Dictionary with current_ratio, debt_equity_ratio, net_profit_margin, ebitda_margin
            - shareholding_distribution: Dictionary with ownership percentages by investor type
            - funding_rounds: List of funding round objects with series, date, amount, lead_investors
            - future_plans: Dictionary with profitability_target, ipo_timeline, arr_target
            - key_insights: List of positive financial observations
            - risks: List of identified financial risks
            - opportunities: List of potential growth opportunities
            - data_sources: List of sources used for the analysis
            
    Returns:
        None: This function saves data to BigQuery and logs the operation status.
        The analysis dictionary is updated with a 'bigquery_saved' flag indicating
        whether the save operation was successful.
        
    Example:
        analysis_data = {
            "company_name": "TechCorp Inc",
            "key_financial_metrics": {"total_funding": "$50M", "arr": "$10M"},
            "growth_metrics": {"revenue_growth": "150%"}
        }
        insert_in_big_query(analysis_data)
    """

    bigquery_success = save_to_bigquery(analysis)
    analysis["bigquery_saved"] = bigquery_success
    
    logger.info(f"🎉 Analysis completed for: {analysis.get('company_name', 'Unknown Company')}")

def save_to_bigquery(analysis: Dict[str, Any]) -> bool:
    """Save analysis results to BigQuery"""
    try:
        credentials = None
        if CREDENTIALS_PATH:
            credentials = service_account.Credentials.from_service_account_file(CREDENTIALS_PATH)
        client = bigquery.Client(project=PROJECT_ID, credentials=credentials)
        # Insert to BigQuery
        table_ref = client.dataset(BIGQUERY_DATASET).table(BIGQUERY_TABLE)
        table = client.get_table(table_ref)
        
        # Prepare data for BigQuery with JSON in financial_data column
        # 'company_name': analysis.get('result', {}).get('company_name', 'Unknown'),

        # Get company name and fetch company ID from BigQuery
        name = analysis.get('company_name', 'Unknown')
        
        # Query company table to get company ID
        company_query = f"""
        SELECT id 
        FROM `{PROJECT_ID}.{BIGQUERY_DATASET}.company` 
        WHERE LOWER(name) = LOWER(@name)
        LIMIT 1
        """
        
        job_config = bigquery.QueryJobConfig(
            query_parameters=[
                bigquery.ScalarQueryParameter("name", "STRING", name)
            ]
        )
        
        query_job = client.query(company_query, job_config=job_config)
        results = query_job.result()
        
        company_id = None
        for row in results:
            company_id = row.id
            break
        
        if not company_id:
            logger.warning(f"Company ID not found for: {name}")
            company_id = f"unknown_{name.lower().replace(' ', '_')}"
        else:
            company_id = company_id
            
        bigquery_row = {
            "company_id": company_id if company_id else "1",
            "financial_data": json.dumps(analysis)
        }
        
        errors = client.insert_rows_json(table, [bigquery_row])
        
        if errors:
            logger.error(f"BigQuery errors: {errors}")
            return False
        
        logger.info(f"✅ Saved to BigQuery: {name}")
        return True
        
    except Exception as e:
        logger.error(f"❌ BigQuery save failed: {str(e)}")
        return False


MODEL = "gemini-2.5-flash"

financial_analysis_agent = Agent(
    model=MODEL,
    name="financial_analysis_agent",
    instruction=prompt.FINANCIAL_ANALYSIS_PROMPT,
    output_key="financial_analysis_report",
    tools=[insert_in_big_query],
    output_schema=FAOutput,
    disallow_transfer_to_parent=True,
    disallow_transfer_to_peers=True
)