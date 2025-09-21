"""A simple agent that uses the google_search tool."""

from google.adk.agents import Agent
from google.adk.tools import google_search

search_agent = Agent(
    model='gemini-2.5-flash',
    name='SearchAgent',
    instruction="You're a specialist in Google Search",
    tools=[google_search],
)