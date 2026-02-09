import json
from pathlib import Path


class SessionStore:
    def __init__(self) -> None:
        self.token: str | None = None
        self.org_id: str | None = None
        self.user_id: str | None = None
        self.full_name: str | None = None
        self.patronymic: str | None = None
        self.theme: str = "dark"
        self.background_path: str | None = None
        self._load()

    def set_token(self, token: str | None) -> None:
        self.token = token
        self._save()

    def set_org_id(self, org_id: str | None) -> None:
        self.org_id = org_id
        self._save()

    def set_user_profile(self, user_id: str | None, full_name: str | None, patronymic: str | None) -> None:
        self.user_id = user_id
        self.full_name = full_name
        self.patronymic = patronymic
        self._save()

    def clear(self) -> None:
        self.token = None
        self.org_id = None
        self.user_id = None
        self.full_name = None
        self.patronymic = None
        self.theme = "dark"
        self.background_path = None
        self._save()

    def _session_path(self) -> Path:
        return Path(__file__).resolve().parents[2] / ".session.json"

    def _load(self) -> None:
        path = self._session_path()
        if not path.exists():
            return
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
            self.token = payload.get("token")
            self.org_id = payload.get("org_id")
            self.user_id = payload.get("user_id")
            self.full_name = payload.get("full_name")
            self.patronymic = payload.get("patronymic")
            self.theme = payload.get("theme", "light")
            self.background_path = payload.get("background_path")
        except (OSError, json.JSONDecodeError):
            return

    def _save(self) -> None:
        path = self._session_path()
        payload = {
            "token": self.token,
            "org_id": self.org_id,
            "user_id": self.user_id,
            "full_name": self.full_name,
            "patronymic": self.patronymic,
            "theme": self.theme,
            "background_path": self.background_path,
        }
        try:
            path.write_text(json.dumps(payload, ensure_ascii=True), encoding="utf-8")
        except OSError:
            return


session_store = SessionStore()
