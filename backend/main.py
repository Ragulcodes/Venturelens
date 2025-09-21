from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import uuid
from datetime import datetime

from services.bigquery_service import fetch_single_record, insert_company_record

app = FastAPI(title="BigQuery FastAPI Example")

# ---------- MODELS ----------
class CompanyCreate(BaseModel):
    name: str

@app.get("/financial-analysis/{company_id}")
def get_financial_analysis(company_id: str):
    result = fetch_single_record(
        "financial_analysis_agent",
        company_id,
        ["company_id", "financial_data"]
    )
    if not result:
        raise HTTPException(status_code=404, detail="Company not found")
    return result

@app.get("/risk-analysis/{company_id}")
def get_risk_analysis(company_id: str):
    result = fetch_single_record(
        "risk_analysis_results",
        company_id,
        ["company_id", "risk_factors_json"]
    )
    if not result:
        raise HTTPException(status_code=404, detail="Company not found")
    return result

@app.get("/benchmark-analysis/{company_id}")
def get_benchmark_analysis(company_id: str):
    result = fetch_single_record(
        "benchmark_analysis_results",
        company_id,
        ["company_id", "benchmark_metrics_json"]
    )
    if not result:
        raise HTTPException(status_code=404, detail="Company not found")
    return result

@app.post("/company")
def create_company(company: CompanyCreate):
    record = {
        "id": str(uuid.uuid4()), 
        "uuid": str(uuid.uuid4()),
        "name": company.name,
        "created_at": datetime.utcnow().isoformat()
    }
    try:
        return insert_company_record("company", record)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
