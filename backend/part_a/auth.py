"""Part A: Wallet login, session tokens, and verify_session gate."""

from __future__ import annotations

import hashlib
import time
from dataclasses import dataclass
from typing import TYPE_CHECKING

from ecdsa import SECP256k1, SigningKey

from backend.security_events import SecurityEventLog

if TYPE_CHECKING:
    from backend.part_a.identity import Identity


@dataclass
class LoginResult:
    success: bool
    status: str  # VERIFIED | FAILED | EXPIRED
    message: str
    session_token: str | None = None
    role: str | None = None
    token_expiry: float | None = None


@dataclass
class ActiveSession:
    role: str
    wallet_address: str
    session_token: str
    token_expiry: float
    signature: str


class AuthManager:
    def __init__(self, security_log: SecurityEventLog) -> None:
        self.security_log = security_log
        self.sessions: dict[str, ActiveSession] = {}
        self._identities_by_wallet: dict[str, Identity] = {}

    def register_identities(self, identities: dict[str, Identity]) -> None:
        for ident in identities.values():
            self._identities_by_wallet[ident.wallet_address.lower()] = ident

    def _sign_token(self, private_key_hex: str, token: str) -> str:
        sk = SigningKey.from_string(bytes.fromhex(private_key_hex), curve=SECP256k1)
        sig = sk.sign_deterministic(token.encode("utf-8"), hashfunc=hashlib.sha256)
        return sig.hex()

    def login(self, wallet_address: str, private_key: str) -> LoginResult:
        wallet = wallet_address.lower()
        ident = self._identities_by_wallet.get(wallet)

        if ident is None:
            self.security_log.record(
                "failed_login",
                wallet_address,
                "Unknown wallet address",
                failed_logins=1,
            )
            return LoginResult(False, "FAILED", "Wallet address not registered")

        if private_key != ident.private_key:
            self.security_log.record(
                "wrong_key_login",
                wallet_address,
                "Invalid private key presented",
                failed_logins=1,
            )
            return LoginResult(False, "FAILED", "Invalid private key")

        ts = time.time()
        token_raw = f"{ident.role}:{ts}"
        session_token = hashlib.sha256(token_raw.encode("utf-8")).hexdigest()
        expiry = ts + 3600
        signature = self._sign_token(ident.private_key, session_token)

        session = ActiveSession(
            role=ident.role,
            wallet_address=ident.wallet_address,
            session_token=session_token,
            token_expiry=expiry,
            signature=signature,
        )
        self.sessions[session_token] = session

        return LoginResult(
            True,
            "VERIFIED",
            f"Session established for {ident.role}",
            session_token=session_token,
            role=ident.role,
            token_expiry=expiry,
        )

    def verify_session(self, token: str) -> tuple[bool, str, ActiveSession | None]:
        session = self.sessions.get(token)
        if session is None:
            self.security_log.record(
                "invalid_session",
                "0x0000000000000000000000000000000000000000",
                "Session token not found",
            )
            return False, "Invalid session token", None

        if time.time() > session.token_expiry:
            self.security_log.record(
                "expired_session",
                session.wallet_address,
                "Session token expired",
                time_gap_sec=time.time() - session.token_expiry,
            )
            del self.sessions[token]
            return False, "Session token expired", None

        return True, "Session valid", session

    def create_expired_token_demo(self, identities: dict[str, Identity]) -> str:
        """Create an already-expired token for demonstration."""
        ident = identities["Employer"]
        past_ts = time.time() - 7200
        token_raw = f"{ident.role}:{past_ts}"
        expired_token = hashlib.sha256(token_raw.encode("utf-8")).hexdigest()
        self.sessions[expired_token] = ActiveSession(
            role=ident.role,
            wallet_address=ident.wallet_address,
            session_token=expired_token,
            token_expiry=past_ts + 3600,
            signature="expired_demo",
        )
        return expired_token

    def reject_expired_token(self, token: str) -> LoginResult:
        ok, msg, _ = self.verify_session(token)
        return LoginResult(False, "EXPIRED" if "expired" in msg.lower() else "FAILED", msg)

    def require_session(self, token: str, allowed_roles: list[str] | None = None) -> ActiveSession:
        ok, msg, session = self.verify_session(token)
        if not ok or session is None:
            raise PermissionError(msg)
        if allowed_roles and session.role not in allowed_roles:
            self.security_log.record(
                "unauthorized_role",
                session.wallet_address,
                f"Role {session.role} not in {allowed_roles}",
            )
            raise PermissionError(f"Role {session.role} not authorized")
        return session

    @staticmethod
    def verify_signature(public_key_hex: str, token: str, signature_hex: str) -> bool:
        from ecdsa import VerifyingKey

        vk = VerifyingKey.from_string(bytes.fromhex(public_key_hex), curve=SECP256k1)
        try:
            return vk.verify(
                bytes.fromhex(signature_hex),
                token.encode("utf-8"),
                hashfunc=hashlib.sha256,
            )
        except Exception:
            return False
