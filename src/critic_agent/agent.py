from typing import Literal

from dotenv import load_dotenv
from langchain.agents import create_agent
from langchain_openai import ChatOpenAI
from pydantic import BaseModel, Field

from config import settings
from critic_agent.prompt import SYSTEM_PROMPT
from tools import knowledge_search, read_url, web_search

load_dotenv()

llm = ChatOpenAI(model=settings.model_name)


class DimensionReview(BaseModel):
    sufficient: bool = Field(
        description="True if this dimension meets the bar for approval; false if insufficient",
    )
    reasoning: str = Field(
        description=(
            "Explicit assessment: for freshness include recency vs. today's date; "
            "for completeness cover the original request; for structure, report-readiness"
        ),
    )


class CriticVerdict(BaseModel):
    decision: Literal["APPROVE", "REVISE"] = Field(
        description="APPROVE only if freshness, completeness, and structure are all sufficient",
    )
    freshness: DimensionReview
    completeness: DimensionReview
    structure: DimensionReview
    strengths: list[str] = Field(
        description="What is already good and should be preserved",
    )
    gaps: list[str] = Field(
        description="What is missing, outdated, weakly supported, or poorly organized",
    )
    revision_requests: list[str] = Field(
        description="Precise actionable tasks for the researcher; empty when decision is APPROVE",
    )


RECURSION_LIMIT = 25

critic_agent = create_agent(
    model=llm,
    tools=[web_search, read_url, knowledge_search],
    system_prompt=SYSTEM_PROMPT,
    response_format=CriticVerdict,
)
