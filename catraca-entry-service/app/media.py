from __future__ import annotations

import requests


class MediaEntryClient:
    def __init__(self, url: str, api_key: str, unit_id: str):
        self.url = url
        self.api_key = api_key
        self.unit_id = unit_id
        self.session = requests.Session()

    def send(self, entry: dict) -> None:
        response = self.session.post(
            self.url,
            headers={"X-Api-Key": self.api_key},
            json={
                "studentId": entry["student_id"],
                "name": entry["student_name"],
                "enteredAt": entry["entered_at"],
                "unitId": self.unit_id,
            },
            timeout=10,
        )
        if not 200 <= response.status_code < 300:
            raise RuntimeError(f"Mídia Indoor recusou a entrada: HTTP {response.status_code}")
