import os
import json
import logging
from datetime import datetime, timezone
from google.cloud import bigquery
from google.cloud.exceptions import NotFound
from google.adk import Agent
from google.adk.tools.function_tool import FunctionTool
from pydantic import BaseModel, Field, ValidationError
from typing import List, Dict, Any, Optional
from google.adk.tools.agent_tool import AgentTool
# Assuming these relative imports are correct in your project structure
from . import prompt
from ..search_agent.agent import search_agent

# --- Configuration ---
PROJECT_ID = os.getenv('GOOGLE_CLOUD_PROJECT', 'starlit-factor-472009-b0')
BIGQUERY_DATASET = os.getenv('BIGQUERY_DATASET', 'pitch_deck_analysis')
BIGQUERY_TABLE = os.getenv('BIGQUERY_TABLE', 'founders_profiles')

# Initialize logger
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Suppress noisy OpenTelemetry warnings about None-valued attributes
os.environ.setdefault("OTEL_LOG_LEVEL", "ERROR")

class _DropGenAIInputTokensWarning(logging.Filter):
    def filter(self, record: logging.LogRecord) -> bool:
        msg = record.getMessage()
        return "Invalid type NoneType for attribute 'gen_ai.usage.input_tokens'" not in msg

try:
    # Lower verbosity of common OTEL loggers
    for name in [
        "opentelemetry",
        "opentelemetry.sdk",
        "opentelemetry.sdk.trace",
        "opentelemetry.instrumentation",
        "opentelemetry.instrumentation.gen_ai",
        "opentelemetry.attributes",
    ]:
        logging.getLogger(name).setLevel(logging.ERROR)

    # Add a focused filter at root to drop just this noisy warning
    logging.getLogger().addFilter(_DropGenAIInputTokensWarning())
except Exception:
    # Best-effort suppression; ignore if logging backend differs
    pass

# --- DETAILED PYDANTIC SCHEMAS ---
class Evidence(BaseModel):
    source: str = Field(..., description="URL or source identifier for the evidence.")
    title: str = Field(..., description="Title or description of the evidence.")

class ProfileDimension(BaseModel):
    summary: str = Field(..., description="Detailed evidence-based assessment.")
    score: Optional[int] = Field(None, description="Score from 1-10, if applicable.")
    evidence: List[Evidence] = Field(..., description="List of evidence supporting the assessment.")

class FounderProfile(BaseModel):
    reputation_integrity: ProfileDimension
    execution_capability: ProfileDimension
    domain_expertise: ProfileDimension
    professional_background: ProfileDimension
    fundraising_investor_relations: ProfileDimension
    network_influence: ProfileDimension
    social_persona: ProfileDimension
    vision_communication: ProfileDimension

class FounderDetail(BaseModel):
    name: str = Field(..., description="Founder's Full Name.")
    current_role: str = Field(..., description="CEO/CTO/Co-founder/etc.")
    profile: FounderProfile

class OverallAssessment(BaseModel):
    team_strength: str = Field(..., description="STRONG/MODERATE/WEAK.")
    key_strengths: List[str]
    key_concerns: List[str]
    investment_recommendation: str

class FounderData(BaseModel):
    analysis_date: str = Field(..., description="YYYY-MM-DD.")
    founders: List[FounderDetail]
    overall_assessment: OverallAssessment

class FounderAnalysisOutput(BaseModel):
    company_name: str = Field(..., description="Name of the startup/company.")
    founder_data: FounderData


# --- Helper Functions ---
def _extract_first_json_object(text: str) -> str:
    """Extract the first top-level JSON object substring from text.
    Returns substring from first '{' to matching '}'.
    """
    start = text.find('{')
    if start == -1:
        raise ValueError("No opening brace found in text")
    depth = 0
    for i in range(start, len(text)):
        ch = text[i]
        if ch == '{':
            depth += 1
        elif ch == '}':
            depth -= 1
            if depth == 0:
                return text[start:i+1]
    raise ValueError("Unbalanced braces in text")


def _clean_json_string(raw_input: Any) -> str:
    """Clean and normalize input to a valid JSON string."""
    if isinstance(raw_input, (dict, list)):
        return json.dumps(raw_input)
    elif isinstance(raw_input, str):
        cleaned = raw_input.strip()
        # Remove markdown fences
        if cleaned.startswith("```"):
            cleaned = cleaned.strip('`').strip()
            if cleaned.startswith('json'):
                cleaned = cleaned[4:].strip()
        # Extract JSON object if mixed with other text
        try:
            cleaned = _extract_first_json_object(cleaned)
        except Exception as e:
            logger.warning(f"JSON extraction skipped: {e}")
        return cleaned
    else:
        return json.dumps(raw_input)


