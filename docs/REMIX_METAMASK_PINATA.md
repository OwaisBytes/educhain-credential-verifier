# Remix + MetaMask + Pinata Setup Guide

Use this guide to deploy the smart contract via **Remix IDE** and connect **MetaMask**, while the Python backend handles Parts A/B/C.

---

## Step 1: Install MetaMask

1. Install [MetaMask](https://metamask.io/) browser extension.
2. Create/import a wallet.
3. Add a test network:
   - **Sepolia** (recommended for Pinata + public testnet), or
   - **Local Hardhat/Ganache** at `http://127.0.0.1:8545`

---

## Step 2: Deploy Contract in Remix

1. Open [https://remix.ethereum.org](https://remix.ethereum.org)
2. Create file: `CredentialRegistry.sol`
3. Copy contents from `c:\BLOCKCHAINFINAL\contracts\CredentialRegistry.sol`
4. Compile with Solidity **0.8.20+**
5. **Deploy & Run Transactions** tab:
   - Environment: **Injected Provider - MetaMask**
   - Contract: `CredentialRegistry`
   - Click **Deploy** → confirm in MetaMask
6. **Copy the deployed contract address** (e.g. `0xABC...`)

---

## Step 3: Pinata IPFS (Optional — real IPFS)

1. Create account at [https://pinata.cloud](https://pinata.cloud)
2. API Keys → New Key → copy **API Key** and **Secret**
3. In PowerShell:

```powershell
$env:PINATA_API_KEY = "your_pinata_api_key"
$env:PINATA_SECRET = "your_pinata_secret"
```

The backend uploads certificate JSON to Pinata when these are set. CIDs are still computed locally via SHA-256 for integrity checks.

---

## Step 4: Connect Python Backend to Remix Contract

```powershell
cd c:\BLOCKCHAINFINAL
$env:REMIX_CONTRACT_ADDRESS = "0xYOUR_DEPLOYED_ADDRESS"
$env:REMIX_RPC_URL = "https://sepolia.infura.io/v3/YOUR_KEY"   # or local node
pip install -r requirements.txt
python backend\main.py
```

When `REMIX_CONTRACT_ADDRESS` is set, Web3.py connects to your live contract instead of the local eth-tester.

---

## Step 5: Interact via Remix UI

After deployment, use Remix to call contract functions:

| Function | Who | Example |
|----------|-----|---------|
| `issueCredential(name, registrar, cid)` | Registrar (deployer) | `"Alice Johnson", 0xRegistrar..., "b3eafcee..."` |
| `revokeCredential(id)` | Registrar | `2` |
| `getCredential(id)` | Anyone | `1` |
| `verifyCredential(id)` | Anyone | `1` → succeeds; `2` if revoked → **reverts** |

Get CIDs by running the Python backend first — it prints the Document-to-CID table.

---

## Step 6: VS Code Workflow

1. Open folder: `c:\BLOCKCHAINFINAL` in VS Code
2. Terminal → run `python backend\main.py`
3. Screenshot the terminal dashboard for your submission
4. Use Remix for on-chain demo video if required

---

## Registrar Wallet Addresses (from Python run)

Run `python backend\main.py` once — the **Identity Table** prints deterministic wallet addresses for:

- **Registrar** — can issue/revoke (mapped to Ethereum address in contract)
- **Student** — credential owner
- **Employer** — verifier role

---

## Troubleshooting

| Issue | Fix |
|-------|-----|
| MetaMask wrong network | Switch to Sepolia or your local chain |
| `onlyRegistrar` revert | Deployer is auto-registrar; call `addRegistrar(addr)` for others |
| Pinata upload fails | Check API keys; simulated SHA-256 CID still works offline |
| Contract not found | Verify `REMIX_CONTRACT_ADDRESS` matches Remix deployment |

---

## Assignment Mapping

- **Part A**: Python identity + Remix contract + MetaMask deploy
- **Part B**: Pinata or simulated IPFS + Python AI layer
- **Part C**: Python ledger/Merkle + terminal dashboard (or Flask API)

All outputs required by the assignment are produced by `python backend\main.py`.
