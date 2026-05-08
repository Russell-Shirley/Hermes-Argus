from googleapiclient.discovery import build


class TasksTools:
    def __init__(self, creds):
        self.service = build("tasks", "v1", credentials=creds)

    def list_lists(self):
        results = self.service.tasklists().list().execute()
        lists = results.get("items", [])
        return [{"id": lst["id"], "title": lst["title"]} for lst in lists]

    def list_tasks(self, list_id: str, show_completed: bool = False):
        params = {"tasklist": list_id}
        if not show_completed:
            params["showCompleted"] = False
        results = self.service.tasks().list(**params).execute()
        tasks = results.get("items", [])
        output = []
        for task in tasks:
            output.append({
                "id": task["id"],
                "title": task.get("title", ""),
                "notes": task.get("notes", ""),
                "due": task.get("due", ""),
                "status": task.get("status", "needsAction"),
            })
        return output

    def create_task(self, list_id: str, title: str, notes: str = "",
                    due: str = ""):
        task_body = {"title": title}
        if notes:
            task_body["notes"] = notes
        if due:
            task_body["due"] = due

        task = self.service.tasks().insert(
            tasklist=list_id, body=task_body
        ).execute()
        return {"id": task["id"], "title": task.get("title", "")}

    def update_task(self, list_id: str, task_id: str, status: str = None):
        task = self.service.tasks().get(
            tasklist=list_id, task=task_id
        ).execute()

        if status is not None:
            task["status"] = status

        updated = self.service.tasks().update(
            tasklist=list_id, task=task_id, body=task
        ).execute()
        return {
            "id": updated["id"],
            "title": updated.get("title", ""),
            "status": updated.get("status", ""),
        }