# --- BigQuery Operations ---
def _ensure_dataset_and_table(client: bigquery.Client) -> bigquery.TableReference:
    """Ensure dataset and table exist, create if necessary."""
    # Ensure dataset exists
    dataset_ref = bigquery.DatasetReference(PROJECT_ID, BIGQUERY_DATASET)
    try:
        client.get_dataset(dataset_ref)
        logger.info(f"Dataset {BIGQUERY_DATASET} exists")
    except NotFound:
        logger.info(f"Creating dataset {BIGQUERY_DATASET}")
        client.create_dataset(bigquery.Dataset(dataset_ref))

    # Ensure table exists
    table_ref = dataset_ref.table(BIGQUERY_TABLE)
    try:
        client.get_table(table_ref)
        logger.info(f"Table {BIGQUERY_TABLE} exists")
    except NotFound:
        logger.info(f"Creating table {BIGQUERY_TABLE}")
        schema = [
            bigquery.SchemaField("company_id", "STRING"),
            bigquery.SchemaField("company_name", "STRING"),
            bigquery.SchemaField("founder_data", "STRING"),
            bigquery.SchemaField("created_at", "TIMESTAMP"),
        ]
        table = bigquery.Table(table_ref, schema=schema)
        client.create_table(table)
    
    return table_ref


def _get_company_id(client: bigquery.Client, company_name: str) -> str:
    """Get company ID from company table, fallback to generated ID."""
    try:
        company_query = f"""
        SELECT id FROM `{PROJECT_ID}.{BIGQUERY_DATASET}.company`
        WHERE LOWER(name) = LOWER(@name) LIMIT 1"""
        job_config = bigquery.QueryJobConfig(
            query_parameters=[bigquery.ScalarQueryParameter("name", "STRING", company_name)]
        )
        query_job = client.query(company_query, job_config=job_config)
        results = query_job.result()
        company_id = next((row.id for row in results), None)
        
        if company_id:
            logger.info(f"Found company ID: {company_id} for {company_name}")
            return company_id
    except Exception as e:
        logger.warning(f"Company lookup failed: {e}")
    
    # Fallback to generated ID
    fallback_id = f"unknown_{company_name.lower().replace(' ', '_').replace('-', '_')}"
    logger.warning(f"Using fallback company ID: {fallback_id}")
    return fallback_id


# --- Main BigQuery Tool ---
def insert_founder_data_in_big_query(analysis_json_string: str) -> str:
    """
    Cleans, validates, and saves founder analysis JSON to BigQuery.
    
    Args:
        analysis_json_string: The raw JSON string produced by the agent
        
    Returns:
        Success or error message
    """
    logger.info("Starting BigQuery insertion process")
    
    try:
        # Clean and validate JSON
        cleaned_json = _clean_json_string(analysis_json_string)
        logger.info("JSON cleaning completed")
        
        # Validate against Pydantic schema
        analysis_data = FounderAnalysisOutput.model_validate_json(cleaned_json)
        analysis_dict = analysis_data.model_dump()
        company_name = analysis_dict.get('company_name', 'Unknown')
        logger.info(f"Analysis validated for company: {company_name}")
        
    except (ValidationError, json.JSONDecodeError) as e:
        error_msg = f"❌ JSON validation/parsing error: {str(e)[:200]}..."
        logger.error(error_msg)
        return error_msg
    
    try:
        # Initialize BigQuery client
        client = bigquery.Client(project=PROJECT_ID)
        logger.info("BigQuery client initialized")
        
        # Ensure infrastructure exists
        table_ref = _ensure_dataset_and_table(client)
        
        # Get or generate company ID
        company_id = _get_company_id(client, company_name)
        
        # Prepare row for insertion
        row = {
            "company_id": company_id,
            "company_name": company_name,
            "founder_data": json.dumps(analysis_dict),
            "created_at": datetime.now(timezone.utc).isoformat(),
        }
        
        # Insert into BigQuery
        errors = client.insert_rows_json(table_ref, [row])
        
        if not errors:
            success_msg = f"✅ Successfully saved founder analysis for '{company_name}' to BigQuery"
            logger.info(success_msg)
            return success_msg
        else:
            error_msg = f"❌ BigQuery insertion errors: {errors}"
            logger.error(error_msg)
            return error_msg
            
    except Exception as e:
        error_msg = f"❌ Unexpected BigQuery error: {str(e)[:200]}..."
        logger.error(error_msg)
        return error_msg


# --- Tool for Company Research ---
def research_company_founders(company_name: str) -> str:
    """
    Research and identify founders of a given company using the search agent.
    
    Args:
        company_name: Name of the company to research
        
    Returns:
        Information about the company's founders
    """
    logger.info(f"Researching founders for: {company_name}")
    
    try:
        # Use search agent to find founders
        search_queries = [
            f"{company_name} founders",
            f"{company_name} CEO founder",
            f"{company_name} startup team founders"
        ]
        
        results = []
        for query in search_queries:
            try:
                result = search_agent.run(query)
                if result:
                    results.append(f"Query: {query}\nResults: {result}\n---")
            except Exception as e:
                logger.warning(f"Search failed for query '{query}': {e}")
                continue
        
        if results:
            combined_results = "\n".join(results)
            logger.info(f"Found founder information for {company_name}")
            return combined_results
        else:
            return f"No founder information found for {company_name}"
            
    except Exception as e:
        error_msg = f"Error researching founders for {company_name}: {e}"
        logger.error(error_msg)
        return error_msg



# --- Agent Definition ---
MODEL = "gemini-2.0-flash"

founder_analysis_agent = Agent(
    name="FounderAnalysisAgent",
    description="A specialized agent for conducting in-depth analysis of startup founders.",
    model=MODEL,
    instruction=prompt.SYSTEM_PROMPT,
    output_key="founder_analysis_report",
    tools=[
        AgentTool(agent=search_agent),
    ],
)