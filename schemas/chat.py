from pydantic import UUID4, BaseModel, Field


class ChatRequest(BaseModel):
    session_id: UUID4
    message: str = Field(min_length=1, max_length=2000)


class ChatResponse(BaseModel):
    response: str
