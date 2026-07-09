"""Part A: Deploy CredentialRegistry and interact via Web3.py."""

from __future__ import annotations

import json
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from eth_account import Account
from web3 import Web3
from web3.providers.eth_tester import EthereumTesterProvider

from backend.config import (
    CONTRACTS_DIR,
    REMIX_CONTRACT_ADDRESS,
    REMIX_RPC_URL,
    SEPOLIA_CONTRACT_CACHE,
    SEPOLIA_PRIVATE_KEY,
    SEPOLIA_RPC_URL,
    USE_SEPOLIA,
)
from backend.security_events import SecurityEventLog

# Pre-compiled ABI/bytecode for CredentialRegistry.sol (^0.8.20)
CONTRACT_ABI: list[dict[str, Any]] = [
    {"inputs": [], "stateMutability": "nonpayable", "type": "constructor"},
    {
        "anonymous": False,
        "inputs": [
            {"indexed": True, "name": "credentialId", "type": "uint256"},
            {"indexed": False, "name": "studentName", "type": "string"},
            {"indexed": True, "name": "registrar", "type": "address"},
            {"indexed": False, "name": "documentCid", "type": "string"},
            {"indexed": False, "name": "issueTimestamp", "type": "uint256"},
        ],
        "name": "CredentialIssued",
        "type": "event",
    },
    {
        "anonymous": False,
        "inputs": [
            {"indexed": True, "name": "credentialId", "type": "uint256"},
            {"indexed": True, "name": "revokedBy", "type": "address"},
        ],
        "name": "CredentialRevoked",
        "type": "event",
    },
    {
        "anonymous": False,
        "inputs": [
            {"indexed": True, "name": "credentialId", "type": "uint256"},
            {"indexed": True, "name": "from", "type": "address"},
            {"indexed": True, "name": "to", "type": "address"},
        ],
        "name": "CredentialTransferred",
        "type": "event",
    },
    {"inputs": [{"name": "registrar", "type": "address"}], "name": "addRegistrar", "outputs": [], "stateMutability": "nonpayable", "type": "function"},
    {"inputs": [], "name": "admin", "outputs": [{"name": "", "type": "address"}], "stateMutability": "view", "type": "function"},
    {"inputs": [{"name": "", "type": "uint256"}], "name": "credentials", "outputs": [
        {"name": "id", "type": "uint256"}, {"name": "studentName", "type": "string"},
        {"name": "registrar", "type": "address"}, {"name": "documentCid", "type": "string"},
        {"name": "issueTimestamp", "type": "uint256"}, {"name": "status", "type": "uint8"},
        {"name": "owner", "type": "address"},
    ], "stateMutability": "view", "type": "function"},
    {"inputs": [], "name": "credentialCount", "outputs": [{"name": "", "type": "uint256"}], "stateMutability": "view", "type": "function"},
    {
        "inputs": [{"name": "credentialId", "type": "uint256"}],
        "name": "getCredential",
        "outputs": [
            {"name": "id", "type": "uint256"}, {"name": "studentName", "type": "string"},
            {"name": "registrar", "type": "address"}, {"name": "documentCid", "type": "string"},
            {"name": "issueTimestamp", "type": "uint256"}, {"name": "status", "type": "uint8"},
            {"name": "owner", "type": "address"},
        ],
        "stateMutability": "view", "type": "function",
    },
    {
        "inputs": [{"name": "studentName", "type": "string"}, {"name": "registrar", "type": "address"}, {"name": "documentCid", "type": "string"}],
        "name": "issueCredential",
        "outputs": [{"name": "", "type": "uint256"}],
        "stateMutability": "nonpayable", "type": "function",
    },
    {"inputs": [{"name": "", "type": "address"}], "name": "isRegistrar", "outputs": [{"name": "", "type": "bool"}], "stateMutability": "view", "type": "function"},
    {"inputs": [{"name": "credentialId", "type": "uint256"}], "name": "revokeCredential", "outputs": [], "stateMutability": "nonpayable", "type": "function"},
    {
        "inputs": [{"name": "credentialId", "type": "uint256"}, {"name": "newOwner", "type": "address"}],
        "name": "transferCredentialOwnership",
        "outputs": [],
        "stateMutability": "nonpayable", "type": "function",
    },
    {
        "inputs": [{"name": "credentialId", "type": "uint256"}],
        "name": "verifyCredential",
        "outputs": [
            {"name": "id", "type": "uint256"}, {"name": "studentName", "type": "string"},
            {"name": "registrar", "type": "address"}, {"name": "documentCid", "type": "string"},
            {"name": "status", "type": "uint8"},
        ],
        "stateMutability": "view", "type": "function",
    },
]

