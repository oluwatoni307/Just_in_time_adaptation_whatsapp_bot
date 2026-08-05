import hashlib
import hmac
import os

from fastapi import FastAPI, Request, Response

VERIFY_TOKEN = os.environ["VERIFY_TOKEN"]
APP_SECRET = os.environ["APP_SECRET"]

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
                        emoji=reaction.get("emoji"),  # missing emoji = reaction removed
                    )

    return Response(status_code=200)


def handle_text(sender: str, message_id: str, body: str):
    print({"sender": sender, "message_id": message_id, "body": body})
    # TODO: your logic here


def handle_reaction(sender: str, reacted_message_id: str, emoji: str | None):
    # look up `reacted_message_id` against whatever you stored when you
    # originally sent/received that message, to know what it's about
    print({"sender": sender, "reacted_message_id": reacted_message_id, "emoji": emoji})
    # TODO: your logic here