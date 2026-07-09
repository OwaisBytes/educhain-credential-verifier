"""
Blockchain-Based Academic Credential Verification DApp
Main orchestrator — runs Parts A, B, C end-to-end.
"""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from tabulate import tabulate

from backend.display import render_dashboard
from backend.part_a.auth import AuthManager
from backend.part_a.contract import CredentialRegistryClient
from backend.part_a.identity import ROLE_PERMISSIONS, generate_all_identities
from backend.part_b.ipfs_storage import IPFSStorage
from backend.part_b.threat_detection import ThreatDetector
from backend.part_c.dashboard import DashboardManager
from backend.part_c.ledger import ChainedLedger
from backend.part_c.merkle import MerkleTree
from backend.security_events import SecurityEventLog


def print_section(title: str) -> None:
    print("\n" + "=" * 70)
    print(f"  {title}")
    print("=" * 70)


def run() -> DashboardManager:
    security_log = SecurityEventLog()
    auth = AuthManager(security_log)
    registry = CredentialRegistryClient(security_log)
    ipfs = IPFSStorage(security_log)
    ledger = ChainedLedger()
    threat = ThreatDetector(security_log)
    dashboard = DashboardManager()

    # ── PART A: Identity & Login ──────────────────────────────────────────
    print_section("PART A — Wallet Identity & Smart Contract Registry")

    identities = generate_all_identities()
    auth.register_identities(identities)

    identity_rows = [
        [ident.role, ident.wallet_truncated(), ident.public_key_truncated()]
        for ident in identities.values()
    ]
    print("\nIdentity Table:")
    print(tabulate(identity_rows, headers=["Role", "Wallet (20)", "Public Key (20)"], tablefmt="grid"))

    # Login demonstrations
    registrar = identities["Registrar"]
    student = identities["Student"]
    employer = identities["Employer"]

    login_ok = auth.login(registrar.wallet_address, registrar.private_key)
    login_fail = auth.login(registrar.wallet_address, "deadbeef" * 8)
    expired_token = auth.create_expired_token_demo(identities)
    login_expired = auth.reject_expired_token(expired_token)

    login_results = [
        ["Successful login (Registrar)", login_ok.status],
        ["Wrong private key", login_fail.status],
        ["Expired token rejection", login_expired.status],
    ]
    print("\nLogin Results:")
    print(tabulate(login_results, headers=["Case", "Result"], tablefmt="grid"))

    active_token = login_ok.session_token or ""
    print(f"\nActive Session Token (first 16): {active_token[:16]}")
    print(f"Role: {login_ok.role}")

    perm_rows = [[role, ", ".join(perms)] for role, perms in ROLE_PERMISSIONS.items()]
    print("\nRole-Permission Mapping:")
    print(tabulate(perm_rows, headers=["Role", "Permissions"], tablefmt="grid"))

    ledger.append("IDENTITY_INIT", registrar.wallet_address, {"roles": list(identities.keys())})
    ledger.append("LOGIN_SUCCESS", registrar.wallet_address, {"status": login_ok.status})
    ledger.append("LOGIN_FAILED", registrar.wallet_address, {"status": login_fail.status})
    ledger.append("LOGIN_EXPIRED", employer.wallet_address, {"status": login_expired.status})

    # ── PART B: IPFS Documents ────────────────────────────────────────────
    print_section("PART B — IPFS Storage & Document Integrity")

    cert1 = {
        "student": "Alice Johnson",
        "degree": "BSc Computer Science",
        "university": "National Tech University",
        "year": 2024,
        "gpa": "3.85",
    }
    cert2 = {
        "student": "Bob Smith",
        "degree": "MSc Data Science",
        "university": "National Tech University",
        "year": 2025,
        "gpa": "3.92",
    }
    cert_spare = {
        "student": "Carol Williams",
        "degree": "PhD Blockchain Systems",
        "university": "National Tech University",
        "year": 2026,
        "gpa": "4.00",
    }

    doc1 = ipfs.store_document("alice_bsc.json", cert1)
    doc2 = ipfs.store_document("bob_msc.json", cert2)
    doc3 = ipfs.store_document("carol_phd_spare.json", cert_spare)

    cid_rows = [
        [d.filename, d.cid[:20], d.pinata_ipfs_hash[:20] if d.pinata_ipfs_hash else "—"]
        for d in ipfs.documents
    ]
    print("\nDocument-to-CID Mapping (SHA-256 CID + Pinata IPFS):")
    print(tabulate(cid_rows, headers=["Filename", "SHA-256 CID (20)", "Pinata IPFS (20)"], tablefmt="grid"))

    integrity_rows = []
    for d in ipfs.documents:
        status, reason = ipfs.verify_document(d.cid)
        integrity_rows.append([d.filename, status, reason[:40]])
    print("\nIntegrity Check (before tampering):")
    print(tabulate(integrity_rows, headers=["File", "Status", "Reason"], tablefmt="grid"))

    ledger.append("DOC_STORED", registrar.wallet_address, {"cids": [d.cid[:20] for d in ipfs.documents]})

    # ── PART A continued: Deploy & Issue Credentials ──────────────────────
    print_section("PART A — Contract Deployment & Credential Operations")

    print(f"\nNetwork mode: {registry.network_label if hasattr(registry, 'network_label') else 'local'}")
    registry.connect()
    registry.register_registrar_wallet(registrar.wallet_address)

    info = registry.deployment_info
    assert info
    print(f"\nContract Address: {info.contract_address}")
    print(f"Deployment TX Hash: {info.deployment_tx_hash}")
    print(f"ABI Functions: {', '.join(info.abi_functions)}")

    ledger.append("CONTRACT_DEPLOYED", registrar.wallet_address, {
        "address": info.contract_address,
        "tx": info.deployment_tx_hash[:20],
    })

    # Issue 2 credentials with session verification
    session = auth.require_session(active_token, allowed_roles=["Registrar"])
    cred_id_1 = registry.issue_credential("Alice Johnson", registrar.wallet_address, doc1.cid)
    ledger.append("CREDENTIAL_ISSUED", session.wallet_address, {
        "id": cred_id_1, "student": "Alice Johnson", "cid": doc1.cid[:20],
    })

    cred_id_2 = registry.issue_credential("Bob Smith", registrar.wallet_address, doc2.cid)
    ledger.append("CREDENTIAL_ISSUED", session.wallet_address, {
        "id": cred_id_2, "student": "Bob Smith", "cid": doc2.cid[:20],
    })

    issue_rows = [
        [c.credential_id, c.student_name, c.document_cid[:20], c.status]
        for c in registry.issued_credentials
    ]
    print("\nIssued Credentials:")
    print(tabulate(issue_rows, headers=["ID", "Student", "CID (20)", "Status"], tablefmt="grid"))

    # Revoke credential 2
    revoke_tx = registry.revoke_credential(cred_id_2)
    ledger.append("CREDENTIAL_REVOKED", session.wallet_address, {"id": cred_id_2, "tx": revoke_tx[:20]})
    print(f"\nRevoke Result: Credential {cred_id_2} -> REVOKED (tx: {revoke_tx[:20]}...)")

    # Attempt verify revoked credential
    ok_rev, revert_msg, _ = registry.verify_credential_on_chain(cred_id_2)
    ledger.append("VERIFY_REVOKED_ATTEMPT", employer.wallet_address, {
        "id": cred_id_2, "reverted": not ok_rev,
    })
    print(f"\nRevoked Credential Verification Revert: {revert_msg}")

    # Block invalid session
    try:
        auth.require_session("invalid_token_xyz")
    except PermissionError:
        pass

    # ── PART B: Tampering Demo ────────────────────────────────────────────
    print_section("PART B — Tampering Detection & AI Threat Analysis")

    tamper_reason = ipfs.tamper_document(doc3.cid)
    tampered_status, tamper_detail = ipfs.verify_document(doc3.cid)
    ledger.append("DOC_TAMPERED", "0xattacker", {"cid": doc3.cid[:20], "reason": tamper_reason})

    print(f"\nTampered Document: {tamper_reason}")
    print(f"verify_document() -> {tampered_status}: {tamper_detail}")

    # Update integrity after tamper
    integrity_rows_after = []
    for d in ipfs.documents:
        status, reason = ipfs.verify_document(d.cid)
        integrity_rows_after.append([d.filename, status])
    print("\nIntegrity Check (after tampering):")
    print(tabulate(integrity_rows_after, headers=["File", "Status"], tablefmt="grid"))

    # Synthetic security events to reach 20+ records
    for i in range(15):
        security_log.record(
            "synthetic_verify_attempt",
            f"0x{'a' * 38}{i:02x}",
            f"Synthetic verification attempt #{i+1}",
            verification_attempts=(i % 5) + 1,
            failed_logins=i % 3,
            wallet_age_blocks=50 + i * 10,
        )

    sec_tx_ids = [tx.tx_id for tx in ledger.transactions]
    threat.train_and_classify(sec_tx_ids)

    threat_rows = [[a.tx_id, a.threat_level, a.confidence] for a in threat.assessments[:10]]
    print(f"\nTraining Dataset Size: {threat.training_size}")
    print(f"Model Accuracy: {threat.model_accuracy}%")
    print("\nPer-Transaction Threat Table (sample):")
    print(tabulate(threat_rows, headers=["TX ID", "Threat", "Confidence"], tablefmt="grid"))

    high_alerts = [[a.tx_id, a.threat_level, a.confidence, a.reason[:40]] for a in threat.high_alerts]
    print("\nHIGH Alerts sent to Dashboard:")
    if high_alerts:
        print(tabulate(high_alerts, headers=["TX ID", "Level", "Conf", "Reason"], tablefmt="grid"))
    else:
        print("  (none from real events — synthetic HIGH may appear after tamper events)")

    for a in threat.assessments:
        ledger.append("THREAT_ASSESSED", a.tx_id, {
            "level": a.threat_level, "confidence": a.confidence,
        })

    # ── PART C: Ledger & Merkle Tree ──────────────────────────────────────
    print_section("PART C — Chained Ledger & Merkle Tree")

    tx_log_rows = [
        [tx.tx_id, tx.action, tx.payload_hash[:16], tx.prev_hash[:16]]
        for tx in ledger.transactions
    ]
    print("\nFull Transaction Log:")
    print(tabulate(tx_log_rows, headers=["TX ID", "Action", "Payload (16)", "Prev (16)"], tablefmt="grid"))
    print(f"\nTotal transactions: {len(ledger.transactions)} (min 10 required)")

    chain_results = ledger.verify_chain()
    chain_rows = [[tx_id, status] for tx_id, status in chain_results]
    print("\nChain Verification:")
    print(tabulate(chain_rows, headers=["TX ID", "Status"], tablefmt="grid"))

    original_tree = MerkleTree(ledger.payload_hashes())
    original_root = original_tree.get_root()
    print(f"\nOriginal Merkle Root: {original_root}")

    # Tamper transaction #3 (index 2)
    tamper_idx = 2
    ledger.tamper_transaction(tamper_idx)
    tampered_tree = MerkleTree(ledger.payload_hashes())
    tampered_root = tampered_tree.get_root()
    changed_path = tampered_tree.changed_path_after_tamper(original_tree, tamper_idx)

    print(f"Tampered Merkle Root: {tampered_root}")
    print(f"Changed-node path (leaf {tamper_idx} -> root):")
    for node in changed_path:
        print(f"  -> {node}")

    # Merkle proof for transaction #1 (index 0)
    proof = original_tree.get_proof(0)
    leaf0 = ledger.transactions[0].payload_hash
    proof_valid = MerkleTree.verify_proof(leaf0, proof, original_root)
    print(f"\nMerkle Proof for TX-0001: {len(proof)} siblings")
    print(f"Merkle Proof Verification: {'VALID' if proof_valid else 'INVALID'}")

    # ── Verify Credential Demo ──────────────────────────────────────────
    print_section("PART C — Verify Credential Demonstration")

    employer_login = auth.login(employer.wallet_address, employer.private_key)
    emp_token = employer_login.session_token or ""

    # VALID credential
    cred_valid = registry.get_credential(cred_id_1)
    integrity1, _ = ipfs.verify_document(cred_valid.document_cid)
    ok1, msg1, _ = registry.verify_credential_on_chain(cred_id_1)
    result1 = "VALID" if ok1 and integrity1 == "INTACT" else "INVALID"
    print(f"\nVerify Credential {cred_id_1}: {result1}")

    # REVOKED credential
    ok2, msg2, _ = registry.verify_credential_on_chain(cred_id_2)
    result2 = "REVOKED" if not ok2 else "VALID"
    print(f"Verify Credential {cred_id_2}: {result2} — {msg2[:80]}")

    verify_results = [
        {"credential_id": cred_id_1, "result": result1, "details": "On-chain VALID + document INTACT"},
        {"credential_id": cred_id_2, "result": result2, "details": msg2[:80]},
    ]

    # ── Dashboard State ───────────────────────────────────────────────────
    identity_panel = []
    for role, ident in identities.items():
        status = "ACTIVE" if role == "Registrar" and login_ok.success else (
            "ACTIVE" if role == "Employer" and employer_login.success else "INACTIVE"
        )
        identity_panel.append({
            "role": ident.role,
            "wallet_address": ident.wallet_address,
            "public_key": ident.public_key,
            "session_status": status,
        })

    cred_panel = [
        {
            "credential_id": c.credential_id,
            "student_name": c.student_name,
            "registrar": c.registrar,
            "status": c.status,
        }
        for c in registry.issued_credentials
    ]

    threat_panel = [
        {
            "tx_id": a.tx_id,
            "threat_level": a.threat_level,
            "confidence": a.confidence,
            "reason": a.reason,
        }
        for a in threat.high_alerts + threat.assessments[:5]
    ]

    tx_panel = [
        {"tx_id": tx.tx_id, "payload_hash": tx.payload_hash, "action": tx.action}
        for tx in ledger.transactions
    ]

    chain_ver_panel = [{"tx_id": tid, "status": st} for tid, st in chain_results]

    dashboard.update(
        identities=identity_panel,
        credentials=cred_panel,
        threat_feed=threat_panel,
        transaction_chain=tx_panel,
        merkle_root=original_root,
        tampered_merkle_root=tampered_root,
        tamper_flag=True,
        chain_verification=chain_ver_panel,
        merkle_proof_valid=proof_valid,
        active_session_token=active_token[:16],
        role_permissions=ROLE_PERMISSIONS,
        contract_info={
            "address": info.contract_address,
            "deployment_tx": info.deployment_tx_hash,
            "abi_functions": info.abi_functions,
        },
        verify_results=verify_results,
    )

    print_section("LIVE DASHBOARD — All 4 Panels")
    from backend.part_c.dashboard import DashboardState
    render_dashboard(dashboard.state)  # type: ignore[arg-type]

    return dashboard, auth, registry, ipfs, ledger, threat


if __name__ == "__main__":
    result = run()
    if isinstance(result, tuple):
        dashboard, auth, registry, ipfs, ledger, threat = result
        from backend.api import bind_runtime
        bind_runtime(auth, registry, ipfs, ledger, threat, dashboard)
        print("\nAPI available at http://127.0.0.1:5000/api/dashboard")
        print("POST /api/verify-credential with {session_token, credential_id}")
