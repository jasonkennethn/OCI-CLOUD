"""
Email Service – Send notifications via Brevo (Sendinblue) API.
"""

import os
import logging
import requests
from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger('cloud_activation')

BREVO_API_URL = 'https://api.brevo.com/v3/smtp/email'


def send_success_email() -> bool:
    """
    Send a success notification email via Brevo API.
    Returns True if the email was sent successfully.
    """
    api_key = os.getenv('BREVO_API_KEY')
    sender_email = os.getenv('EMAIL_SENDER')
    recipient_email = os.getenv('EMAIL_RECIPIENT')

    if not all([api_key, sender_email, recipient_email]):
        logger.error("Email config incomplete – check BREVO_API_KEY, EMAIL_SENDER, EMAIL_RECIPIENT in .env")
        return False

    payload = {
        'sender': {
            'name': 'Celarox Cloud',
            'email': sender_email,
        },
        'to': [
            {
                'email': recipient_email,
                'name': 'Jason Kenneth',
            }
        ],
        'subject': '✅ OCI Cloud Activation – Success',
        'htmlContent': '''
        <div style="font-family: 'Inter', -apple-system, sans-serif; max-width: 520px; margin: 40px auto; padding: 40px; background: linear-gradient(135deg, #0f0f23 0%, #1a1a3e 100%); border-radius: 16px; color: #e0e0ff;">
            <div style="text-align: center; margin-bottom: 24px;">
                <div style="display: inline-block; width: 56px; height: 56px; background: linear-gradient(135deg, #22c55e, #16a34a); border-radius: 50%; line-height: 56px; font-size: 28px;">✓</div>
            </div>
            <h1 style="text-align: center; font-size: 22px; font-weight: 600; margin: 0 0 8px; color: #ffffff;">Cloud has been allotted Successfully</h1>
            <p style="text-align: center; font-size: 14px; color: #a0a0cc; margin: 0 0 32px;">Your OCI A1 Flex instance is now provisioned and running.</p>
            <div style="background: rgba(255,255,255,0.05); border: 1px solid rgba(255,255,255,0.08); border-radius: 10px; padding: 20px; margin-bottom: 24px;">
                <table style="width: 100%; border-collapse: collapse; font-size: 13px;">
                    <tr><td style="padding: 6px 0; color: #8888bb;">Stack</td><td style="padding: 6px 0; text-align: right; color: #ffffff;">celarox-a1-personal-cloud</td></tr>
                    <tr><td style="padding: 6px 0; color: #8888bb;">Shape</td><td style="padding: 6px 0; text-align: right; color: #ffffff;">VM.Standard.A1.Flex</td></tr>
                    <tr><td style="padding: 6px 0; color: #8888bb;">OCPUs / RAM</td><td style="padding: 6px 0; text-align: right; color: #ffffff;">2 / 12 GB</td></tr>
                    <tr><td style="padding: 6px 0; color: #8888bb;">Region</td><td style="padding: 6px 0; text-align: right; color: #ffffff;">ap-mumbai-1</td></tr>
                </table>
            </div>
            <p style="text-align: center; font-size: 12px; color: #666688; margin: 0;">The scheduler has been stopped. No further attempts will be made.</p>
        </div>
        ''',
    }

    headers = {
        'accept': 'application/json',
        'api-key': api_key,
        'content-type': 'application/json',
    }

    try:
        response = requests.post(BREVO_API_URL, json=payload, headers=headers, timeout=30)
        if response.status_code in (200, 201):
            logger.info(f"✅ Email sent successfully to {recipient_email}")
            return True
        else:
            logger.error(f"Email API error: {response.status_code} – {response.text}")
            return False
    except Exception as e:
        logger.error(f"Email sending failed: {e}")
        return False
