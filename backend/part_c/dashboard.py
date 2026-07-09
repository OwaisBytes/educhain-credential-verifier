"""Part C: Dashboard state aggregator for terminal UI and Flask API."""

from __future__ import annotations

from dataclasses import dataclass, asdict
from typing import Any


@dataclass
class DashboardState:
    identities: list[dict[str, Any]]
    credentials: list[dict[str, Any]]
    threat_feed: list[dict[str, Any]]
    transaction_chain: list[dict[str, Any]]
    merkle_root: str
    tampered_merkle_root: str
    tamper_flag: bool
    chain_verification: list[dict[str, str]]
    merkle_proof_valid: bool
    active_session_token: str
    role_permissions: dict[str, list[str]]
    contract_info: dict[str, Any]
    verify_results: list[dict[str, Any]]

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


class DashboardManager:
    def __init__(self) -> None:
        self.state: DashboardState | None = None

    def update(self, **kwargs: Any) -> None:
        if self.state is None:
            self.state = DashboardState(
                identities=[], credentials=[], threat_feed=[],
                transaction_chain=[], merkle_root="", tampered_merkle_root="",
                tamper_flag=False, chain_verification=[], merkle_proof_valid=False,
                active_session_token="", role_permissions={}, contract_info={},
                verify_results=[],
            )
        for k, v in kwargs.items():
            if hasattr(self.state, k):
                setattr(self.state, k, v)

    def get_state(self) -> dict[str, Any]:
        if self.state is None:
            return {}
        return self.state.to_dict()

    def add_verify_result(self, credential_id: int, result: str, details: str) -> None:
        if self.state:
            self.state.verify_results.append({
                "credential_id": credential_id,
                "result": result,
                "details": details,
            })
