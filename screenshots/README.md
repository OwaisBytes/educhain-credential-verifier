# Screenshots

Add your lab exam / demo screenshots here before submission.

## Required Screenshots

| File name (suggested) | What to capture |
|----------------------|-----------------|
| `01-vscode-project.png` | VS Code with project folder open |
| `02-identity-login.png` | Identity table + login VERIFIED/FAILED/EXPIRED |
| `03-sepolia-etherscan.png` | Sepolia Etherscan contract page |
| `04-credentials-revoke.png` | Issued credentials + revoke output |
| `05-pinata-files.png` | Pinata dashboard with pinned certificates |
| `06-tamper-detection.png` | TAMPERED document detection result |
| `07-ai-threats.png` | AI threat table + HIGH alerts |
| `08-ledger-merkle.png` | Transaction log + Merkle root |
| `09-dashboard-overview.png` | Web dashboard — Overview page |
| `10-dashboard-wallets.png` | Web dashboard — Wallets page |
| `11-dashboard-credentials.png` | Web dashboard — Credentials page |
| `12-dashboard-threats.png` | Web dashboard — Threat Intel page |
| `13-dashboard-ledger.png` | Web dashboard — Audit Ledger page |
| `14-verify-valid.png` | Verify Credential ID=1 → VALID |
| `15-verify-revoked.png` | Verify Credential ID=2 → REVOKED |
| `16-metamask-sepolia.png` | MetaMask Sepolia transactions (optional) |

## How to take dashboard screenshots

1. Run `python server.py`
2. Open http://127.0.0.1:5000
3. Use **Win + Shift + S** to capture each panel
4. Save PNG files in this folder

## Display in README

After adding images, reference them in the main README:

```markdown
![Dashboard Overview](screenshots/09-dashboard-overview.png)
```
