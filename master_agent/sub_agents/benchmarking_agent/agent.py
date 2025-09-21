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

from google.adk import Agent
from pydantic import BaseModel, Field,field_validator,ValidationInfo

from . import prompt
from . import tools
from typing import Dict, Any

import json
import re


class BenchmarkReportOutput(BaseModel):
    """Schema for the benchmark analysis agent's output"""
    investment_recommendation_report: str = Field(
        description="A comprehensive investment recommendation report with pros, cons, and detailed analysis.",
        default=""
    )
    benchmark_analysis_json: Dict[str, Any] = Field(
        description="Structured JSON containing all benchmark metrics with scores and assessments",
        default_factory=dict
    )
    investment_recommendation: str = Field(
        description="Investment recommendation (STRONG BUY/BUY/HOLD/WEAK BUY/AVOID)",
        default="HOLD"
    )
    overall_score: float = Field(
        description="Overall score out of 10.0",
        default=0.0
    )
    confidence_score: float = Field(
        description="Confidence score of the analysis (0.0 to 1.0)",
        default=0.0
    )
    bigquery_saved: bool = Field(
        description="Whether the analysis was successfully saved to BigQuery",
        default=False
    )

    @field_validator('benchmark_analysis_json', mode='before')
    def parse_benchmark_json(cls, v):
        """Parse benchmark JSON, handling markdown-wrapped JSON"""
        if isinstance(v, dict):
            return v

        if isinstance(v, str):
            # Remove markdown code block formatting
            v = re.sub(r'^```json\s*', '', v, flags=re.MULTILINE)
            v = re.sub(r'\s*```$', '', v, flags=re.MULTILINE)
            v = v.strip()

            try:
                return json.loads(v)
            except json.JSONDecodeError as e:
                print(f"JSON parsing error: {e}")
                print(f"Problematic JSON string: {v[:200]}...")
                return {}

        return {}


MODEL = "gemini-2.5-flash"

benchmarking_agent = Agent(
    model=MODEL,
    name="benchmarking_agent",
    instruction=prompt.BENCHMARK_AGENT_PROMPT,
    output_key="investment_recommendation_report",
    output_schema=BenchmarkReportOutput,
    tools=[
        tools.analyze_startup_benchmarks,
        tools.query_benchmark_data,
        tools.fetch_market_comparables,
        tools.calculate_financial_multiples

    ]
)
