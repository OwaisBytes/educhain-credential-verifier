"""Part C: SHA-256 chained transaction ledger."""

from __future__ import annotations

import hashlib
import json
import time
from dataclasses import dataclass, asdict
from typing import Any


@dataclass
class Transaction:
    tx_id: str
    action: str
    actor_wallet: str
    timestamp: float
    payload_hash: str
    prev_hash: str
    data: dict[str, Any]

    def compute_hash(self) -> str:
        payload = json.dumps(self.data, sort_keys=True, separators=(",", ":"))
        return hashlib.sha256(payload.encode("utf-8")).hexdigest()


class ChainedLedger:
    GENESIS = "0" * 64

    def __init__(self) -> None:
        self.transactions: list[Transaction] = []
        self._counter = 0

    def _next_id(self) -> str:
        self._counter += 1
        return f"TX-{self._counter:04d}"

    def append(self, action: str, actor_wallet: str, data: dict[str, Any]) -> Transaction:
        prev = self.transactions[-1].payload_hash if self.transactions else self.GENESIS
        tx = Transaction(
            tx_id=self._next_id(),
            action=action,
            actor_wallet=actor_wallet,
            timestamp=time.time(),
            payload_hash="",
            prev_hash=prev,
            data=data,
        )
        tx.payload_hash = tx.compute_hash()
        self.transactions.append(tx)
        return tx

    def verify_chain(self) -> list[tuple[str, str]]:
        results: list[tuple[str, str]] = []
        for i, tx in enumerate(self.transactions):
            recomputed = tx.compute_hash()
            hash_ok = recomputed == tx.payload_hash
            if i == 0:
                prev_ok = tx.prev_hash == self.GENESIS
            else:
                prev_ok = tx.prev_hash == self.transactions[i - 1].payload_hash
            status = "VALID" if hash_ok and prev_ok else "BROKEN"
            results.append((tx.tx_id, status))
        return results

    def tamper_transaction(self, index: int) -> Transaction:
        tx = self.transactions[index]
        if tx.data:
            key = next(iter(tx.data))
            val = tx.data[key]
            if isinstance(val, str):
                tx.data[key] = val + "X"
            else:
                tx.data["_tampered"] = True
        tx.payload_hash = tx.compute_hash()
        return tx

    def payload_hashes(self) -> list[str]:
        return [tx.payload_hash for tx in self.transactions]
