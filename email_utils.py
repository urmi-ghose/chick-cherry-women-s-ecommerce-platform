import requests
import json
import os
from django.conf import settings


def send_email_via_nodemailer(to_email, subject, html_content, text_content=None):
    """
    Send email using the Node.js nodemailer service
    """
    try:
        email_service_url = getattr(
            settings, "EMAIL_SERVICE_URL", "http://localhost:3001/send-email"
        )

        payload = {
            "to": to_email,
            "subject": subject,
            "html": html_content,
        }

        if text_content:
            payload["text"] = text_content

        response = requests.post(
            email_service_url,
            json=payload,
            timeout=10,  # 10 second timeout
        )

        if response.status_code == 200:
            result = response.json()
            if result.get("success"):
                print(f"Email sent successfully to {to_email}")
                return True
            else:
                print(f"Email service returned error: {result.get('message')}")
                return False
        else:
            print(f"Email service HTTP error: {response.status_code}")
            return False

    except requests.exceptions.RequestException as e:
        print(f"Failed to connect to email service: {e}")
        return False
    except Exception as e:
        print(f"Unexpected error sending email: {e}")
        return False
