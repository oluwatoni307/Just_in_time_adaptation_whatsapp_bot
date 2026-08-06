"""
Checks approval status of every submitted hydration_* template.

Run: python -m app.util.check_template_status
"""

import os
import requests
from dotenv import load_dotenv

load_dotenv()

WHATSAPP_TOKEN = os.environ.get("WHATSAPP_ACCESS_TOKEN")
WABA_ID = os.environ.get("WHATSAPP_BUSINESS_ACCOUNT_ID")
API_URL = f"https://graph.facebook.com/v21.0/{WABA_ID}/message_templates"


def check_status():
    response = requests.get(
        API_URL,
        headers={"Authorization": f"Bearer {WHATSAPP_TOKEN}"},
        params={"limit": 100},
        timeout=10,
    )
    response.raise_for_status()
    data = response.json()

    for template in data.get("data", []):
        if template["name"].startswith("hydration_"):
            print(f"{template['name']:35} {template['status']:15} {template.get('category', '')}")


if __name__ == "__main__":
    check_status()