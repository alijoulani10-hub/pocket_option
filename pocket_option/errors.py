from __future__ import annotations

import typing

__all__ = ("DealError", "DealErrorCode", "PocketOptionError")


class PocketOptionError(Exception):
    def __init__(self, code: str, message: str, extras: dict | None = None) -> None:
        super().__init__(message)
        self.code = code
        self.message = message
        self.extras = extras

    def __str__(self) -> str:
        if self.extras is not None:
            return f"[{self.code}] {self.message} {self.extras!r}"
        return f"[{self.code}] {self.message}"


type DealErrorCode = typing.Literal[
    "min_amount",
    "max_amount",
    "min_duration",
    "max_duration",
    "max_orders",
    "timeout",
    "not_found",
]


class DealError(PocketOptionError):
    code: DealErrorCode

    def __init__(self, code: DealErrorCode, message: str, extras: dict | None = None) -> None:
        super().__init__(code, message, extras)
