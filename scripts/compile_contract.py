"""Compile CredentialRegistry.sol and save artifact for Web3 deployment."""

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CONTRACT = ROOT / "contracts" / "CredentialRegistry.sol"
OUT = ROOT / "contracts" / "CredentialRegistry.json"


def main() -> None:
    import solcx

    solcx.install_solc("0.8.20")
    solcx.set_solc_version("0.8.20")
    compiled = solcx.compile_files(
        [str(CONTRACT)],
        output_values=["abi", "bin"],
    )
    key = next(k for k in compiled if k.endswith(":CredentialRegistry"))
    artifact = {
        "contractName": "CredentialRegistry",
        "abi": compiled[key]["abi"],
        "bytecode": compiled[key]["bin"],
    }
    OUT.write_text(json.dumps(artifact, indent=2), encoding="utf-8")
    print(f"Compiled -> {OUT}")


if __name__ == "__main__":
    main()
