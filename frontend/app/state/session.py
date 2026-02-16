import json
from pathlib import Path


class SessionStore:
    def __init__(self) -> None:
        self.token: str | None = None
        self.org_id: str | None = None
        self.user_id: str | None = None
        self.full_name: str | None = None
        self.patronymic: str | None = None
        self.role: str | None = None  # "admin" or "member"
        self.profile_complete: bool = False
        self.consent_accepted: bool = False
        self.theme: str = "dark"
        self.background_path: str | None = None
        self.avatar_path: str | None = None
        self.questionnaire_approved: bool = False
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

    def set_role(self, role: str) -> None:
        self.role = role
        self._save()

    def set_profile_complete(self, complete: bool) -> None:
        self.profile_complete = complete
        self._save()

    def set_consent_accepted(self, accepted: bool) -> None:
        self.consent_accepted = accepted
        self._save()

    def set_avatar_path(self, path: str | None) -> None:
        self.avatar_path = path
        self._save()

    def set_questionnaire_approved(self, approved: bool) -> None:
        self.questionnaire_approved = approved
        self._save()

    def clear(self) -> None:
        self.token = None
        self.org_id = None
        self.user_id = None
        self.full_name = None
        self.patronymic = None
        self.role = None
        self.profile_complete = False
        self.consent_accepted = False
        self.theme = "dark"
        self.background_path = None
        self.avatar_path = None
        self.questionnaire_approved = False
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
            self.role = payload.get("role")
            self.profile_complete = payload.get("profile_complete", False)
            self.consent_accepted = payload.get("consent_accepted", False)
            self.theme = payload.get("theme", "dark")
            self.background_path = payload.get("background_path")
            self.avatar_path = payload.get("avatar_path")
            self.questionnaire_approved = payload.get("questionnaire_approved", False)
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
            "role": self.role,
            "profile_complete": self.profile_complete,
            "consent_accepted": self.consent_accepted,
            "theme": self.theme,
            "background_path": self.background_path,
            "avatar_path": self.avatar_path,
            "questionnaire_approved": self.questionnaire_approved,
        }
        try:
            path.write_text(json.dumps(payload, ensure_ascii=True), encoding="utf-8")
        except OSError:
            return


session_store = SessionStore()
