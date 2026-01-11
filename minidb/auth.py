from __future__ import annotations

import hashlib
import uuid
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Dict, Optional

from .errors import AuthError


@dataclass
class Session:
    user_id: int
    username: str
    expiry: datetime


class Authenticator:
    def __init__(self, session_ttl_hours: int = 24):
        self._sessions: Dict[str, Session] = {}
        self._ttl = timedelta(hours=session_ttl_hours)

    @staticmethod
    def hash_password(password: str) -> str:
        return hashlib.sha256(password.encode("utf-8")).hexdigest()

    def create_session(self, user_id: int, username: str) -> str:
        token = str(uuid.uuid4())
        self._sessions[token] = Session(
            user_id=user_id,
            username=username,
            expiry=datetime.now(timezone.utc) + self._ttl,
        )
        return token

    def validate(self, token: Optional[str]) -> Session:
        if not token or token not in self._sessions:
            raise AuthError("Invalid session")
        s = self._sessions[token]
        if datetime.now(timezone.utc) >= s.expiry:
            del self._sessions[token]
            raise AuthError("Session expired")
        return s

    def logout(self, token: Optional[str]) -> None:
        if token and token in self._sessions:
            del self._sessions[token]
