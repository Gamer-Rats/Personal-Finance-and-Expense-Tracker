from pydantic import BaseModel
from fastapi import status
from app.dependencies.auth import AuthDep
from app.services.ai_chat import AIChatService
from . import api_router


class ChatRequest(BaseModel):
    message: str
    session_id: str | None = None


@api_router.post("/chat", status_code=status.HTTP_200_OK)
async def chat_with_assistant(payload: ChatRequest, user: AuthDep):
    service = AIChatService()
    reply = await service.ask(user.username, payload.message, payload.session_id)
    return {"reply": reply}
