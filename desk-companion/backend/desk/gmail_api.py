"""Fixed Gmail API sender; OAuth belongs to the shared application connection."""

import base64
from email.message import EmailMessage
from email.policy import SMTP
import httpx


class MailTransportError(Exception):
    def __init__(self, code, *, unknown=False):
        super().__init__(code)
        self.code, self.unknown = code, unknown


class GmailAPI:
    def __init__(self, transport=None):
        self.transport = transport

    def send(self, email, access_token, draft, message_id):
        message = EmailMessage(policy=SMTP)
        message["From"], message["To"] = email, draft["to"]
        message["Subject"], message["Message-ID"] = draft["subject"], message_id
        message.set_content(draft["body"], charset="utf-8")
        raw = base64.urlsafe_b64encode(message.as_bytes()).decode().rstrip("=")
        try:
            with httpx.Client(
                timeout=10, transport=self.transport, trust_env=False, follow_redirects=False
            ) as client:
                response = client.post(
                    "https://gmail.googleapis.com/gmail/v1/users/me/messages/send",
                    headers={"Authorization": "Bearer " + access_token},
                    json={"raw": raw},
                )
            if response.status_code in {401, 403}:
                raise MailTransportError("GOOGLE_RECONNECT_REQUIRED")
            if 400 <= response.status_code < 500:
                raise MailTransportError("EMAIL_SEND_REJECTED")
            if response.status_code != 200 or len(response.content) > 65536:
                raise MailTransportError("EMAIL_SEND_UNKNOWN", unknown=True)
            result = response.json()
            if not isinstance(result.get("id"), str) or not 1 <= len(result["id"]) <= 200:
                raise ValueError()
            return {"accepted": True, "provider_id": result["id"]}
        except (httpx.ConnectError, httpx.ConnectTimeout, httpx.PoolTimeout):
            raise MailTransportError("EMAIL_CONNECTION_FAILED") from None
        except (httpx.HTTPError, ValueError):
            raise MailTransportError("EMAIL_SEND_UNKNOWN", unknown=True) from None
