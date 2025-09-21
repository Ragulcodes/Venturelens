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

"""Venturelens Master Agent: Comprehensive venture capital analysis coordinator"""

from google.adk.agents import LlmAgent
from google.adk.tools.agent_tool import AgentTool
from .sub_agents.search_agent.agent import search_agent

from . import prompt
from .sub_agents.document_preprocessing_agent.agent import document_preprocessing_agent
# from .sub_agents.market_research_agent.agent import market_research_agent
from .sub_agents.founder_analysis_agent.agent import founder_analysis_agent
from .sub_agents.risk_detection_agent.agent import risk_detection_agent
from .sub_agents.benchmarking_agent.agent import benchmarking_agent
from .sub_agents.financial_analysis_agent.agent import financial_analysis_agent
# from .sub_agents.reporting_agent.agent import reporting_agent

MODEL = "gemini-2.5-flash"


venturelens_master = LlmAgent(
    name="venturelens_master",
    model=MODEL,
    description=(
        "Comprehensive venture capital analysis coordinator that guides users "
        "through structured startup due diligence by orchestrating specialized "
        "subagents for document processing, market research, financial analysis, "
        "founder assessment, risk detection, benchmarking, and reporting."
    ),
    instruction=prompt.VENTURELENS_MASTER_PROMPT,
    output_key="venturelens_analysis_output",
    tools=[
        AgentTool(agent=search_agent),
        AgentTool(agent=financial_analysis_agent),
        AgentTool(agent=document_preprocessing_agent),
        AgentTool(agent=market_research_agent),
        AgentTool(agent=founder_analysis_agent),
        AgentTool(agent=risk_detection_agent),
        AgentTool(agent=benchmarking_agent),
        # AgentTool(agent=reporting_agent),
    ]
)

root_agent = venturelens_master