"""Flask API + professional web dashboard."""

from __future__ import annotations

from pathlib import Path

from flask import Flask, jsonify, render_template, request, send_from_directory
from flask_cors import CORS

from backend.part_c.dashboard import DashboardManager
from backend.screenshots_util import SCREENSHOTS_DIR, list_screenshots

WEB_DIR = Path(__file__).resolve().parent.parent / "web"

app = Flask(
    __name__,
    template_folder=str(WEB_DIR / "templates"),
    static_folder=str(WEB_DIR / "static"),
    static_url_path="/static",
)
CORS(app)

dashboard_mgr = DashboardManager()
_runtime: dict = {}


def bind_runtime(
    auth_manager,
    registry_client,
    ipfs_storage,
    ledger,
    threat_detector,
    dashboard: DashboardManager,
    identities: dict | None = None,
    employer_token: str = "",
    network_label: str = "local",
    ai_accuracy: float = 0.0,
    training_size: int = 0,
) -> None:
    _runtime["auth"] = auth_manager
    _runtime["registry"] = registry_client
    _runtime["ipfs"] = ipfs_storage
    _runtime["ledger"] = ledger
    _runtime["threat"] = threat_detector
    _runtime["identities"] = identities or {}
    _runtime["employer_token"] = employer_token
    _runtime["network_label"] = network_label
    _runtime["ai_accuracy"] = ai_accuracy
    _runtime["training_size"] = training_size
    global dashboard_mgr
    dashboard_mgr = dashboard


def _enriched_state() -> dict:
    state = dashboard_mgr.get_state()
    state["network_label"] = _runtime.get("network_label", "local")
    state["ai_accuracy"] = _runtime.get("ai_accuracy", 0)
    state["training_size"] = _runtime.get("training_size", 0)
    state["employer_session_token"] = _runtime.get("employer_token", "")
    ipfs = _runtime.get("ipfs")
    if ipfs and hasattr(ipfs, "documents"):
        state["documents"] = [
            {
                "filename": d.filename,
                "cid": d.cid,
                "pinata_ipfs_hash": d.pinata_ipfs_hash,
                "pinata_url": d.pinata_url,
            }
            for d in ipfs.documents
        ]
    state["screenshots"] = list_screenshots()
    return state


@app.route("/screenshots/<path:filename>")
def serve_screenshot(filename: str):
    return send_from_directory(SCREENSHOTS_DIR, filename)


@app.route("/api/screenshots", methods=["GET"])
def get_screenshots():
    return jsonify({"screenshots": list_screenshots(), "count": len(list_screenshots())})


def _read_web_file(*parts: str) -> str:
    path = WEB_DIR.joinpath(*parts)
    return path.read_text(encoding="utf-8")


@app.route("/")
def index():
    return render_template(
        "index.html",
        inline_css=_read_web_file("static", "css", "dashboard.css"),
        inline_js=_read_web_file("static", "js", "dashboard.js"),
    )


@app.route("/api/dashboard", methods=["GET"])
def get_dashboard():
    return jsonify(_enriched_state())


@app.route("/api/demo-login", methods=["POST"])
def demo_login():
    """Assignment demo: login by role using deterministic identity keys."""
    auth = _runtime.get("auth")
    identities = _runtime.get("identities", {})
    if not auth or not identities:
        return jsonify({"error": "System not initialized"}), 500

    role = (request.get_json(force=True) or {}).get("role", "Employer")
    ident = identities.get(role)
    if not ident:
        return jsonify({"error": f"Unknown role: {role}"}), 400

    result = auth.login(ident.wallet_address, ident.private_key)
    if not result.success:
        return jsonify({"error": result.message, "status": result.status}), 401

    return jsonify({
        "status": result.status,
        "role": result.role,
        "session_token": result.session_token,
        "token_preview": (result.session_token or "")[:16],
    })


@app.route("/api/verify-credential", methods=["POST"])
def verify_credential():
    body = request.get_json(force=True) or {}
    token = body.get("session_token", "")
    credential_id = int(body.get("credential_id", 0))

    auth = _runtime.get("auth")
    registry = _runtime.get("registry")
    ipfs = _runtime.get("ipfs")
    ledger = _runtime.get("ledger")

    if not all([auth, registry, ipfs, ledger]):
        return jsonify({"error": "System not initialized"}), 500

    try:
        auth.require_session(token, allowed_roles=["Employer", "Registrar", "Student"])
    except PermissionError as exc:
        return jsonify({"result": "DENIED", "details": str(exc)}), 403

    try:
        cred = registry.get_credential(credential_id)
    except Exception:
        dashboard_mgr.add_verify_result(credential_id, "NOT FOUND", "Credential does not exist")
        return jsonify({"result": "NOT FOUND", "details": "Credential not found"})

    if cred.status == "REVOKED":
        ok, msg, _ = registry.verify_credential_on_chain(credential_id)
        ledger.append("VERIFY_REVOKED", "employer", {"credential_id": credential_id, "msg": msg})
        dashboard_mgr.add_verify_result(credential_id, "REVOKED", msg)
        return jsonify({"result": "REVOKED", "details": msg})

    integrity, reason = ipfs.verify_document(cred.document_cid)
    if integrity == "TAMPERED":
        dashboard_mgr.add_verify_result(credential_id, "FORGED", reason)
        return jsonify({"result": "FORGED", "details": reason})

    ok, msg, verified = registry.verify_credential_on_chain(credential_id)
    if ok and verified:
        ledger.append("VERIFY_VALID", "employer", {
            "credential_id": credential_id,
            "student": verified.student_name,
            "cid": verified.document_cid,
        })
        dashboard_mgr.add_verify_result(
            credential_id, "VALID", "Credential verified on-chain and document intact"
        )
        return jsonify({
            "result": "VALID",
            "student": verified.student_name,
            "document_cid": verified.document_cid,
        })

    dashboard_mgr.add_verify_result(credential_id, "REVOKED", msg)
    return jsonify({"result": "REVOKED", "details": msg})


def run_api(host: str = "127.0.0.1", port: int = 5000) -> None:
    import webbrowser
    url = f"http://{host}:{port}"
    print(f"\n  Web Dashboard: {url}")
    print("  Press Ctrl+C to stop\n")
    webbrowser.open(url)
    app.run(host=host, port=port, debug=False, use_reloader=False)
