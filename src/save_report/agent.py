from dotenv import load_dotenv
from langchain_openai import ChatOpenAI
from langgraph.checkpoint.memory import InMemorySaver
from langgraph.prebuilt import create_react_agent

from config import settings
from save_report.prompt import SYSTEM_PROMPT
from tools import list_files, read_file, write_report

load_dotenv()

tools = [read_file, list_files, write_report]

llm = ChatOpenAI(model=settings.model_name)
checkpointer = InMemorySaver()

RECURSION_LIMIT = 12

save_report_agent = create_react_agent(
    model=llm,
    tools=tools,
    prompt=SYSTEM_PROMPT,
    checkpointer=checkpointer,
)
