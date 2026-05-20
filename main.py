from agents import Runner
import logging
from settings import settings
from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException, Request
from agents import SQLiteSession
from agent import GraduateAgent
from agents.mcp import MCPServerSse, MCPServerSseParams
from schemas.chat import ChatRequest, ChatResponse
from fastapi.middleware.cors import CORSMiddleware

logger = logging.getLogger(__name__)


server_params = MCPServerSseParams(url=settings.mcp_server_url)


@asynccontextmanager
async def lifespan(application: FastAPI):
    async with MCPServerSse(server_params) as server:
        application.state.agent = GraduateAgent().create_agent([server])
        yield


app = FastAPI(lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=False,
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)


@app.get("/")
def root():
    return {"status": "ok"}


@app.post("/chat", response_model=ChatResponse)
async def chat_message(chat_request: ChatRequest, request: Request) -> ChatResponse:
    agent = request.app.state.agent

    try:
        session = SQLiteSession(
            session_id=str(chat_request.session_id), db_path="/data/sessions.db"
        )
        result = await Runner.run(agent, chat_request.message, session=session)
    except Exception as err:
        logger.exception("Chat request failed")
        raise HTTPException(
            status_code=502,
            detail="The chat service is currently unavailable",
        ) from err

    if not result.final_output:
        logger.warning("Agent returned empty response")
        raise HTTPException(
            status_code=502,
            detail="The chat service returned no response",
        )

    return ChatResponse(response=result.final_output)
