from __future__ import annotations

import logging
import threading
import sys
from dataclasses import dataclass, field
from typing import Optional
from enum import Enum

logger = logging.getLogger(__name__)


class UserCommand(str, Enum):
    PAUSE = "pause"
    RESUME = "resume"
    FOCUS = "focus"
    SKIP = "skip"
    STOP = "stop"
    STATUS = "status"


@dataclass
class UserInput:
    command: UserCommand
    argument: str = ""


@dataclass
class AsyncInputHandler:
    _input_queue: list[str] = field(default_factory=list)
    _lock: threading.Lock = field(default_factory=threading.Lock)
    _thread: Optional[threading.Thread] = None
    _running: bool = False
    _prompt_text: str = "aidbqc> "

    def start(self) -> None:
        if self._running:
            return
        self._running = True
        self._thread = threading.Thread(target=self._input_loop, daemon=True)
        self._thread.start()
        logger.info("AsyncInputHandler started")

    def stop(self) -> None:
        self._running = False
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=2.0)
        logger.info("AsyncInputHandler stopped")

    def _input_loop(self) -> None:
        while self._running:
            try:
                line = input(self._prompt_text)
                with self._lock:
                    self._input_queue.append(line.strip())
            except EOFError:
                self._running = False
                break
            except Exception as e:
                logger.debug(f"Input loop error: {e}")
                break

    def get_input(self) -> Optional[UserInput]:
        with self._lock:
            if not self._input_queue:
                return None
            raw = self._input_queue.pop(0)
        return self._parse_input(raw)

    def get_all_pending(self) -> list[UserInput]:
        with self._lock:
            raw_items = list(self._input_queue)
            self._input_queue.clear()
        return [self._parse_input(r) for r in raw_items if r.strip()]

    def _parse_input(self, raw: str) -> UserInput:
        if not raw:
            return UserInput(command=UserCommand.STATUS, argument="")

        parts = raw.split(maxsplit=1)
        cmd_str = parts[0].lower()
        arg = parts[1] if len(parts) > 1 else ""

        try:
            command = UserCommand(cmd_str)
        except ValueError:
            return UserInput(command=UserCommand.FOCUS, argument=raw)

        return UserInput(command=command, argument=arg)

    @property
    def is_running(self) -> bool:
        return self._running

    def inject_input(self, text: str) -> None:
        with self._lock:
            self._input_queue.append(text.strip())
