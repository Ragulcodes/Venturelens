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

"""Benchmark Analysis Agent for comprehensive startup evaluation and competitive benchmarking."""

import os
import json
import logging
import uuid
from datetime import datetime
from typing import Dict, List, Any, Optional
from dataclasses import dataclass

from google.cloud import bigquery
from google.oauth2 import service_account
from google.adk.tools.google_search_tool import google_search

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Environment variables
PROJECT_ID = os.getenv('GOOGLE_CLOUD_PROJECT', 'starlit-factor-472009-b0')
BUCKET_NAME = os.getenv('BUCKET_NAME', 'pitch-deck-analysis-bucket')
BIGQUERY_DATASET = os.getenv('BIGQUERY_DATASET', 'pitch_deck_analysis')
BIGQUERY_TABLE = os.getenv('BIGQUERY_TABLE', 'benchmark_analysis_results')
CREDENTIALS_PATH = os.getenv('GOOGLE_APPLICATION_CREDENTIALS')

@dataclass
class BenchmarkMetric:
    """Data class for benchmark metric structure"""
    name: str
    startup_value: str
    sector_median: str
    sector_top_quartile: str
    score: float  # 0.0 to 10.0
    assessment: str
    category: str = "Unknown"


class BenchmarkAnalysisEngine:
    """Enhanced Benchmark Analysis Engine with BigQuery integration"""

    def __init__(self):
        credentials = None
        if CREDENTIALS_PATH:
            credentials = service_account.Credentials.from_service_account_file(CREDENTIALS_PATH)
        self.client = bigquery.Client(project=PROJECT_ID, credentials=credentials)
        self.benchmark_categories = [
            "financial_benchmarks",
            "traction_benchmarks",
            "market_benchmarks",
            "technology_benchmarks",
            "team_benchmarks",
            "funding_benchmarks"
        ]

    def analyze_startup_benchmarks(self, company_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Main function to analyze startup benchmarks and return structured JSON

        Args:
            company_data: Dictionary containing startup information

        Returns:
            Complete benchmark analysis with JSON structure
        """
        try:
            logger.info(f"Starting benchmark analysis for: {company_data.get('company_name', 'Unknown')}")

            # Generate dynamic benchmark metrics
            benchmark_metrics = self._generate_dynamic_benchmarks(company_data)

            # Calculate overall score and recommendation
            overall_score = self._calculate_overall_score(benchmark_metrics, company_data)
            investment_rec = self._determine_investment_recommendation(overall_score)

            # Create structured response
            analysis_result = {
                "company_id": company_data.get("company_id", str(uuid.uuid4())),
                "company_name": company_data.get("company_name", "Unknown"),
                "analysis_date": datetime.utcnow().isoformat(),
                "session_id": str(uuid.uuid4()),
                "benchmark_metrics": self._format_benchmark_metrics_json(benchmark_metrics),
                "investment_recommendation": investment_rec,
                "overall_score": overall_score,
                "investment_pros": self._generate_investment_pros(benchmark_metrics, company_data),
                "investment_cons": self._generate_investment_cons(benchmark_metrics, company_data),
                "investment_horizon": self._determine_investment_horizon(company_data),
                "return_potential": self._assess_return_potential(overall_score),
                "competitive_positioning": self._analyze_competitive_positioning(company_data),
                "financial_multiples": self._calculate_financial_multiples(company_data),
                "investment_thesis": self._generate_investment_thesis(company_data, overall_score),
                "confidence_score": self._calculate_confidence_score(company_data, benchmark_metrics)
            }

            # Save to BigQuery
            success = self._save_to_bigquery(analysis_result)
            analysis_result["bigquery_saved"] = success

            if success:
                logger.info(
                    f"[BigQuery] Successfully saved benchmark analysis for company: {analysis_result['company_name']}")
            else:
                logger.error(
                    f"[BigQuery] Failed to save benchmark analysis for company: {analysis_result['company_name']}")

            logger.info(f"Benchmark analysis completed for: {analysis_result['company_name']}")
            return analysis_result

        except Exception as e:
            logger.error(f"Benchmark analysis failed: {str(e)}")
            return {
                "success": False,
                "error": str(e),
                "company_name": company_data.get("company_name", "Unknown")
            }

    def _generate_dynamic_benchmarks(self, company_data: Dict[str, Any]) -> Dict[str, List[BenchmarkMetric]]:
        """Generate dynamic benchmark metrics based on company data and sector"""
        benchmarks = {
            "financial_benchmarks": [],
            "traction_benchmarks": [],
            "market_benchmarks": [],
            "technology_benchmarks": [],
            "team_benchmarks": [],
            "funding_benchmarks": []
        }

        sector = company_data.get("sector", "SaaS").lower()
        stage = company_data.get("stage", "Series_B").lower()

        # Financial Benchmarks
        revenue_growth = company_data.get("revenue_growth_yoy", 0)
        sector_median_growth = self._get_sector_median(sector, "revenue_growth", 45)

        revenue_benchmark = BenchmarkMetric(
            name="revenue_growth_yoy",
            startup_value=f"{revenue_growth}%",
            sector_median=f"{sector_median_growth}%",
            sector_top_quartile=f"{int(sector_median_growth * 1.8)}%",
            score=self._calculate_percentile_score(revenue_growth, sector_median_growth, "higher_better"),
            assessment=self._generate_assessment(revenue_growth, sector_median_growth, "higher_better"),
            category="Financial"
        )
        benchmarks["financial_benchmarks"].append(revenue_benchmark)

        # Burn Multiple
        burn_multiple = company_data.get("burn_multiple", 0)
        sector_burn_median = self._get_sector_median(sector, "burn_multiple", 3.5)

        burn_benchmark = BenchmarkMetric(
            name="burn_multiple",
            startup_value=f"{burn_multiple}x",
            sector_median=f"{sector_burn_median}x",
            sector_top_quartile=f"{sector_burn_median * 0.6:.1f}x",
            score=self._calculate_percentile_score(burn_multiple, sector_burn_median, "lower_better"),
            assessment=self._generate_assessment(burn_multiple, sector_burn_median, "lower_better"),
            category="Financial"
        )
        benchmarks["financial_benchmarks"].append(burn_benchmark)

        # Market Benchmarks
        tam = company_data.get("total_addressable_market", 0)

        tam_benchmark = BenchmarkMetric(
            name="total_addressable_market",
            startup_value=f"${tam / 1000000000:.1f}B" if tam > 1000000000 else f"${tam / 1000000:.0f}M",
            sector_median="$2.5B",
            sector_top_quartile="$10B",
            score=self._calculate_tam_score(tam),
            assessment=self._generate_tam_assessment(tam),
            category="Market"
        )
        benchmarks["market_benchmarks"].append(tam_benchmark)

        # Technology Benchmarks
        tech_differentiation = company_data.get("technology_differentiation_score", 5)

        tech_benchmark = BenchmarkMetric(
            name="technology_differentiation",
            startup_value=f"{tech_differentiation}/10",
            sector_median="6/10",
            sector_top_quartile="8/10",
            score=tech_differentiation,
            assessment=self._generate_tech_assessment(tech_differentiation),
            category="Technology"
        )
        benchmarks["technology_benchmarks"].append(tech_benchmark)

        # Team Benchmarks
        team_experience = company_data.get("team_experience_score", 5)

        team_benchmark = BenchmarkMetric(
            name="team_experience",
            startup_value=f"{team_experience}/10",
            sector_median="6/10",
            sector_top_quartile="8/10",
            score=team_experience,
            assessment=self._generate_team_assessment(team_experience),
            category="Team"
        )
        benchmarks["team_benchmarks"].append(team_benchmark)

        # Traction Benchmarks
        customer_count = company_data.get("customer_count", 0)
        sector_customer_median = self._get_sector_median(sector, "customer_count", 500)

        traction_benchmark = BenchmarkMetric(
            name="customer_count",
            startup_value=str(customer_count),
            sector_median=str(sector_customer_median),
            sector_top_quartile=str(int(sector_customer_median * 2)),
            score=self._calculate_percentile_score(customer_count, sector_customer_median, "higher_better"),
            assessment=self._generate_assessment(customer_count, sector_customer_median, "higher_better"),
            category="Traction"
        )
        benchmarks["traction_benchmarks"].append(traction_benchmark)

        # Funding Benchmarks
        funding_efficiency = company_data.get("funding_efficiency_score", 5)

        funding_benchmark = BenchmarkMetric(
            name="funding_efficiency",
            startup_value=f"{funding_efficiency}/10",
            sector_median="6/10",
            sector_top_quartile="8/10",
            score=funding_efficiency,
            assessment=self._generate_funding_assessment(funding_efficiency),
            category="Funding"
        )
        benchmarks["funding_benchmarks"].append(funding_benchmark)

        return benchmarks

    def _get_sector_median(self, sector: str, metric: str, default: float) -> float:
        """Get sector median for specific metric"""
        sector_medians = {
            "saas": {
                "revenue_growth": 65,
                "burn_multiple": 2.8,
                "cac_payback": 18,
                "customer_count": 800
            },
            "ecommerce": {
                "revenue_growth": 85,
                "burn_multiple": 4.2,
                "cac_payback": 12,
                "customer_count": 2000
            },
            "fintech": {
                "revenue_growth": 75,
                "burn_multiple": 3.2,
                "cac_payback": 15,
                "customer_count": 1200
            },
            "marketplace": {
                "revenue_growth": 90,
                "burn_multiple": 3.8,
                "cac_payback": 14,
                "customer_count": 5000
            }
        }
        return sector_medians.get(sector, {}).get(metric, default)

    def _calculate_percentile_score(self, value: float, median: float, direction: str) -> float:
        """Calculate percentile score (0-10) based on value vs median"""
        if median == 0:
            return 5.0

        ratio = value / median

        if direction == "higher_better":
            if ratio >= 2.0:
                return 10.0
            elif ratio >= 1.5:
                return 8.5
            elif ratio >= 1.2:
                return 7.0
            elif ratio >= 1.0:
                return 6.0
            elif ratio >= 0.8:
                return 4.0
            else:
                return 2.0
        else:  # lower_better
            if ratio <= 0.5:
                return 10.0
            elif ratio <= 0.7:
                return 8.5
            elif ratio <= 0.9:
                return 7.0
            elif ratio <= 1.1:
                return 6.0
            elif ratio <= 1.3:
                return 4.0
            else:
                return 2.0

    def _generate_assessment(self, value: float, median: float, direction: str) -> str:
        """Generate text assessment based on performance"""
        if median == 0:
            return "Insufficient data for comparison"

        ratio = value / median

        if direction == "higher_better":
            if ratio >= 2.0:
                return "Exceptional - significantly outperforming sector"
            elif ratio >= 1.2:
                return "Strong - above sector median"
            elif ratio >= 0.8:
                return "Average - near sector median"
            else:
                return "Below Average - underperforming sector"
        else:
            if ratio <= 0.7:
                return "Exceptional - significantly more efficient than sector"
            elif ratio <= 1.1:
                return "Strong - better than sector median"
            elif ratio <= 1.3:
                return "Average - near sector median"
            else:
                return "Below Average - less efficient than sector"

    def _calculate_tam_score(self, tam: float) -> float:
        """Calculate TAM score based on market size"""
        if tam >= 50000000000:  # $50B+
            return 10.0
        elif tam >= 10000000000:  # $10B+
            return 8.5
        elif tam >= 5000000000:  # $5B+
            return 7.0
        elif tam >= 1000000000:  # $1B+
            return 6.0
        elif tam >= 500000000:  # $500M+
            return 4.0
        else:
            return 2.0

    def _generate_tam_assessment(self, tam: float) -> str:
        """Generate TAM assessment"""
        if tam >= 50000000000:
            return "Exceptional - massive addressable market"
        elif tam >= 10000000000:
            return "Strong - large addressable market"
        elif tam >= 1000000000:
            return "Good - significant market opportunity"
        else:
            return "Limited - smaller market opportunity"

    def _generate_tech_assessment(self, score: float) -> str:
        """Generate technology differentiation assessment"""
        if score >= 8:
            return "Strong - clear competitive moats"
        elif score >= 6:
            return "Good - some differentiation"
        elif score >= 4:
            return "Average - limited differentiation"
        else:
            return "Weak - commoditized offering"

    def _generate_team_assessment(self, score: float) -> str:
        """Generate team experience assessment"""
        if score >= 8:
            return "Exceptional - proven leadership team"
        elif score >= 6:
            return "Strong - experienced team"
        elif score >= 4:
            return "Average - mixed experience"
        else:
            return "Weak - limited relevant experience"

    def _generate_funding_assessment(self, score: float) -> str:
        """Generate funding efficiency assessment"""
        if score >= 8:
            return "Excellent - highly efficient capital usage"
        elif score >= 6:
            return "Good - reasonable funding efficiency"
        elif score >= 4:
            return "Average - typical capital requirements"
        else:
            return "Poor - inefficient capital usage"

    def _calculate_overall_score(self, benchmark_metrics: Dict[str, List[BenchmarkMetric]],
                                 company_data: Dict[str, Any]) -> float:
        """Calculate weighted overall score"""
        stage = company_data.get("stage", "series_b").lower()
        sector = company_data.get("sector", "saas").lower()

        # Dynamic weights based on stage and sector
        weights = self._get_dynamic_weights(stage, sector)

        category_scores = {}
        for category, metrics in benchmark_metrics.items():
            if metrics:
                category_scores[category] = sum(metric.score for metric in metrics) / len(metrics)

        # Apply weights
        weighted_score = 0.0
        for category, weight in weights.items():
            score = category_scores.get(category, 5.0)  # Default to 5.0 if missing
            weighted_score += score * weight

        return round(weighted_score, 1)

    def _get_dynamic_weights(self, stage: str, sector: str) -> Dict[str, float]:
        """Get dynamic weights based on stage and sector"""
        base_weights = {
            "financial_benchmarks": 0.25,
            "market_benchmarks": 0.20,
            "technology_benchmarks": 0.20,
            "team_benchmarks": 0.15,
            "traction_benchmarks": 0.15,
            "funding_benchmarks": 0.05
        }

        # Stage adjustments
        if "seed" in stage or "pre_series_a" in stage:
            base_weights["team_benchmarks"] += 0.10
            base_weights["financial_benchmarks"] -= 0.05
            base_weights["traction_benchmarks"] -= 0.05
        elif "series_b" in stage or "growth" in stage:
            base_weights["financial_benchmarks"] += 0.10
            base_weights["team_benchmarks"] -= 0.05
            base_weights["market_benchmarks"] -= 0.05
        elif "pre_ipo" in stage or "late" in stage:
            base_weights["financial_benchmarks"] += 0.15
            base_weights["funding_benchmarks"] += 0.05
            base_weights["technology_benchmarks"] -= 0.10
            base_weights["team_benchmarks"] -= 0.10

        # Sector adjustments
        if sector == "fintech":
            base_weights["financial_benchmarks"] += 0.10
            base_weights["technology_benchmarks"] += 0.05
            base_weights["market_benchmarks"] -= 0.10
            base_weights["team_benchmarks"] -= 0.05
        elif sector == "healthcare" or sector == "biotech":
            base_weights["technology_benchmarks"] += 0.10
            base_weights["team_benchmarks"] += 0.10
            base_weights["traction_benchmarks"] -= 0.10
            base_weights["financial_benchmarks"] -= 0.10

        return base_weights

    def _determine_investment_recommendation(self, overall_score: float) -> str:
        """Determine investment recommendation based on overall score"""
        if overall_score >= 9.0:
            return "STRONG BUY"
        elif overall_score >= 7.5:
            return "BUY"
        elif overall_score >= 6.0:
            return "HOLD"
        elif overall_score >= 4.0:
            return "WEAK BUY"
        else:
            return "AVOID"

    def _generate_investment_pros(self, benchmark_metrics: Dict[str, List[BenchmarkMetric]],
                                  company_data: Dict[str, Any]) -> List[str]:
        """Generate investment pros based on strong metrics"""
        pros = []

        # Find top performing metrics
        all_metrics = []
        for category_metrics in benchmark_metrics.values():
            all_metrics.extend(category_metrics)

        top_metrics = sorted(all_metrics, key=lambda x: x.score, reverse=True)[:6]

        for metric in top_metrics:
            if metric.score >= 7.0:
                pros.append(f"**{metric.name.replace('_', ' ').title()}**: {metric.assessment}")

        # Add company-specific pros
        if company_data.get("revenue_growth_yoy", 0) > 100:
            pros.append(f"**Strong Revenue Growth**: {company_data['revenue_growth_yoy']}% YoY growth rate")

        return pros[:6]  # Top 6 pros

    def _generate_investment_cons(self, benchmark_metrics: Dict[str, List[BenchmarkMetric]],
                                  company_data: Dict[str, Any]) -> List[str]:
        """Generate investment cons based on weak metrics"""
        cons = []

        # Find bottom performing metrics
        all_metrics = []
        for category_metrics in benchmark_metrics.values():
            all_metrics.extend(category_metrics)

        bottom_metrics = sorted(all_metrics, key=lambda x: x.score)[:6]

        for metric in bottom_metrics:
            if metric.score <= 5.0:
                cons.append(f"**{metric.name.replace('_', ' ').title()}**: {metric.assessment}")

        # Add standard risk cons
        cons.extend([
            "**Market Competition**: Intense competitive landscape",
            "**Execution Risk**: Achieving growth targets depends on execution"
        ])

        return cons[:6]  # Top 6 cons

    def _determine_investment_horizon(self, company_data: Dict[str, Any]) -> str:
        """Determine recommended investment horizon"""
        stage = company_data.get("stage", "series_b").lower()

        if "pre_ipo" in stage:
            return "12-18M"
        elif "series_c" in stage or "late" in stage:
            return "18-24M"
        else:
            return "24-36M"

    def _assess_return_potential(self, overall_score: float) -> str:
        """Assess return potential based on overall score"""
        if overall_score >= 8.5:
            return "High"
        elif overall_score >= 6.5:
            return "Medium"
        else:
            return "Low"

    def _format_benchmark_metrics_json(self, benchmark_metrics: Dict[str, List[BenchmarkMetric]]) -> Dict[str, Dict]:
        """Format benchmark metrics into the requested JSON structure"""
        formatted_metrics = {}

        for category, metrics in benchmark_metrics.items():
            formatted_metrics[category] = {}
            for metric in metrics:
                formatted_metrics[category][metric.name] = {
                    "startup_value": metric.startup_value,
                    "sector_median": metric.sector_median,
                    "sector_top_quartile": metric.sector_top_quartile,
                    "score": metric.score,
                    "assessment": metric.assessment
                }

        return formatted_metrics

    def _analyze_competitive_positioning(self, company_data: Dict[str, Any]) -> Dict[str, str]:
        """Analyze competitive positioning"""
        return {
            "market_position": company_data.get("market_position", "Unknown"),
            "key_differentiators": company_data.get("key_differentiators", "Not specified"),
            "competitive_advantages": company_data.get("competitive_advantages", "Not specified")
        }

    def _calculate_financial_multiples(self, company_data: Dict[str, Any]) -> Dict[str, float]:
        """Calculate key financial multiples"""
        return {
            "price_to_sales": company_data.get("price_to_sales_ratio", 0),
            "ev_to_revenue": company_data.get("ev_to_revenue_ratio", 0),
            "ltv_to_cac": company_data.get("ltv_cac_ratio", 0)
        }

    def _generate_investment_thesis(self, company_data: Dict[str, Any], overall_score: float) -> str:
        """Generate investment thesis summary"""
        company_name = company_data.get("company_name", "Company")
        sector = company_data.get("sector", "technology")

        if overall_score >= 8.0:
            thesis = f"{company_name} presents a compelling investment opportunity in the {sector} sector with strong fundamentals and clear competitive advantages."
        elif overall_score >= 6.0:
            thesis = f"{company_name} shows solid potential in the {sector} market with decent fundamentals, though some execution risks remain."
        else:
            thesis = f"{company_name} faces significant challenges in the competitive {sector} landscape with concerning fundamentals."

        return thesis

    def _calculate_confidence_score(self, company_data: Dict[str, Any],
                                    benchmark_metrics: Dict[str, List[BenchmarkMetric]]) -> float:
        """Calculate confidence score based on data completeness"""
        total_fields = len(company_data)
        filled_fields = sum(1 for value in company_data.values() if value not in [None, "", 0, []])

        return round(filled_fields / total_fields if total_fields > 0 else 0.0, 2)

    def _save_to_bigquery(self, analysis_result: Dict[str, Any]) -> bool:
        """Save complete benchmark analysis to BigQuery"""
        try:
            # Prepare row data for BigQuery
            row_data = {
                'company_id': analysis_result.get('company_id'),
                'company_name': analysis_result.get('company_name'),
                'analysis_date': analysis_result.get('analysis_date'),
                'session_id': analysis_result.get('session_id'),
                'investment_recommendation': analysis_result.get('investment_recommendation'),
                'overall_score': analysis_result.get('overall_score', 0.0),
                'confidence_score': analysis_result.get('confidence_score', 0.0),
                'investment_horizon': analysis_result.get('investment_horizon'),
                'return_potential': analysis_result.get('return_potential'),

                # Store complete benchmark metrics as JSON
                'benchmark_metrics_json': json.dumps(analysis_result.get('benchmark_metrics', {})),

                # Store investment analysis as JSON
                'investment_pros_json': json.dumps(analysis_result.get('investment_pros', [])),
                'investment_cons_json': json.dumps(analysis_result.get('investment_cons', [])),

                # Store additional analysis as JSON
                'competitive_positioning_json': json.dumps(analysis_result.get('competitive_positioning', {})),
                'financial_multiples_json': json.dumps(analysis_result.get('financial_multiples', {})),

                # Processing metadata
                'processing_status': 'SUCCESS',
                'created_at': datetime.utcnow().isoformat(),
                'updated_at': datetime.utcnow().isoformat()
            }

            # Insert to BigQuery
            table_ref = self.client.dataset(BIGQUERY_DATASET).table(BIGQUERY_TABLE)
            table = self.client.get_table(table_ref)
            errors = self.client.insert_rows_json(table, [row_data])

            if errors:
                logger.error(f"BigQuery errors: {errors}")
                return False

            logger.info(f"Benchmark analysis saved to BigQuery: {analysis_result.get('company_name')}")
            return True

        except Exception as e:
            logger.error(f"BigQuery save failed: {str(e)}")
            return False


# Initialize the benchmark analysis engine
benchmark_engine = BenchmarkAnalysisEngine()


# Tool functions for the ADK agent
def analyze_startup_benchmarks(company_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Tool function: Analyze startup benchmarks and return structured results

    Args:
        company_data: Dictionary containing startup information including:
            - company_name, sector, stage, revenue_growth_yoy, burn_multiple,
            - total_addressable_market, technology_differentiation_score, etc.

    Returns:
        Complete benchmark analysis with JSON structure matching requirements
    """
    return benchmark_engine.analyze_startup_benchmarks(company_data)


def query_benchmark_data(company_name: Optional[str] = None, limit: int = 10) -> Dict[str, Any]:
    """
    Tool function: Query historical benchmark analysis results from BigQuery

    Args:
        company_name: Optional company name to filter results
        limit: Maximum number of results to return

    Returns:
        Historical benchmark analysis data
    """
    try:
        client = benchmark_engine.client

        where_clause = f"WHERE company_name = '{company_name}'" if company_name else ""

        query = f"""
        SELECT
            company_name,
            investment_recommendation,
            overall_score,
            confidence_score,
            investment_horizon,
            return_potential,
            analysis_date,
            benchmark_metrics_json,
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
                "investment_recommendation": row.investment_recommendation,
                "overall_score": row.overall_score,
                "confidence_score": row.confidence_score,
                "investment_horizon": row.investment_horizon,
                "return_potential": row.return_potential,
                "analysis_date": row.analysis_date,
                "processing_status": row.processing_status
            }

            # Parse benchmark metrics JSON if needed
            if hasattr(row, 'benchmark_metrics_json') and row.benchmark_metrics_json:
                analysis["benchmark_metrics"] = json.loads(row.benchmark_metrics_json)

            analyses.append(analysis)

        return {
            "success": True,
            "count": len(analyses),
            "analyses": analyses
        }

    except Exception as e:
        logger.error(f"Query failed: {str(e)}")
        return {"success": False, "error": str(e)}


def fetch_market_comparables(sector: str, stage: str, limit: int = 20) -> Dict[str, Any]:
    """
    Tool function: Fetch market comparables for benchmarking

    Args:
        sector: Industry sector (e.g., 'SaaS', 'Fintech', 'E-commerce')
        stage: Funding stage (e.g., 'Series_A', 'Series_B', 'Growth')
        limit: Maximum number of comparables to return

    Returns:
        Market comparable data for benchmarking
    """
    try:
        # Mock data for now - in production, this would fetch from external APIs
        # or databases with real comparable company data

        mock_comparables = {
            "sector": sector,
            "stage": stage,
            "comparables": [
                {
                    "company_name": "ComparableCo A",
                    "valuation_multiple": 12.5,
                    "revenue_growth_yoy": 70,
                    "burn_multiple": 2.5
                },
                {
                    "company_name": "ComparableCo B",
                    "valuation_multiple": 9.8,
                    "revenue_growth_yoy": 55,
                    "burn_multiple": 3.1
                },
                {
                    "company_name": "ComparableCo C",
                    "valuation_multiple": 15.0,
                    "revenue_growth_yoy": 85,
                    "burn_multiple": 1.9
                }
            ]
        }
        return {"success": True, "data": mock_comparables}
    except Exception as e:
        logger.error(f"Fetching market comparables failed: {str(e)}")
        return {"success": False, "error": str(e)}


def calculate_financial_multiples(company_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Tool function: Calculate key financial multiples for a startup.

    Args:
        company_data: Dictionary containing financial metrics like revenue and valuation.

    Returns:
        A dictionary of calculated financial multiples.
    """
    try:
        multiples = benchmark_engine._calculate_financial_multiples(company_data)
        return {"success": True, "multiples": multiples}
    except Exception as e:
        logger.error(f"Calculating financial multiples failed: {str(e)}")
        return {"success": False, "error": str(e)}