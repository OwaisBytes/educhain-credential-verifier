"""Rich terminal dashboard renderer."""

from __future__ import annotations

from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich import box

from backend.part_c.dashboard import DashboardState


def render_dashboard(state: DashboardState) -> None:
    console = Console(width=120)

    t1 = Table(title="Panel 1 — Wallet Identities", box=box.ROUNDED, expand=True)
    t1.add_column("Role", style="cyan")
    t1.add_column("Wallet Address")
    t1.add_column("Public Key (20)")
    t1.add_column("Session Status")
    for ident in state.identities:
        t1.add_row(
            ident["role"],
            ident["wallet_address"][:42],
            ident["public_key"][:20],
            ident.get("session_status", "INACTIVE"),
        )
    console.print(Panel(t1, title="[bold]Academic Credential Verification Dashboard[/]", border_style="blue"))

    t2 = Table(title="Panel 2 — Issued Credentials", box=box.ROUNDED, expand=True)
    t2.add_column("ID")
    t2.add_column("Student")
    t2.add_column("Registrar")
    t2.add_column("Status")
    for c in state.credentials:
        reg = c["registrar"]
        t2.add_row(str(c["credential_id"]), c["student_name"], str(reg)[:20], c["status"])
    console.print(t2)

    t3 = Table(title="Panel 3 — Threat Alert Feed", box=box.ROUNDED, expand=True)
    t3.add_column("TX ID")
    t3.add_column("Threat")
    t3.add_column("Confidence")
    t3.add_column("Reason", overflow="fold")
    for alert in state.threat_feed[:15]:
        level = alert["threat_level"]
        style = "bold red" if level == "HIGH" else ("yellow" if level == "MEDIUM" else "green")
        t3.add_row(alert["tx_id"], f"[{style}]{level}[/]", str(alert["confidence"]), alert["reason"][:80])
    console.print(t3)

    t4 = Table(title="Panel 4 — Transaction Chain & Merkle Root", box=box.ROUNDED, expand=True)
    t4.add_column("TX ID")
    t4.add_column("Hash (16)")
    t4.add_column("Chain Status")
    for i, tx in enumerate(state.transaction_chain[:12]):
        chain_st = state.chain_verification[i]["status"] if i < len(state.chain_verification) else ""
        t4.add_row(tx["tx_id"], tx["payload_hash"][:16], chain_st)
    merkle_short = state.merkle_root[:32] if state.merkle_root else ""
    t4.add_row("MERKLE ROOT", merkle_short, "VALID" if state.merkle_proof_valid else "")
    if state.tamper_flag:
        t4.add_row("TAMPERED ROOT", state.tampered_merkle_root[:32], "MODIFIED")
    console.print(t4)

    if state.verify_results:
        tv = Table(title="Verify Credential Results", box=box.ROUNDED)
        tv.add_column("Credential ID")
        tv.add_column("Result")
        tv.add_column("Details")
        for vr in state.verify_results:
            tv.add_row(str(vr["credential_id"]), vr["result"], vr["details"][:70])
        console.print(tv)
