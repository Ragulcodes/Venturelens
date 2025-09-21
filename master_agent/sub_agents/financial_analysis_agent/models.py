"""
Pydantic models for Financial Analysis Agent output
"""

from typing import Optional, List, Dict
from pydantic import BaseModel, Field
from decimal import Decimal
from datetime import datetime


class KeyFinancialMetrics(BaseModel):
    """Key financial metrics of the company"""
    total_funding: str = Field(..., description="Total funding raised (e.g., '$26.4M')")
    current_valuation: str = Field(..., description="Current valuation in Crores (e.g., '₹1,270 Cr')")
    arr: str = Field(..., description="Annual Recurring Revenue in Crores (e.g., '₹100+ Cr')")
    fy24_revenue: str = Field(..., description="FY24 Revenue in Crores (e.g., '₹60.1 Cr')")
    fy24_loss: str = Field(..., description="FY24 Loss in Crores (e.g., '₹24.4 Cr')")


class GrowthMetrics(BaseModel):
    """Growth metrics and trends"""
    revenue_growth_4x_since_2022: str = Field(..., description="Revenue growth multiple since 2022 (e.g., '4x')")
    yoy_revenue_growth_fy24: str = Field(..., description="Year-over-year revenue growth percentage (e.g., '36%')")
    loss_reduction_fy24: str = Field(..., description="Loss reduction percentage in FY24 (e.g., '55%')")
    employee_growth_2025: str = Field(..., description="Employee growth percentage in 2025 (e.g., '4%')")


class FinancialHealth(BaseModel):
    """Financial health indicators"""
    current_ratio: str = Field(..., description="Current ratio (e.g., 2.9)")
    debt_equity_ratio: str = Field(..., description="Debt to Equity ratio (e.g., 23.0)")
    net_profit_margin: str = Field(..., description="Net profit margin percentage (e.g., '-40.6%')")
    ebitda_margin: str = Field(..., description="EBITDA margin percentage (e.g., '-29%')")


class ShareholdingDistribution(BaseModel):
    """Current shareholding distribution"""
    funds: str = Field(..., description="Percentage held by funds (e.g., 48.4)")
    founders: str = Field(..., description="Percentage held by founders (e.g., 19.95)")
    enterprises: str = Field(..., description="Percentage held by enterprises (e.g., 18.83)")
    esop_pool: str = Field(..., description="ESOP pool percentage (e.g., 4.03)")
    angels: str = Field(..., description="Percentage held by angel investors (e.g., 4.2)")
    others: str = Field(..., description="Percentage held by others (e.g., 4.62)")


class FundingRound(BaseModel):
    """Individual funding round details"""
    series: str = Field(..., description="Funding series name (e.g., 'Series C')")
    date: str = Field(..., description="Date of funding round (e.g., 'May 2025')")
    amount: str = Field(..., description="Amount raised in the round (e.g., '₹113 crore (~$13.2M)')")
    lead_investors: List[str] = Field(default_factory=list, description="List of lead investors")


class FuturePlans(BaseModel):
    """Future business plans and projections"""
    profitability_target: str = Field(..., description="Target for profitability (e.g., 'FY26')")
    ipo_readiness_timeline: str = Field(..., description="IPO readiness timeline (e.g., 'within 2 years')")
    arr_target: str = Field(..., description="ARR target and timeline (e.g., 'Double ARR in next 12-18 months')")


class FAOutput(BaseModel):
    """Complete Financial Analysis Output Model"""
    
    # Company identification
    company_name: str = Field(..., description="Name of the company being analyzed")
    analysis_date: Optional[str] = Field(None, description="Date of analysis")
    
    # Key sections from the dashboard
    key_financial_metrics: KeyFinancialMetrics = Field(..., description="Key financial metrics")
    growth_metrics: GrowthMetrics = Field(..., description="Growth metrics and trends")
    financial_health: FinancialHealth = Field(..., description="Financial health indicators")
    
    # Shareholding and funding
    shareholding_distribution: ShareholdingDistribution = Field(..., description="Current shareholding structure")
    funding_rounds: List[FundingRound] = Field(default_factory=list, description="List of funding rounds")
    
    # Future outlook
    future_plans: FuturePlans = Field(..., description="Future business plans and projections")
    
    # Additional insights
    key_insights: List[str] = Field(default_factory=list, description="Key insights from the analysis")
    risks: List[str] = Field(default_factory=list, description="Identified risks")
    opportunities: List[str] = Field(default_factory=list, description="Identified opportunities")
    
    # References
    data_sources: List[str] = Field(default_factory=list, description="Data sources used for analysis")
    
    class Config:
        """Pydantic configuration"""
        json_schema_extra = {
            "example": {
                "company_name": "Example Corp",
                "analysis_date": "2025-01-01",
                "key_financial_metrics": {
                    "total_funding": "$26.4M",
                    "current_valuation": "₹1,270 Cr",
                    "arr": "₹100+ Cr",
                    "fy24_revenue": "₹60.1 Cr",
                    "fy24_loss": "₹24.4 Cr"
                },
                "growth_metrics": {
                    "revenue_growth_4x_since_2022": "4x",
                    "yoy_revenue_growth_fy24": "36%",
                    "loss_reduction_fy24": "55%",
                    "employee_growth_2025": "4%"
                },
                "financial_health": {
                    "current_ratio": 2.9,
                    "debt_equity_ratio": 23.0,
                    "net_profit_margin": "-40.6%",
                    "ebitda_margin": "-29%"
                },
                "shareholding_distribution": {
                    "funds": 48.4,
                    "founders": 19.95,
                    "enterprises": 18.83,
                    "esop_pool": 4.03,
                    "angels": 4.2,
                    "others": 4.62
                },
                "funding_rounds": [
                    {
                        "series": "Series C",
                        "date": "May 2025",
                        "amount": "₹113 crore (~$13.2M)",
                        "lead_investors": ["IndiaMART", "BEENEXT"]
                    },
                    {
                        "series": "Series B",
                        "date": "Feb 2022",
                        "amount": "$19.4M",
                        "lead_investors": ["IndiaMART", "IndiaQuotient", "BEENEXT"]
                    },
                    {
                        "series": "Series A",
                        "date": "Nov 2021",
                        "amount": "$161K",
                        "lead_investors": []
                    }
                ],
                "future_plans": {
                    "profitability_target": "FY26",
                    "ipo_readiness_timeline": "within 2 years",
                    "arr_target": "Double ARR in next 12-18 months"
                },
                "key_insights": [
                    "Strong revenue growth trajectory with 4x increase since 2022",
                    "Significant loss reduction of 55% in FY24",
                    "Healthy current ratio of 2.9 indicates good liquidity"
                ],
                "risks": [
                    "High debt-equity ratio at 23.0",
                    "Negative profit margins indicate ongoing losses",
                    "Dependency on external funding for growth"
                ],
                "opportunities": [
                    "Path to profitability by FY26",
                    "IPO opportunity within 2 years",
                    "Strong investor backing from established funds"
                ],
                "data_sources": [
                    "Company filings",
                    "Investor presentations",
                    "Market research reports"
                ]
            }
        }
