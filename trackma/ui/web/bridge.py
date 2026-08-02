"""Qt WebChannel adapter for the typed Trackma command contract."""

from __future__ import annotations

import json
from concurrent.futures import Future, ThreadPoolExecutor
from typing import Any, Callable

from PyQt6 import QtCore

from .contract import CommandError, error_response, success_response
from .controller import BackendController


NativeHandler = Callable[[str, dict[str, Any]], Any]


class WebBridge(QtCore.QObject):
    response = QtCore.pyqtSignal(str)
    event: Any = QtCore.pyqtSignal(str)

    def __init__(
        self,
        controller: BackendController,
        native_handler: NativeHandler | None = None,
        parent: QtCore.QObject | None = None,
    ) -> None:
        super().__init__(parent)
        self.controller = controller
        self.native_handler = native_handler
        self._executor = ThreadPoolExecutor(max_workers=1, thread_name_prefix="trackma-engine")
        self._closed = False
        self.controller.event_callback = self.emit_event

    @QtCore.pyqtSlot(str, str, str)
    def request(self, request_id: str, command: str, payload_json: str) -> None:
        if self._closed:
            self._emit_response(
                error_response(request_id, CommandError("BRIDGE_CLOSED", "Application is closing"))
            )
            return
        try:
            payload = json.loads(payload_json or "{}")
            if not isinstance(payload, dict):
                raise ValueError
        except (json.JSONDecodeError, ValueError):
            self._emit_response(
                error_response(
                    request_id,
                    CommandError("INVALID_PAYLOAD", "Command payload must be a JSON object"),
                )
            )
            return

        if command.startswith("native."):
            self._handle_native(request_id, command, payload)
            return

        future = self._executor.submit(self.controller.handle, command, payload)
        future.add_done_callback(lambda result: self._complete(request_id, result))

    def _handle_native(self, request_id: str, command: str, payload: dict[str, Any]) -> None:
        if self.native_handler is None:
            self._emit_response(
                error_response(request_id, CommandError("INVALID_COMMAND", "Native command unavailable"))
            )
            return
        try:
            self._emit_response(success_response(request_id, self.native_handler(command, payload)))
        except CommandError as error:
            self._emit_response(error_response(request_id, error))
        except Exception:
            self._emit_response(
                error_response(request_id, CommandError("NATIVE_ERROR", "Native operation failed"))
            )

    def _complete(self, request_id: str, future: Future[Any]) -> None:
        try:
            payload = success_response(request_id, future.result())
        except CommandError as error:
            payload = error_response(request_id, error)
        except Exception:
            payload = error_response(
                request_id,
                CommandError("INTERNAL_ERROR", "Unexpected backend error"),
            )
        self._emit_response(payload)

    def _emit_response(self, payload: dict[str, Any]) -> None:
        self.response.emit(json.dumps(payload, separators=(",", ":")))

    def emit_event(self, name: str, payload: Any) -> None:
        self.event.emit(
            json.dumps({"name": name, "payload": payload}, separators=(",", ":"), default=str)
        )

    def close(self) -> None:
        if self._closed:
            return
        self._closed = True
        future = self._executor.submit(self.controller.handle, "app.shutdown", {})
        try:
            future.result(timeout=20)
        finally:
            self._executor.shutdown(wait=True, cancel_futures=True)
