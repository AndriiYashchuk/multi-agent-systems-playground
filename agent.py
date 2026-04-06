from dotenv import load_dotenv
from langchain_openai import ChatOpenAI
from langgraph.prebuilt import create_react_agent
from langgraph.checkpoint.memory import InMemorySaver

from config import settings
from prompt import SYSTEM_PROMPT
from tools import web_search, read_file, list_files, read_url, write_report, knowledge_search

load_dotenv()

tools = [web_search, read_file, list_files, read_url, write_report, knowledge_search]

llm = ChatOpenAI(model=settings.model_name)
checkpointer = InMemorySaver()

agent = create_react_agent(
    model=llm,
    tools=tools,
    prompt=SYSTEM_PROMPT,
    checkpointer=checkpointer,
)
