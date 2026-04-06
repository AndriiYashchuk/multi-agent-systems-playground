from dotenv import load_dotenv
from langchain_openai import ChatOpenAI
from langgraph.checkpoint.memory import InMemorySaver
from langgraph.prebuilt import create_react_agent

from config import settings
from research_agent.prompt import SYSTEM_PROMPT
from tools import knowledge_search, read_url, web_search

load_dotenv()

tools = [web_search, read_url, knowledge_search]

llm = ChatOpenAI(model=settings.model_name)
checkpointer = InMemorySaver()

RECURSION_LIMIT = 15

research_agent = create_react_agent(
    model=llm,
    tools=tools,
    prompt=SYSTEM_PROMPT,
    checkpointer=checkpointer,
)
