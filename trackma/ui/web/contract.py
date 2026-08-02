"""Stable JSON contract shared by the desktop bridge and React client."""

from __future__ import annotations

import datetime
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Any, Union


JsonValue = Union[None, bool, int, float, str, list["JsonValue"], dict[str, "JsonValue"]]


@dataclass
class CommandError(Exception):
    code: str
    message: str
    details: Any = None

    def __post_init__(self) -> None:
        if not self.code or not self.message:
            raise ValueError("Command errors require a code and message")
        super().__init__(self.message)


def normalize_json(value: Any) -> JsonValue:
    """Convert Trackma values to data that can safely cross QWebChannel."""
    if value is None or isinstance(value, (bool, int, float, str)):
        return value
    if isinstance(value, (datetime.datetime, datetime.date, datetime.time)):
        return value.isoformat()
    if isinstance(value, (Enum, Path)):
        return normalize_json(value.value if isinstance(value, Enum) else str(value))
    if isinstance(value, dict):
        return {str(key): normalize_json(item) for key, item in value.items()}
    if isinstance(value, (list, tuple, set, frozenset)):
        return [normalize_json(item) for item in value]
    return str(value)


def public_account(account_id: int, account: dict[str, Any], service_name: str) -> dict[str, JsonValue]:
    """Return account metadata without credentials or OAuth state."""
    return {
        "id": account_id,
        "username": str(account.get("username", "")),
        "api": str(account.get("api", "")),
        "serviceName": service_name,
    }


def success_response(request_id: str, data: Any = None) -> dict[str, JsonValue]:
    return {"id": request_id, "ok": True, "data": normalize_json(data)}


def error_response(request_id: str, error: CommandError) -> dict[str, JsonValue]:
    payload: dict[str, JsonValue] = {
        "code": error.code,
        "message": error.message,
    }
    if error.details is not None:
        payload["details"] = normalize_json(error.details)
    return {"id": request_id, "ok": False, "error": payload}
