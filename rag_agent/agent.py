from dotenv import load_dotenv
from langchain_openai import ChatOpenAI
from langgraph.prebuilt import create_react_agent
from langgraph.checkpoint.memory import InMemorySaver

from config import settings
from rag_agent.prompt import SEARCH_AGENT_PROMPT
from rag_agent.tools import search, expand_chunk_context

load_dotenv()

MAX_ITERATIONS = 5
# Each ReAct iteration = 1 LLM call + 1 tool call = 2 graph steps.
# Final LLM response adds 1 more step.
RECURSION_LIMIT = MAX_ITERATIONS * 2 + 1

tools = [search, expand_chunk_context]

llm = ChatOpenAI(model=settings.model_name)
checkpointer = InMemorySaver()

search_agent = create_react_agent(
    model=llm,
    tools=tools,
    prompt=SEARCH_AGENT_PROMPT,
    checkpointer=checkpointer,
)
