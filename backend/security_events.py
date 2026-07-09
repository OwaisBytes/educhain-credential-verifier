"""Shared security event collector feeding Part B AI threat detection."""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Any


@dataclass
class SecurityEvent:
    event_type: str
    actor_wallet: str
    details: str
    timestamp: float = field(default_factory=time.time)
    failed_logins: int = 0
    verification_attempts: int = 0
    doc_tamper_flag: int = 0
    time_gap_sec: float = 0.0
    wallet_age_blocks: int = 100


class SecurityEventLog:
    """Central log for failed logins, expired sessions, reverts, tampering."""

    def __init__(self) -> None:
        self.events: list[SecurityEvent] = []
        self._failed_login_counts: dict[str, int] = {}

    def record(
        self,
        event_type: str,
        actor_wallet: str,
        details: str,
        *,
        failed_logins: int | None = None,
        verification_attempts: int = 0,
        doc_tamper_flag: int = 0,
        time_gap_sec: float = 0.0,
        wallet_age_blocks: int = 100,
    ) -> SecurityEvent:
        if event_type in ("failed_login", "wrong_key_login"):
            self._failed_login_counts[actor_wallet] = (
                self._failed_login_counts.get(actor_wallet, 0) + 1
            )
            fl = failed_logins if failed_logins is not None else self._failed_login_counts[actor_wallet]
        else:
            fl = failed_logins or 0

        evt = SecurityEvent(
            event_type=event_type,
            actor_wallet=actor_wallet,
            details=details,
            failed_logins=fl,
            verification_attempts=verification_attempts,
            doc_tamper_flag=doc_tamper_flag,
            time_gap_sec=time_gap_sec,
            wallet_age_blocks=wallet_age_blocks,
        )
        self.events.append(evt)
        return evt

    def to_feature_rows(self) -> list[dict[str, Any]]:
        return [
            {
                "event_type": e.event_type,
                "actor_wallet": e.actor_wallet,
                "failed_logins": e.failed_logins,
                "verification_attempts": e.verification_attempts,
                "doc_tamper_flag": e.doc_tamper_flag,
                "time_gap_sec": e.time_gap_sec,
                "wallet_age_blocks": e.wallet_age_blocks,
            }
            for e in self.events
        ]
