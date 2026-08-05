import os

import httpx

ACCESS_TOKEN = os.environ["WHATSAPP_ACCESS_TOKEN"]
PHONE_NUMBER_ID = os.environ["WHATSAPP_PHONE_NUMBER_ID"]

BASE_URL = f"https://graph.facebook.com/v23.0/{PHONE_NUMBER_ID}/messages"
HEADERS = {"Authorization": f"Bearer {ACCESS_TOKEN}"}


def send_text(to: str, body: str) -> str:
    """Send a text message. `to` must be E.164 with no leading '+' or '0'
    (e.g. Nigerian numbers: 234XXXXXXXXXX). Returns the outbound wamid."""
    resp = httpx.post(
        BASE_URL,
        headers=HEADERS,
        json={
            "messaging_product": "whatsapp",
            "recipient_type": "individual",
            "to": to,
            "type": "text",
            "text": {"body": body},
        },
    )
    resp.raise_for_status()
    return resp.json()["messages"][0]["id"]