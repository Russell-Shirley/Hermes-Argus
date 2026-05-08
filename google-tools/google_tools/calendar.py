from googleapiclient.discovery import build


class CalendarTools:
    def __init__(self, creds):
        self.service = build("calendar", "v3", credentials=creds)

    def list_events(self, time_min: str = None, time_max: str = None,
                    max_results: int = 10):
        params = {
            "calendarId": "primary",
            "maxResults": max_results,
            "singleEvents": True,
            "orderBy": "startTime",
        }
        if time_min:
            params["timeMin"] = time_min
        if time_max:
            params["timeMax"] = time_max

        events_result = self.service.events().list(**params).execute()
        events = events_result.get("items", [])
        output = []
        for event in events:
            attendees = []
            for a in event.get("attendees", []):
                attendees.append({
                    "email": a.get("email", ""),
                    "responseStatus": a.get("responseStatus", ""),
                })
            output.append({
                "id": event["id"],
                "summary": event.get("summary", ""),
                "start": event.get("start", {}),
                "end": event.get("end", {}),
                "attendees": attendees,
                "location": event.get("location", ""),
            })
        return output

    def create_event(self, summary: str, start: str, end: str,
                     location: str = "", description: str = ""):
        event_body = {
            "summary": summary,
            "start": {"dateTime": start, "timeZone": "America/Chicago"},
            "end": {"dateTime": end, "timeZone": "America/Chicago"},
        }
        if location:
            event_body["location"] = location
        if description:
            event_body["description"] = description

        event = (
            self.service.events()
            .insert(calendarId="primary", body=event_body)
            .execute()
        )
        return {"id": event["id"], "html_link": event.get("htmlLink", "")}

    def update_event(self, event_id: str, summary: str = None,
                     start: str = None, end: str = None):
        event = self.service.events().get(
            calendarId="primary", eventId=event_id
        ).execute()

        if summary is not None:
            event["summary"] = summary
        if start is not None:
            event["start"] = {"dateTime": start, "timeZone": "America/Chicago"}
        if end is not None:
            event["end"] = {"dateTime": end, "timeZone": "America/Chicago"}

        updated = (
            self.service.events()
            .update(calendarId="primary", eventId=event_id, body=event)
            .execute()
        )
        return {"id": updated["id"], "html_link": updated.get("htmlLink", "")}

    def delete_event(self, event_id: str):
        self.service.events().delete(
            calendarId="primary", eventId=event_id
        ).execute()
        return {"deleted": True}
