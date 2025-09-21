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

"""Risk Detection Agent tools for performing comprehensive risk analysis."""

import os
import json
import logging
import uuid
from datetime import datetime
from typing import Dict, List, Any, Optional
from dataclasses import dataclass

from google.cloud import bigquery
from google.adk.tools.google_search_tool import google_search

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Environment variables
PROJECT_ID = os.getenv('GOOGLE_CLOUD_PROJECT', 'starlit-factor-472009-b0')
BIGQUERY_DATASET = os.getenv('BIGQUERY_DATASET', 'pitch_deck_analysis')
BIGQUERY_TABLE = os.getenv('BIGQUERY_TABLE', 'risk_analysis_results')


@dataclass
class RiskFactor:
    """Data class for risk factor structure"""
    name: str
    impact: str  # High, Medium, Low
    probability: str  # High, Medium, Low
    risk_score: str  # High, Medium, Low
    mitigation: str  # Strong, Partial, None
    category: str = "Unknown"
    description: str = ""


class RiskAnalysisEngine:
    """Enhanced Risk Analysis Engine with BigQuery integration"""

    def __init__(self):
        self.client = bigquery.Client(project=PROJECT_ID)
        self.risk_categories = [
            "Market_Competition",
            "Technology_Disruption",
            "Regulatory_Changes",
            "Talent_Acquisition",
            "Economic_Downturn",
            "Cybersecurity_Threats",
            "Supply_Chain_Disruption",
            "Financial_Liquidity",
            "Product_Development",
            "Customer_Concentration"
        ]

    def analyze_company_risks(self, company_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Main function to analyze company risks and return structured JSON

        Args:
            company_data: Dictionary containing company information

        Returns:
            Complete risk analysis with JSON structure
        """
        try:
            logger.info(f"Starting risk analysis for: {company_data.get('company_name', 'Unknown')}")

            # Generate dynamic risk factors
            risk_factors = self._generate_dynamic_risk_factors(company_data)

            # Create structured response
            analysis_result = {
                "company_id": company_data.get("company_id", str(uuid.uuid4())),
                "company_name": company_data.get("company_name", "Unknown"),
                "analysis_date": datetime.utcnow().isoformat(),
                "session_id": str(uuid.uuid4()),
                "risk_factors": self._format_risk_factors_json(risk_factors),
                "overall_risk_score": self._calculate_overall_risk_score(risk_factors),
                "high_priority_risks": self._identify_high_priority_risks(risk_factors),
                "financial_metrics": self._extract_financial_metrics(company_data),
                "mitigation_recommendations": self._generate_mitigation_strategies(risk_factors),
                "confidence_score": self._calculate_confidence_score(company_data, risk_factors)
            }

            # Save to BigQuery
            success = self._save_to_bigquery(analysis_result)
            analysis_result["bigquery_saved"] = success

            if success:
                logger.info(
                    f"[BigQuery] Successfully saved risk analysis for company: {analysis_result['company_name']}")
            else:
                logger.error(f"[BigQuery] Failed to save risk analysis for company: {analysis_result['company_name']}")

            logger.info(f"Risk analysis completed for: {analysis_result['company_name']}")
            return analysis_result

        except Exception as e:
            logger.error(f"Risk analysis failed: {str(e)}")
            return {
                "success": False,
                "error": str(e),
                "company_name": company_data.get("company_name", "Unknown")
            }

    def _generate_dynamic_risk_factors(self, company_data: Dict[str, Any]) -> List[RiskFactor]:
        """Generate dynamic risk factors based on company data"""
        risks = []

        # Market Competition Risk
        market_cap = company_data.get("market_cap", 0)
        competitor_count = company_data.get("competitor_count", 0)

        market_competition = RiskFactor(
            name="Market_Competition",
            impact="High" if competitor_count > 10 else "Medium" if competitor_count > 5 else "Low",
            probability="High" if market_cap < 1000000000 else "Medium",
            risk_score=self._calculate_risk_score("High" if competitor_count > 10 else "Medium", "High"),
            mitigation="Partial" if company_data.get("unique_value_prop") else "None",
            category="Strategic",
            description="Competitive pressure from existing and new market players"
        )
        risks.append(market_competition)

        # Technology Disruption
        industry = company_data.get("industry", "").lower()
        tech_investment = company_data.get("rd_investment_percent", 0)

        tech_disruption = RiskFactor(
            name="Technology_Disruption",
            impact="High" if industry in ["fintech", "healthcare", "retail"] else "Medium",
            probability="High" if tech_investment < 5 else "Medium" if tech_investment < 15 else "Low",
            risk_score=self._calculate_risk_score(
                "High" if industry in ["fintech", "healthcare"] else "Medium",
                "High" if tech_investment < 5 else "Medium"
            ),
            mitigation="Strong" if tech_investment > 15 else "Partial" if tech_investment > 5 else "None",
            category="Technology",
            description="Risk of technological obsolescence and digital transformation"
        )
        risks.append(tech_disruption)

        # Regulatory Changes
        regulatory_risk = company_data.get("regulatory_risk_score", 5)
        regulatory_change = RiskFactor(
            name="Regulatory_Changes",
            impact="High" if regulatory_risk > 7 else "Medium" if regulatory_risk > 4 else "Low",
            probability="High" if industry in ["fintech", "healthcare"] else "Medium",
            risk_score=self._calculate_risk_score(
                "High" if regulatory_risk > 7 else "Medium",
                "High" if industry in ["fintech", "healthcare"] else "Medium"
            ),
            mitigation="Strong" if company_data.get("compliance_team") else "None",
            category="Legal",
            description="Changes in laws and regulations impacting business operations"
        )
        risks.append(regulatory_change)

        # Financial Liquidity
        cash_runway = company_data.get("cash_runway_months", 0)
        financial_liquidity = RiskFactor(
            name="Financial_Liquidity",
            impact="High" if cash_runway < 6 else "Medium" if cash_runway < 12 else "Low",
            probability="High" if cash_runway < 12 else "Low",
            risk_score=self._calculate_risk_score(
                "High" if cash_runway < 6 else "Medium",
                "High" if cash_runway < 12 else "Low"
            ),
            mitigation="Partial" if company_data.get("fundraising_plan") else "None",
            category="Financial",
            description="Inability to meet short-term financial obligations"
        )
        risks.append(financial_liquidity)

        # Cybersecurity Threats
        cybersecurity_score = company_data.get("cybersecurity_score", 5)
        cybersecurity_threat = RiskFactor(
            name="Cybersecurity_Threats",
            impact="High" if company_data.get("sensitive_data") else "Medium",
            probability="High" if cybersecurity_score < 5 else "Medium" if cybersecurity_score < 8 else "Low",
            risk_score=self._calculate_risk_score(
                "High" if company_data.get("sensitive_data") else "Medium",
                "High" if cybersecurity_score < 5 else "Medium"
            ),
            mitigation="Strong" if cybersecurity_score > 8 else "Partial",
            category="Operational",
            description="Data breaches and system failures"
        )
        risks.append(cybersecurity_threat)

        return risks

    def _calculate_risk_score(self, impact: str, probability: str) -> str:
        """Calculate overall risk score based on impact and probability"""
        risk_matrix = {
            ("High", "High"): "High",
            ("High", "Medium"): "High",
            ("High", "Low"): "Medium",
            ("Medium", "High"): "High",
            ("Medium", "Medium"): "Medium",
            ("Medium", "Low"): "Low",
            ("Low", "High"): "Medium",
            ("Low", "Medium"): "Low",
            ("Low", "Low"): "Low"
        }
        return risk_matrix.get((impact, probability), "Medium")

    def _format_risk_factors_json(self, risk_factors: List[RiskFactor]) -> Dict[str, Dict[str, str]]:
        """Format risk factors into the requested JSON structure"""
        formatted_risks = {}

        for risk in risk_factors:
            formatted_risks[risk.name] = {
                "impact": risk.impact,
                "probability": risk.probability,
                "risk_score": risk.risk_score,
                "mitigation": risk.mitigation,
                "category": risk.category,
                "description": risk.description
            }

        return formatted_risks

    def _calculate_overall_risk_score(self, risk_factors: List[RiskFactor]) -> str:
        """Calculate overall risk score for the company"""
        high_count = sum(1 for risk in risk_factors if risk.risk_score == "High")
        total_count = len(risk_factors)

        if total_count == 0:
            return "Medium"

        if high_count / total_count >= 0.4:
            return "High"
        elif high_count / total_count >= 0.2:
            return "Medium"
        else:
            return "Low"

    def _identify_high_priority_risks(self, risk_factors: List[RiskFactor]) -> List[str]:
        """Identify high priority risks that need immediate attention"""
        return [risk.name for risk in risk_factors if risk.risk_score == "High"]

    def _extract_financial_metrics(self, company_data: Dict[str, Any]) -> Dict[str, Any]:
        """Extract and calculate financial risk metrics"""
        return {
            "liquidity_risks": {
                "current_ratio": company_data.get("current_ratio", 0),
                "cash_runway_months": company_data.get("cash_runway_months", 0),
                "burn_rate": company_data.get("monthly_burn_rate", 0)
            },
            "profitability_risks": {
                "net_margin": company_data.get("net_margin_percent", 0),
                "path_to_profit": company_data.get("path_to_profit", "Unknown"),
                "unit_economics": company_data.get("unit_economics_status", "Unknown")
            },
            "leverage_risks": {
                "debt_to_equity": company_data.get("debt_to_equity_ratio", 0),
                "interest_coverage": company_data.get("interest_coverage_ratio", 0),
                "financial_flexibility": company_data.get("financial_flexibility", "Limited")
            }
        }

    def _generate_mitigation_strategies(self, risk_factors: List[RiskFactor]) -> List[Dict[str, str]]:
        """Generate mitigation strategies for high-priority risks"""
        strategies = []

        high_risks = [risk for risk in risk_factors if risk.risk_score == "High"]

        strategy_templates = {
            "Market_Competition": "Develop unique value proposition and strengthen customer loyalty programs",
            "Technology_Disruption": "Increase R&D investment and establish innovation partnerships",
            "Regulatory_Changes": "Build compliance team and engage with regulatory bodies proactively",
            "Talent_Acquisition": "Implement competitive compensation packages and remote work options",
            "Financial_Liquidity": "Secure additional funding and optimize cash flow management",
            "Cybersecurity_Threats": "Invest in advanced security protocols and regular audits"
        }

        for risk in high_risks[:5]:  # Top 5 high risks
            strategy = strategy_templates.get(risk.name, f"Develop comprehensive risk management plan for {risk.name}")
            strategies.append({
                "risk_name": risk.name,
                "strategy": strategy,
                "priority": "High",
                "timeline": "3-6 months"
            })

        return strategies

    def _calculate_confidence_score(self, company_data: Dict[str, Any], risk_factors: List[RiskFactor]) -> float:
        """Calculate confidence score based on data completeness"""
        total_fields = len(company_data)
        filled_fields = sum(1 for value in company_data.values() if value not in [None, "", 0, []])
        return round(filled_fields / total_fields if total_fields > 0 else 0.0, 2)

    def _save_to_bigquery(self, analysis_result: Dict[str, Any]) -> bool:
        """Save complete risk analysis to BigQuery"""
        try:
            # Prepare row data for BigQuery
            row_data = {
                'company_id': analysis_result.get('company_id'),
                'company_name': analysis_result.get('company_name'),
                'analysis_date': analysis_result.get('analysis_date'),
                'session_id': analysis_result.get('session_id'),
                'overall_risk_score': analysis_result.get('overall_risk_score'),
                'high_priority_risks': analysis_result.get('high_priority_risks', []),
                'confidence_score': analysis_result.get('confidence_score', 0.0),

                'risk_factors_json': json.dumps(analysis_result.get('risk_factors', {})),
                'financial_metrics_json': json.dumps(analysis_result.get('financial_metrics', {})),
                'mitigation_strategies_json': json.dumps(analysis_result.get('mitigation_recommendations', [])),

                'processing_status': 'SUCCESS',
                'created_at': datetime.utcnow().isoformat(),
                'updated_at': datetime.utcnow().isoformat()
            }

            table_ref = self.client.dataset(BIGQUERY_DATASET).table(BIGQUERY_TABLE)
            table = self.client.get_table(table_ref)
            errors = self.client.insert_rows_json(table, [row_data])

            if errors:
                logger.error(f"BigQuery errors: {errors}")
                return False

            logger.info(f"Risk analysis saved to BigQuery: {analysis_result.get('company_name')}")
            return True

        except Exception as e:
            logger.error(f"BigQuery save failed: {str(e)}")
            return False


# Initialize the risk analysis engine
risk_engine = RiskAnalysisEngine()


# Tool functions for the ADK agent
def analyze_company_risk_profile(company_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Tool function: Analyze company risk profile and return structured results

    Args:
        company_data: Dictionary containing company information including:
            - company_name, industry, market_cap, competitor_count, employee_count,
            - rd_investment_percent, cash_runway_months, monthly_burn_rate, etc.

    Returns:
        Complete risk analysis with JSON structure matching your requirements
    """
    return risk_engine.analyze_company_risks(company_data)


def query_risk_analysis_results(company_name: Optional[str] = None, limit: int = 10) -> Dict[str, Any]:
    """
    Tool function: Query historical risk analysis results from BigQuery

    Args:
        company_name: Optional company name to filter results
        limit: Maximum number of results to return

    Returns:
        Historical risk analysis data
    """
    try:
        client = bigquery.Client(project=PROJECT_ID)

        where_clause = f"WHERE company_name = '{company_name}'" if company_name else ""

        query = f"""
        SELECT 
            company_name,
            overall_risk_score,
            ARRAY_LENGTH(high_priority_risks) as high_risk_count,
            confidence_score,
            analysis_date,
            risk_factors_json,
            processing_status
        FROM `{PROJECT_ID}.{BIGQUERY_DATASET}.{BIGQUERY_TABLE}`
        {where_clause}
        ORDER BY analysis_date DESC
        LIMIT {limit}
        """

        results = client.query(query)

        analyses = []
        for row in results:
            analysis = {
                "company_name": row.company_name,
                "overall_risk_score": row.overall_risk_score,
                "high_risk_count": row.high_risk_count,
                "confidence_score": row.confidence_score,
                "analysis_date": row.analysis_date,
                "processing_status": row.processing_status
            }

            if hasattr(row, 'risk_factors_json') and row.risk_factors_json:
                analysis["risk_factors"] = json.loads(row.risk_factors_json)

            analyses.append(analysis)

        return {
            "success": True,
            "count": len(analyses),
            "analyses": analyses
        }

    except Exception as e:
        logger.error(f"Query failed: {str(e)}")
        return {"success": False, "error": str(e)}