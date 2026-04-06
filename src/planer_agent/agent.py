from langchain.agents import create_agent
from tools import web_search, knowledge_search 
from planer_agent.prompt import SYSTEM_PROMPT
from langchain_openai import ChatOpenAI
from config import settings
from pydantic import BaseModel, Field

llm = ChatOpenAI(model=settings.model_name)


class ResearchPlan(BaseModel):
    goal: str = Field(description="What we are trying to answer")
    search_queries: list[str] = Field(description="Specific queries to execute")
    sources_to_check: list[str] = Field(description="'knowledge_base', 'web', or both")
    output_format: str = Field(description="What the final report should look like")



planner_agent = create_agent(
    model=llm,
    tools=[web_search, knowledge_search],
    system_prompt=SYSTEM_PROMPT,
    response_format=ResearchPlan,
)