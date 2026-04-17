from __future__ import annotations

from dotenv import load_dotenv
from langchain_openai import ChatOpenAI

from config import settings
from prompt import SYSTEM_PROMPT
from hw_4.tools import TOOL_MAP, TOOL_SCHEMAS
from hw_4.simple_memory import SimpleMemory
from hw_4.custom_react_agent import CustomReActAgent

load_dotenv()

llm = ChatOpenAI(
    model=settings.model_name,
    temperature=0,
)

memory = SimpleMemory()

agent = CustomReActAgent(
    model=llm,
    tool_schemas=TOOL_SCHEMAS,
    tool_map=TOOL_MAP,
    system_prompt=SYSTEM_PROMPT,
    memory=memory,
    max_iterations=10,
)
