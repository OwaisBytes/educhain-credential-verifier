"""Global configuration for the Credential Verification DApp."""

import os
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent.parent
CONTRACTS_DIR = ROOT_DIR / "contracts"
CERTIFICATES_DIR = ROOT_DIR / "certificates"
DATA_DIR = ROOT_DIR / "data"

# Load .env from project root
_env_path = ROOT_DIR / ".env"
if _env_path.exists():
    try:
        from dotenv import load_dotenv
        load_dotenv(_env_path)
    except ImportError:
        for line in _env_path.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                k, _, v = line.partition("=")
                os.environ.setdefault(k.strip(), v.strip())

DATA_DIR.mkdir(parents=True, exist_ok=True)

ROLE_SEEDS = {
    "Registrar": "university_registrar_seed_v1",
    "Student": "student_credential_owner_seed_v1",
    "Employer": "employer_verifier_seed_v1",
}

SESSION_TTL_SECONDS = 3600

NETWORK = os.getenv("NETWORK", "local").lower()
SEPOLIA_RPC_URL = os.getenv("SEPOLIA_RPC_URL", "https://ethereum-sepolia-rpc.publicnode.com")
SEPOLIA_PRIVATE_KEY = os.getenv("SEPOLIA_PRIVATE_KEY", "").strip().removeprefix("0x")

REMIX_CONTRACT_ADDRESS = os.getenv("REMIX_CONTRACT_ADDRESS", "").strip()
REMIX_RPC_URL = os.getenv("REMIX_RPC_URL", SEPOLIA_RPC_URL)

PINATA_API_KEY = os.getenv("PINATA_API_KEY", "")
PINATA_SECRET = os.getenv("PINATA_SECRET", "")
PINATA_JWT = os.getenv("PINATA_JWT", "")
USE_PINATA = bool(PINATA_API_KEY and PINATA_SECRET)

SEPOLIA_CONTRACT_CACHE = DATA_DIR / "sepolia_contract.json"
USE_SEPOLIA = NETWORK == "sepolia" and bool(SEPOLIA_PRIVATE_KEY)
