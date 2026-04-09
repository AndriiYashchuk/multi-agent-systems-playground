from dotenv import load_dotenv
from langchain.agents import create_agent
from langchain.agents.middleware import HumanInTheLoopMiddleware
from langchain_openai import ChatOpenAI
from langgraph.checkpoint.memory import InMemorySaver

import workflow_log
from config import settings
from supervisor_prompt import supervisor_prompt
from tools import critique, plan, research, save_report

load_dotenv()
workflow_log.configure_workflow_logging()

SUPERVISOR_RECURSION_LIMIT = 50

supervisor = create_agent(
    model=ChatOpenAI(model=settings.model_name),
    tools=[plan, research, critique, save_report],
    system_prompt=supervisor_prompt,
    middleware=[
        HumanInTheLoopMiddleware(
            interrupt_on={"save_report": True},
        ),
    ],
    checkpointer=InMemorySaver(),
)

agent = supervisor
