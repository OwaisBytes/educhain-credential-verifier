"""
Start the Credential Verification DApp with professional web dashboard.
Runs full pipeline (Parts A, B, C) then opens http://127.0.0.1:5000
"""

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))

from backend.api import bind_runtime, run_api
from backend.main import run


if __name__ == "__main__":
    print("Initializing blockchain credential system...")
    result = run()
    if isinstance(result, tuple):
        dashboard, auth, registry, ipfs, ledger, threat = result

        identities = {}
        for ident in auth._identities_by_wallet.values():
            identities[ident.role] = ident

        employer = identities.get("Employer")
        employer_token = ""
        if employer:
            login = auth.login(employer.wallet_address, employer.private_key)
            employer_token = login.session_token or ""

        bind_runtime(
            auth,
            registry,
            ipfs,
            ledger,
            threat,
            dashboard,
            identities=identities,
            employer_token=employer_token,
            network_label=getattr(registry, "network_label", "local"),
            ai_accuracy=threat.model_accuracy,
            training_size=threat.training_size,
        )
        run_api()
