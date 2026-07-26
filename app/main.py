from fastapi import FastAPI
from pydantic import BaseModel

from .database import Base, engine
from .channel import send_message
from .resolution import resolve_pending_messages

Base.metadata.create_all(bind=engine)

app = FastAPI(title="bluedrop-bot")


class DebugSendRequest(BaseModel):
    user_id: int
    arm: str
    content: str


@app.post("/debug/send")
def debug_send(payload: DebugSendRequest):
    log_id = send_message(payload.user_id, payload.arm, payload.content)
    return {"status": "sent", "log_id": log_id}


@app.post("/debug/resolve")
def debug_resolve():
    resolve_pending_messages()
    return {"status": "resolution job ran"}