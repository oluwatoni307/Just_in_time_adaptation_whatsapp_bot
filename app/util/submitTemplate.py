"""
One-off script: submits every message in library.py's MESSAGE_LIBRARY to
Meta as a WhatsApp message template for review.

Run once: python -m app.util.submit_templates

Templates take hours to days to get approved (longer for MARKETING
category). Check status in WhatsApp Manager -> Message Templates, or via
GET /{WABA_ID}/message_templates.

Requires WHATSAPP_BUSINESS_ACCOUNT_ID (different from WHATSAPP_PHONE_NUMBER_ID
— this is the WABA ID, found in WhatsApp Manager -> Overview).
"""

import os
import re
import requests

from app.util.library import MESSAGE_LIBRARY

WHATSAPP_TOKEN = os.environ.get("WHATSAPP_ACCESS_TOKEN")
WABA_ID = os.environ.get("WHATSAPP_BUSINESS_ACCOUNT_ID")
API_URL = f"https://graph.facebook.com/v21.0/{WABA_ID}/message_templates"


def _slugify(arm_name: str, index: int) -> str:
    """Template names: lowercase, underscores only, must be unique."""
    return f"hydration_{arm_name}_{index}"


def submit_all_templates():
    results = []
    for arm, messages in MESSAGE_LIBRARY.items():
        for i, text in enumerate(messages, start=1):
            name = _slugify(arm.value, i)

            payload = {
                "name": name,
                "language": "en",
                "category": "MARKETING",
                "components": [
                    {"type": "BODY", "text": text}
                ],
            }

            response = requests.post(
                API_URL,
                headers={"Authorization": f"Bearer {WHATSAPP_TOKEN}"},
                json=payload,
                timeout=10,
            )

            if response.status_code >= 400:
                print(f"FAILED  {name}: {response.status_code} {response.text}")
            else:
                print(f"SUBMITTED  {name}")

            results.append((name, response.status_code))

    return results


if __name__ == "__main__":
    submit_all_templates()