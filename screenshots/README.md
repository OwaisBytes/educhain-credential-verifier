# Screenshots for GitHub README

Add your lab exam screenshots here as **PNG** or **JPG** files.

## Quick steps (show on GitHub main page)

1. Save screenshots into this folder, e.g.:
   - `09-dashboard-overview.png`
   - `14-verify-valid.png`
   - `15-verify-revoked.png`

2. Run the sync script (updates README with image tags):
   ```bash
   python scripts/sync_readme_screenshots.py
   ```

3. Push to GitHub:
   ```bash
   git add screenshots/ README.md
   git commit -m "Add demo screenshots"
   git push
   ```

4. Open your repo — images appear in the **Demo Preview** section on the main page.

> **Important:** GitHub only shows images that are **committed and pushed**.  
> Plain text paths like `screenshots/file.png` do NOT display — the sync script creates proper `![alt](screenshots/file.png)` markdown.

---

## Suggested screenshot list

| Filename | What to capture |
|----------|-----------------|
| `01-vscode-project.png` | VS Code project folder |
| `02-identity-login.png` | Identity table + login results |
| `03-sepolia-etherscan.png` | Sepolia Etherscan contract |
| `04-credentials-revoke.png` | Issued + revoked credentials |
| `05-pinata-files.png` | Pinata pinned files |
| `06-tamper-detection.png` | TAMPERED document result |
| `07-ai-threats.png` | AI threat table |
| `08-ledger-merkle.png` | Transaction log + Merkle root |
| `09-dashboard-overview.png` | Web dashboard — Overview |
| `10-dashboard-wallets.png` | Web dashboard — Wallets |
| `11-dashboard-credentials.png` | Web dashboard — Credentials |
| `12-dashboard-threats.png` | Web dashboard — Threat Intel |
| `13-dashboard-ledger.png` | Web dashboard — Audit Ledger |
| `14-verify-valid.png` | Verify ID=1 → VALID |
| `15-verify-revoked.png` | Verify ID=2 → REVOKED |
| `16-metamask-sepolia.png` | MetaMask Sepolia (optional) |

## How to capture dashboard screenshots

1. Run `python server.py`
2. Open http://127.0.0.1:5000
3. Press **Win + Shift + S** → save PNG here
4. Run sync script + push (steps above)
