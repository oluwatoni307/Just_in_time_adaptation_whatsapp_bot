"""
messaging.py — pure WhatsApp Cloud API client. Knows nothing about users,
repo, or bandit arms — just sends text to a phone number.

REQUIRES environment variables:
    WHATSAPP_TOKEN
    WHATSAPP_PHONE_NUMBER_ID
"""

import logging
import os
from dataclasses import dataclass

import requests

logger = logging.getLogger("messaging")

WHATSAPP_TOKEN = os.environ.get("WHATSAPP_ACCESS_TOKEN")
WHATSAPP_PHONE_NUMBER_ID = os.environ.get("WHATSAPP_PHONE_NUMBER_ID")
WHATSAPP_API_URL = f"https://graph.facebook.com/v21.0/{WHATSAPP_PHONE_NUMBER_ID}/messages"


@dataclass
class SendResult:
    failed: bool
    error: str = ""


def send_whatsapp_text(phone_number: str, text: str) -> SendResult:
    try:
        response = requests.post(
            WHATSAPP_API_URL,
            headers={"Authorization": f"Bearer {WHATSAPP_TOKEN}"},
            json={
                "messaging_product": "whatsapp",
                "to": phone_number,
                "type": "text",
                "text": {"body": text},
            },
            timeout=10,
        )
        if response.status_code >= 400:
            return SendResult(failed=True, error=f"WhatsApp API error {response.status_code}: {response.text}")
        return SendResult(failed=False)
    except requests.RequestException as e:
        logger.error("send_whatsapp_text failed for phone_number=%s: %s", phone_number, e)
        return SendResult(failed=True, error=str(e))
def send_whatsapp_template(phone_number: str, template_name: str, language: str = "en") -> SendResult:
    try:
        response = requests.post(
            WHATSAPP_API_URL,
            headers={"Authorization": f"Bearer {WHATSAPP_TOKEN}"},
            json={
                "messaging_product": "whatsapp",
                "to": phone_number,
                "type": "template",
                "template": {
                    "name": template_name,
                    "language": {"code": language},
                },
            },
            timeout=10,
        )
        if response.status_code >= 400:
            return SendResult(failed=True, error=f"WhatsApp API error {response.status_code}: {response.text}")
        return SendResult(failed=False)
    except requests.RequestException as e:
        logger.error("send_whatsapp_template failed for phone_number=%s: %s", phone_number, e)
        return SendResult(failed=True, error=str(e))