# Bytecode compiled from CredentialRegistry.sol - will be loaded or compiled
CONTRACT_BYTECODE: str = ""


@dataclass
class DeploymentInfo:
    contract_address: str
    deployment_tx_hash: str
    abi_functions: list[str]


@dataclass
class CredentialRecord:
    credential_id: int
    student_name: str
    registrar: str
    document_cid: str
    status: str
    issue_timestamp: int


class CredentialRegistryClient:
    def __init__(self, security_log: SecurityEventLog) -> None:
        self.security_log = security_log
        self.w3: Web3 | None = None
        self.contract = None
        self.deployer_address: str | None = None
        self.deployment_info: DeploymentInfo | None = None
        self.captured_events: list[dict[str, Any]] = []
        self.issued_credentials: list[CredentialRecord] = []
        self._bytecode = CONTRACT_BYTECODE
        self._sepolia_account: Account | None = None
        self.network_label = "local"

    def _abi_function_names(self) -> list[str]:
        abi = self._load_abi()
        return [f["name"] for f in abi if f.get("type") == "function" and f.get("name")]

    def _load_abi(self) -> list[dict[str, Any]]:
        artifact = CONTRACTS_DIR / "CredentialRegistry.json"
        if artifact.exists():
            return json.loads(artifact.read_text(encoding="utf-8"))["abi"]
        return CONTRACT_ABI

    def _verify_contract_on_chain(self, address: str) -> None:
        assert self.w3
        addr = Web3.to_checksum_address(address)
        code = self.w3.eth.get_code(addr)
        if not code or code == b"0x" or len(code) < 10:
            raise RuntimeError(
                f"No contract bytecode at {address}. Deployment likely failed — "
                "delete data/sepolia_contract.json and run again."
            )

    def _sepolia_gas_params(self) -> dict[str, int]:
        assert self.w3
        try:
            latest = self.w3.eth.get_block("latest")
            base_fee = latest.get("baseFeePerGas") or self.w3.eth.gas_price
        except Exception:
            base_fee = self.w3.eth.gas_price
        priority = self.w3.to_wei(2, "gwei")
        return {
            "maxFeePerGas": int(base_fee * 2 + priority),
            "maxPriorityFeePerGas": priority,
        }

    def _send_transaction(self, fn) -> tuple[Any, str]:
        """Send contract tx via Sepolia signed raw tx or local eth-tester."""
        assert self.w3 and self.deployer_address
        if self._sepolia_account:
            account = self._sepolia_account
            gas_params = self._sepolia_gas_params()
            tx = fn.build_transaction({
                "from": account.address,
                "nonce": self.w3.eth.get_transaction_count(account.address),
                "chainId": self.w3.eth.chain_id,
                **gas_params,
            })
            try:
                tx["gas"] = int(self.w3.eth.estimate_gas(tx) * 1.3)
            except Exception:
                tx["gas"] = 2_000_000
            signed = account.sign_transaction(tx)
            tx_hash = self.w3.eth.send_raw_transaction(signed.raw_transaction)
            receipt = self.w3.eth.wait_for_transaction_receipt(tx_hash, timeout=300)
            if receipt.get("status", 0) != 1:
                raise RuntimeError(
                    f"Sepolia transaction failed (status=0). tx={tx_hash.hex()}. "
                    "Check https://sepolia.etherscan.io for details."
                )
            return receipt, tx_hash.hex()
        tx_hash = fn.transact({"from": self.deployer_address})
        receipt = self.w3.eth.wait_for_transaction_receipt(tx_hash)
        return receipt, tx_hash.hex() if isinstance(tx_hash, bytes) else str(tx_hash)

    def _bind_contract(self, address: str, deployment_tx: str) -> None:
        assert self.w3
        abi = self._load_abi()
        checksum = Web3.to_checksum_address(address)
        self._verify_contract_on_chain(checksum)
        self.contract = self.w3.eth.contract(address=checksum, abi=abi)
        self.deployment_info = DeploymentInfo(
            contract_address=checksum,
            deployment_tx_hash=deployment_tx,
            abi_functions=self._abi_function_names(),
        )

    def _connect_sepolia(self) -> None:
        self.w3 = Web3(Web3.HTTPProvider(SEPOLIA_RPC_URL))
        if not self.w3.is_connected():
            raise ConnectionError(f"Cannot connect to Sepolia RPC: {SEPOLIA_RPC_URL}")
        self._sepolia_account = Account.from_key(SEPOLIA_PRIVATE_KEY)
        self.deployer_address = self._sepolia_account.address
        self.network_label = "sepolia"
        print(f"  Sepolia account: {self.deployer_address}")
        print(f"  Sepolia balance: {self.w3.from_wei(self.w3.eth.get_balance(self.deployer_address), 'ether')} ETH")

        if REMIX_CONTRACT_ADDRESS:
            self._bind_contract(REMIX_CONTRACT_ADDRESS, "remix_deployed")
            return

        if SEPOLIA_CONTRACT_CACHE.exists():
            cached = json.loads(SEPOLIA_CONTRACT_CACHE.read_text(encoding="utf-8"))
            addr = cached.get("address", "")
            try:
                if addr:
                    self._verify_contract_on_chain(addr)
                    self._bind_contract(addr, cached.get("tx_hash", "cached"))
                    print(f"  Reusing cached Sepolia contract: {addr}")
                    return
            except RuntimeError:
                print(f"  Cached contract {addr} invalid — redeploying...")
                SEPOLIA_CONTRACT_CACHE.unlink(missing_ok=True)

        abi = self._load_abi()
        bytecode = self._load_bytecode()
        Contract = self.w3.eth.contract(abi=abi, bytecode=bytecode)
        receipt, tx_hex = self._send_transaction(Contract.constructor())
        address = receipt.contractAddress
        if not address:
            raise RuntimeError("Deploy receipt has no contractAddress — deployment failed.")
        time.sleep(3)
        self._bind_contract(address, tx_hex)
        SEPOLIA_CONTRACT_CACHE.write_text(
            json.dumps({"address": address, "tx_hash": tx_hex}, indent=2),
            encoding="utf-8",
        )
        print(f"  Deployed new contract on Sepolia: {address}")
        print(f"  Etherscan: https://sepolia.etherscan.io/address/{address}")

    def _load_bytecode(self) -> str:
        if self._bytecode:
            return self._bytecode
        artifact = CONTRACTS_DIR / "CredentialRegistry.json"
        if artifact.exists():
            data = json.loads(artifact.read_text(encoding="utf-8"))
            return data.get("bytecode", "") or data.get("data", {}).get("bytecode", {}).get("object", "")
        try:
            import solcx
            solcx.install_solc("0.8.20")
            solcx.set_solc_version("0.8.20")
            compiled = solcx.compile_files(
                [str(CONTRACTS_DIR / "CredentialRegistry.sol")],
                output_values=["abi", "bin"],
            )
            key = next(k for k in compiled if k.endswith(":CredentialRegistry"))
            self._bytecode = compiled[key]["bin"]
            return self._bytecode
        except Exception:
            raise RuntimeError(
                "Contract bytecode not found. Run: python scripts/compile_contract.py"
            )

    def connect(self) -> None:
        if USE_SEPOLIA:
            self._connect_sepolia()
            return

        if REMIX_CONTRACT_ADDRESS:
            self.w3 = Web3(Web3.HTTPProvider(REMIX_RPC_URL))
            if not self.w3.is_connected():
                raise ConnectionError(f"Cannot connect to {REMIX_RPC_URL}")
            self._bind_contract(REMIX_CONTRACT_ADDRESS, "remix_deployed")
            self.network_label = "remix"
            return

        self.w3 = Web3(EthereumTesterProvider())
        self.deployer_address = self.w3.eth.accounts[0]
        self.network_label = "local"
        abi = self._load_abi()
        bytecode = self._load_bytecode()
        Contract = self.w3.eth.contract(abi=abi, bytecode=bytecode)
        tx = Contract.constructor().transact({"from": self.deployer_address})
        receipt = self.w3.eth.wait_for_transaction_receipt(tx)
        self._bind_contract(receipt.contractAddress, tx.hex() if isinstance(tx, bytes) else str(tx))

    def _eth_address_from_wallet(self, wallet_hex: str) -> str:
        """Map custom wallet hash to valid Ethereum address for local testing."""
        raw = wallet_hex.replace("0x", "")
        return Web3.to_checksum_address("0x" + raw[:40])

    def register_registrar_wallet(self, wallet_address: str) -> None:
        """On Sepolia the deployer is already registrar from constructor — skip."""
        if self._sepolia_account:
            return
        assert self.contract and self.w3 and self.deployer_address
        eth_addr = self._eth_address_from_wallet(wallet_address)
        if not self.contract.functions.isRegistrar(eth_addr).call():
            fn = self.contract.functions.addRegistrar(eth_addr)
            self._send_transaction(fn)

    def issue_credential(self, student_name: str, registrar_wallet: str, document_cid: str) -> int:
        assert self.contract and self.w3 and self.deployer_address
        if self._sepolia_account:
            registrar = self.deployer_address
        else:
            registrar = self._eth_address_from_wallet(registrar_wallet)
        fn = self.contract.functions.issueCredential(student_name, registrar, document_cid)
        receipt, _ = self._send_transaction(fn)
        for log in receipt.logs:
            decoded = self.contract.events.CredentialIssued().process_log(log)
            self.captured_events.append({"event": "CredentialIssued", "args": dict(decoded["args"])})
        cred_id = self.contract.functions.credentialCount().call()
        cred = self.get_credential(cred_id)
        self.issued_credentials.append(cred)
        return cred_id

    def revoke_credential(self, credential_id: int) -> str:
        assert self.contract and self.w3 and self.deployer_address
        fn = self.contract.functions.revokeCredential(credential_id)
        receipt, tx_hex = self._send_transaction(fn)
        for log in receipt.logs:
            decoded = self.contract.events.CredentialRevoked().process_log(log)
            self.captured_events.append({"event": "CredentialRevoked", "args": dict(decoded["args"])})
        for c in self.issued_credentials:
            if c.credential_id == credential_id:
                c.status = "REVOKED"
        return tx_hex

    def get_credential(self, credential_id: int) -> CredentialRecord:
        assert self.contract
        result = self.contract.functions.getCredential(credential_id).call()
        status = "VALID" if result[5] == 0 else "REVOKED"
        return CredentialRecord(
            credential_id=result[0],
            student_name=result[1],
            registrar=result[2],
            document_cid=result[3],
            status=status,
            issue_timestamp=result[4],
        )

    def verify_credential_on_chain(self, credential_id: int) -> tuple[bool, str, CredentialRecord | None]:
        assert self.contract
        try:
            result = self.contract.functions.verifyCredential(credential_id).call()
            cred = CredentialRecord(
                credential_id=result[0],
                student_name=result[1],
                registrar=result[2],
                document_cid=result[3],
                status="VALID",
                issue_timestamp=0,
            )
            return True, "VALID", cred
        except Exception as exc:
            msg = str(exc)
            if "REVOKED" in msg.upper():
                self.security_log.record(
                    "revoked_credential_verify",
                    "0xemployer",
                    f"Verification attempt on revoked credential {credential_id}",
                    verification_attempts=1,
                )
            return False, msg, None
