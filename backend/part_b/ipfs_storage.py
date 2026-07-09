"""Part B: Simulated IPFS (SHA-256 CID) with Pinata real IPFS upload."""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import requests

from backend.config import CERTIFICATES_DIR, PINATA_API_KEY, PINATA_JWT, PINATA_SECRET, USE_PINATA
from backend.security_events import SecurityEventLog


@dataclass
class DocumentRecord:
    filename: str
    cid: str
    content: dict[str, Any]
    pinata_ipfs_hash: str = ""
    pinata_url: str = ""


class IPFSStorage:
    """Local dictionary keyed by SHA-256 hex CID; Pinata for real IPFS pinning."""

    def __init__(self, security_log: SecurityEventLog) -> None:
        self.security_log = security_log
        self.store: dict[str, dict[str, Any]] = {}
        self.documents: list[DocumentRecord] = []
        CERTIFICATES_DIR.mkdir(parents=True, exist_ok=True)

    @staticmethod
    def compute_cid(content: dict[str, Any]) -> str:
        raw = json.dumps(content, sort_keys=True, separators=(",", ":")).encode("utf-8")
        return hashlib.sha256(raw).hexdigest()

    def store_document(self, filename: str, content: dict[str, Any]) -> DocumentRecord:
        cid = self.compute_cid(content)
        self.store[cid] = content
        path = CERTIFICATES_DIR / filename
        path.write_text(json.dumps(content, indent=2), encoding="utf-8")

        pinata_hash = ""
        pinata_url = ""
        if USE_PINATA:
            pinata_hash, pinata_url = self._upload_to_pinata(filename, content)

        record = DocumentRecord(
            filename=filename,
            cid=cid,
            content=content,
            pinata_ipfs_hash=pinata_hash,
            pinata_url=pinata_url,
        )
        self.documents.append(record)
        return record

    def _upload_to_pinata(self, filename: str, content: dict[str, Any]) -> tuple[str, str]:
        url = "https://api.pinata.cloud/pinning/pinJSONToIPFS"
        headers: dict[str, str] = {"Content-Type": "application/json"}
        if PINATA_JWT:
            headers["Authorization"] = f"Bearer {PINATA_JWT}"
        else:
            headers["pinata_api_key"] = PINATA_API_KEY
            headers["pinata_secret_api_key"] = PINATA_SECRET

        payload = {"pinataContent": content, "pinataMetadata": {"name": filename}}
        resp = requests.post(url, json=payload, headers=headers, timeout=60)
        resp.raise_for_status()
        data = resp.json()
        ipfs_hash = data.get("IpfsHash", "")
        gateway_url = f"https://gateway.pinata.cloud/ipfs/{ipfs_hash}" if ipfs_hash else ""
        return ipfs_hash, gateway_url

    def verify_document(self, cid: str) -> tuple[str, str]:
        if cid not in self.store:
            return "TAMPERED", f"CID {cid[:20]}... not found in store"
        stored = self.store[cid]
        recomputed = self.compute_cid(stored)
        if recomputed == cid:
            return "INTACT", "Document hash matches CID"
        self.security_log.record(
            "document_tamper",
            "0x0000000000000000000000000000000000000000",
            f"Document CID {cid} failed integrity check",
            doc_tamper_flag=1,
        )
        return "TAMPERED", f"Hash mismatch for CID {cid[:20]}..."

    def tamper_document(self, cid: str) -> str:
        if cid not in self.store:
            raise KeyError(f"CID not found: {cid}")
        doc = self.store[cid]
        key = next(iter(doc))
        original = doc[key]
        if isinstance(original, str) and original:
            doc[key] = original[:-1] + ("X" if original[-1] != "X" else "Y")
        else:
            doc["_tampered"] = True
        self.store[cid] = doc
        return f"Tampered one field in document at CID {cid[:20]}..."

    def get_document(self, cid: str) -> dict[str, Any] | None:
        return self.store.get(cid)
