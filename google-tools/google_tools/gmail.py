import base64
from email.mime.text import MIMEText

from googleapiclient.discovery import build


class GmailTools:
    def __init__(self, creds):
        self.service = build("gmail", "v1", credentials=creds)

    def list_messages(self, max_results: int = 10):
        results = (
            self.service.users()
            .messages()
            .list(userId="me", maxResults=max_results)
            .execute()
        )
        messages = results.get("messages", [])
        if not messages:
            return []
        return self._batch_get_metadata(messages)

    def search(self, query: str, max_results: int = 10):
        results = (
            self.service.users()
            .messages()
            .list(userId="me", q=query, maxResults=max_results)
            .execute()
        )
        messages = results.get("messages", [])
        if not messages:
            return []
        return self._batch_get_metadata(messages)

    def read_message(self, message_id: str):
        msg = (
            self.service.users()
            .messages()
            .get(userId="me", id=message_id, format="full")
            .execute()
        )
        headers = msg["payload"]["headers"]
        subject = next((h["value"] for h in headers if h["name"] == "Subject"), "")
        from_ = next((h["value"] for h in headers if h["name"] == "From"), "")
        to = next((h["value"] for h in headers if h["name"] == "To"), "")
        date = next((h["value"] for h in headers if h["name"] == "Date"), "")
        body = self._get_body(msg["payload"])

        return {
            "id": msg["id"],
            "subject": subject,
            "from": from_,
            "to": to,
            "date": date,
            "body_text": body,
        }

    def send(self, to: str, subject: str, body: str):
        message = MIMEText(body)
        message["to"] = to
        message["subject"] = subject
        raw = base64.urlsafe_b64encode(message.as_bytes()).decode()
        sent = (
            self.service.users()
            .messages()
            .send(userId="me", body={"raw": raw})
            .execute()
        )
        return {"message_id": sent["id"], "thread_id": sent["threadId"]}

    def _batch_get_metadata(self, messages):
        output = []
        for msg in messages:
            details = (
                self.service.users()
                .messages()
                .get(
                    userId="me",
                    id=msg["id"],
                    format="metadata",
                    metadataHeaders=["Subject", "From", "Date"],
                )
                .execute()
            )
            headers = details["payload"]["headers"]
            subject = next(
                (h["value"] for h in headers if h["name"] == "Subject"), ""
            )
            from_ = next((h["value"] for h in headers if h["name"] == "From"), "")
            date = next((h["value"] for h in headers if h["name"] == "Date"), "")
            output.append(
                {
                    "id": msg["id"],
                    "threadId": msg["threadId"],
                    "subject": subject,
                    "from": from_,
                    "date": date,
                    "snippet": details.get("snippet", ""),
                }
            )
        return output

    def _get_body(self, payload):
        if "parts" in payload:
            for part in payload["parts"]:
                if part["mimeType"] == "text/plain":
                    data = part["body"].get("data", "")
                    if data:
                        return base64.urlsafe_b64decode(data).decode(
                            "utf-8", errors="replace"
                        )
        data = payload.get("body", {}).get("data", "")
        if data:
            return base64.urlsafe_b64decode(data).decode("utf-8", errors="replace")
        return ""
