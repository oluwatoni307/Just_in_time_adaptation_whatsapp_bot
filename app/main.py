import hashlib
import hmac
import os

from fastapi import FastAPI, Request, Response

from app.response_handling_and_logging.handleIncomingMessage import handle_incoming_message

VERIFY_TOKEN = os.environ["VERIFY_TOKEN"]
APP_SECRET = os.environ["APP_SECRET"]

print(f"DEBUG APP_SECRET starts_with={APP_SECRET[:6]!r} length={len(APP_SECRET)}")  # TODO: remove after debugging

app = FastAPI()


@app.get("/webhooks")
def verify(request: Request):
    params = request.query_params
    if params.get("hub.mode") == "subscribe" and params.get("hub.verify_token") == VERIFY_TOKEN:
        return Response(content=params.get("hub.challenge"), status_code=200)
    return Response(status_code=403)


@app.post("/webhooks")
async def receive(request: Request):
    body = await request.body()
    sig = request.headers.get("X-Hub-Signature-256", "")
    expected = "sha256=" + hmac.new(APP_SECRET.encode(), body, hashlib.sha256).hexdigest()

    print(f"DEBUG expected={expected!r} received={sig!r}")  # TODO: remove after debugging

    if not hmac.compare_digest(expected, sig):
        return Response(status_code=403)

    payload = await request.json()

    for entry in payload.get("entry", []):
        for change in entry.get("changes", []):
            value = change.get("value", {})

            for msg in value.get("messages", []):
                msg_type = msg.get("type")

                if msg_type == "text":
                    handle_text(sender=msg.get("from"), message_id=msg.get("id"), body=msg["text"]["body"])

                elif msg_type == "reaction":
                    reaction = msg.get("reaction", {})
                    handle_reaction(
                        sender=msg.get("from"),
                        reacted_message_id=reaction.get("message_id"),
                        emoji=reaction.get("emoji"),
                    )

    return Response(status_code=200)


def _normalize_phone(whatsapp_number: str) -> str:
    if whatsapp_number.startswith("234") and len(whatsapp_number) == 13:
        return "0" + whatsapp_number[3:]
    return whatsapp_number


class IncomingMessage:
    def __init__(self, userId: str, text: str, type: str = "text"):
        self.userId = userId
        self.text = text
        self.type = type


def handle_text(sender: str, message_id: str, body: str):
    phone_number = _normalize_phone(sender)
    message = IncomingMessage(userId=phone_number, text=body, type="text")
    handle_incoming_message(message)


def handle_reaction(sender: str, reacted_message_id: str, emoji: str | None):
    print({"sender": sender, "reacted_message_id": reacted_message_id, "emoji": emoji})