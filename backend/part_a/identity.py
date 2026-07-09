"""Part A: Deterministic ECDSA wallet identities for three roles."""

from __future__ import annotations

import hashlib
import time
from dataclasses import dataclass

from ecdsa import SECP256k1, SigningKey

from backend.config import ROLE_SEEDS, SESSION_TTL_SECONDS


@dataclass
class Identity:
    role: str
    wallet_address: str
    public_key: str
    private_key: str
    session_token: str
    token_expiry: float

    def public_key_truncated(self, length: int = 20) -> str:
        return self.public_key[:length]

    def wallet_truncated(self, length: int = 20) -> str:
        return self.wallet_address[:length]


def _derive_signing_key(seed_string: str) -> SigningKey:
    """Deterministically derive SECP256k1 key from fixed seed string."""
    digest = hashlib.sha256(seed_string.encode("utf-8")).digest()
    return SigningKey.from_string(digest, curve=SECP256k1)


def _pubkey_to_wallet(public_key_bytes: bytes) -> str:
    """Wallet address = first 20 bytes of SHA-256(public key), as 0x-prefixed hex."""
    pubkey_hash = hashlib.sha256(public_key_bytes).digest()
    return "0x" + pubkey_hash[:20].hex()


def create_identity(role: str, timestamp: float | None = None) -> Identity:
    seed = ROLE_SEEDS[role]
    sk = _derive_signing_key(seed)
    vk = sk.get_verifying_key()
    pub_bytes = vk.to_string()
    pub_hex = pub_bytes.hex()

    wallet = _pubkey_to_wallet(pub_bytes)
    ts = timestamp if timestamp is not None else time.time()
    token_raw = f"{role}:{ts}"
    session_token = hashlib.sha256(token_raw.encode("utf-8")).hexdigest()
    expiry = ts + SESSION_TTL_SECONDS

    return Identity(
        role=role,
        wallet_address=wallet,
        public_key=pub_hex,
        private_key=sk.to_string().hex(),
        session_token=session_token,
        token_expiry=expiry,
    )


def generate_all_identities() -> dict[str, Identity]:
    ts = time.time()
    return {role: create_identity(role, ts) for role in ROLE_SEEDS}


ROLE_PERMISSIONS = {
    "Registrar": ["issue_credential", "revoke_credential", "view_credentials"],
    "Student": ["view_own_credential", "transfer_ownership"],
    "Employer": ["verify_credential", "view_public_credentials"],
}
