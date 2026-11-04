"""Tier 3: Jira and Google Calendar, called directly by the record service (not as Switch agent tools).

Neither is the medical record and neither approves anything. Use a test Jira project and a test calendar.
Each action runs once per case (the `external` table) and a failure never blocks the loop.
"""
import base64
import json
import os
import urllib.request
from datetime import datetime, timedelta, timezone


def http_json(method, url, body=None, headers=None):
    req = urllib.request.Request(url, method=method, data=json.dumps(body).encode() if body is not None else None,
                                 headers={"Content-Type": "application/json", **(headers or {})})
    with urllib.request.urlopen(req, timeout=20) as r:
        raw = r.read()
    return json.loads(raw) if raw else {}


def _once(db, case_id, kind):
    return db.execute("SELECT ref FROM external WHERE case_id=? AND kind=?", (case_id, kind)).fetchone()


def _remember(db, case_id, kind, ref):
    db.execute("INSERT OR REPLACE INTO external VALUES(?,?,?)", (case_id, kind, ref))
    db.commit()


class Jira:
    """One task per case: created on RESOLVED, reassigned to the incoming nurse on ACCEPT."""

    def __init__(self, url, email, token, project, accounts=None, http=http_json):
        self.url, self.project, self.accounts, self.http = url.rstrip("/"), project, accounts or {}, http
        self.headers = {"Authorization": "Basic " + base64.b64encode(f"{email}:{token}".encode()).decode()}

    def on_resolved(self, case, owner, db):
        if _once(db, case["id"], "jira"):
            return None
        res = self.http("POST", f"{self.url}/rest/api/3/issue", {"fields": {
            "project": {"key": self.project}, "issuetype": {"name": "Task"},
            "summary": f"Case {case['id']}: confirm the patient received the doctor's explanation",
            "description": {"type": "doc", "version": 1, "content": [{"type": "paragraph", "content": [
                {"type": "text", "text": f"Fictional demo data. Case {case['id']}, owner {owner}."}]}]}}}, self.headers)
        _remember(db, case["id"], "jira", res["key"])
        self._assign(res["key"], owner)
        return f"Jira task {res['key']} created for Case {case['id']}, owner {owner}"

    def on_accept(self, case, owner, db):
        ref = _once(db, case["id"], "jira")
        if not ref:
            return None
        self._assign(ref["ref"], owner)
        return f"Jira task {ref['ref']} owner changed to {owner}"

    def _assign(self, key, owner):
        account = self.accounts.get(owner)
        if account:
            self.http("PUT", f"{self.url}/rest/api/3/issue/{key}/assignee", {"accountId": account}, self.headers)


class GoogleCalendar:
    """One follow-up event on the care-team test calendar, created on RESOLVED."""

    def __init__(self, access_token, calendar_id="primary", delay_hours=2, http=http_json):
        self.calendar_id, self.delay, self.http = calendar_id, delay_hours, http
        self.headers = {"Authorization": f"Bearer {access_token}"}

    def on_resolved(self, case, owner, db):
        if _once(db, case["id"], "calendar"):
            return None
        start = datetime.now(timezone.utc) + timedelta(hours=self.delay)
        res = self.http("POST", f"https://www.googleapis.com/calendar/v3/calendars/{self.calendar_id}/events", {
            "summary": f"Case {case['id']}: check patient ate without nausea",
            "description": f"Fictional demo data. Owner: {owner}. Case {case['id']}.",
            "start": {"dateTime": start.isoformat()},
            "end": {"dateTime": (start + timedelta(minutes=15)).isoformat()}}, self.headers)
        _remember(db, case["id"], "calendar", res.get("id", ""))
        return f"Calendar event created for Case {case['id']} (owner {owner})"

    def on_accept(self, case, owner, db):
        return None


def from_env(accounts=None):
    """Enable whichever integrations have credentials in the environment."""
    out = []
    if os.environ.get("JIRA_URL"):
        out.append(Jira(os.environ["JIRA_URL"], os.environ["JIRA_EMAIL"], os.environ["JIRA_TOKEN"],
                        os.environ["JIRA_PROJECT"], accounts))
    if os.environ.get("GCAL_TOKEN"):
        out.append(GoogleCalendar(os.environ["GCAL_TOKEN"], os.environ.get("GCAL_CALENDAR_ID", "primary")))
    return out
