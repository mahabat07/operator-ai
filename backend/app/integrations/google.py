from datetime import datetime, timezone
from typing import Any

import httpx

GMAIL_API = "https://gmail.googleapis.com/gmail/v1"
CALENDAR_API = "https://www.googleapis.com/calendar/v3"
DRIVE_API = "https://www.googleapis.com/drive/v3"


class GoogleWorkspaceClient:
    def __init__(self, access_token: str):
        self._headers = {"Authorization": f"Bearer {access_token}"}

    async def list_recent_messages(self, max_results: int = 20) -> list[dict[str, Any]]:

        async with httpx.AsyncClient(timeout=30, headers=self._headers) as client:
            list_resp = await client.get(f"{GMAIL_API}/users/me/messages", params={"maxResults": max_results, "q": "in:inbox"})
            if list_resp.status_code != 200:
                return []
            message_ids = [m["id"] for m in list_resp.json().get("messages", [])]

            messages = []
            for mid in message_ids:
                detail = await client.get(f"{GMAIL_API}/users/me/messages/{mid}", params={"format": "metadata", "metadataHeaders": ["From", "Subject", "Date"]})
                if detail.status_code != 200:
                    continue
                data = detail.json()
                headers = {h["name"]: h["value"] for h in data.get("payload", {}).get("headers", [])}
                messages.append({
                    "id": data["id"], "thread_id": data.get("threadId"),
                    "sender": headers.get("From", ""), "subject": headers.get("Subject", ""),
                    "snippet": data.get("snippet", ""), "received_at": headers.get("Date", ""),
                })
            return messages

    async def send_reply(self, thread_id: str, raw_rfc822_message_base64url: str) -> dict[str, Any]:
        async with httpx.AsyncClient(timeout=30, headers=self._headers) as client:
            resp = await client.post(
                f"{GMAIL_API}/users/me/messages/send",
                json={"raw": raw_rfc822_message_base64url, "threadId": thread_id},
            )
            resp.raise_for_status()
            return resp.json()

    async def list_upcoming_events(self, days_ahead: int = 7) -> list[dict[str, Any]]:
        now = datetime.now(timezone.utc)
        async with httpx.AsyncClient(timeout=30, headers=self._headers) as client:
            resp = await client.get(
                f"{CALENDAR_API}/calendars/primary/events",
                params={"timeMin": now.isoformat(), "singleEvents": "true", "orderBy": "startTime", "maxResults": 50},
            )
            if resp.status_code != 200:
                print(
                    f"Google Calendar API error: "
                    f"status={resp.status_code}, "
                    f"response={resp.text}"
                )
                return []
            events = []
            for item in resp.json().get("items", []):
                start = item.get("start", {}).get("dateTime") or item.get("start", {}).get("date")
                end = item.get("end", {}).get("dateTime") or item.get("end", {}).get("date")
                events.append({
                    "external_id": item["id"], "title": item.get("summary", "(no title)"),
                    "starts_at": start, "ends_at": end,
                    "attendees": [a.get("email") for a in item.get("attendees", [])],
                    "location": item.get("location"),
                })
            return events

    async def list_recent_drive_files(self, max_results: int = 20) -> list[dict[str, Any]]:
        async with httpx.AsyncClient(timeout=30, headers=self._headers) as client:
            resp = await client.get(
                f"{DRIVE_API}/files",
                params={"pageSize": max_results, "orderBy": "modifiedTime desc",
                        "fields": "files(id,name,mimeType,modifiedTime,webViewLink)"},
            )
            if resp.status_code != 200:
                return []
            return resp.json().get("files", [])
