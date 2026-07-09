const API = "";
const VIEW_TITLES = {
  overview: "System Overview",
  wallets: "Wallet Identities",
  credentials: "Issued Credentials",
  security: "Threat Intelligence",
  ledger: "Audit Ledger",
  verify: "Degree Verification",
  documents: "IPFS Document Vault",
};

const ROLE_EMOJI = { Registrar: "🏛", Student: "🎓", Employer: "🏢" };
const ROLE_CLASS = { Registrar: "registrar", Student: "student", Employer: "employer" };

let sessionToken = "";
let lastData = null;

function $(id) { return document.getElementById(id); }

function truncate(str, n = 18) {
  if (!str) return "—";
  return str.length > n ? str.slice(0, n) + "…" : str;
}

function toast(msg, type = "success") {
  const el = document.createElement("div");
  el.className = `toast ${type}`;
  el.textContent = msg;
  $("toastContainer").appendChild(el);
  setTimeout(() => el.remove(), 4200);
}

function switchView(viewId) {
  document.querySelectorAll(".view").forEach(v => v.classList.remove("active"));
  document.querySelectorAll(".nav-item").forEach(n => n.classList.remove("active"));
  $(`view-${viewId}`)?.classList.add("active");
  document.querySelector(`[data-view="${viewId}"]`)?.classList.add("active");
  $("pageTitle").textContent = VIEW_TITLES[viewId] || "Dashboard";
}

document.querySelectorAll(".nav-item").forEach(btn => {
  btn.addEventListener("click", () => switchView(btn.dataset.view));
});
$("goVerifyBtn")?.addEventListener("click", () => switchView("verify"));

async function fetchDashboard() {
  const res = await fetch(`${API}/api/dashboard`);
  if (!res.ok) throw new Error("Dashboard not ready");
  return res.json();
}

function renderOverview(data) {
  const addr = data.contract_info?.address || "—";
  $("overviewContract").textContent = addr;
  $("statContract").textContent = truncate(addr, 22);
  $("statMerkle").textContent = data.merkle_root || "—";

  const link = $("etherscanLink");
  if (addr && addr.startsWith("0x")) {
    link.href = `https://sepolia.etherscan.io/address/${addr}`;
    link.style.display = "inline";
  } else {
    link.style.display = "none";
  }

  const broken = (data.chain_verification || []).some(c => c.status === "BROKEN");
  $("statChain").innerHTML = broken
    ? '<span style="color:var(--rose)">BROKEN</span>'
    : '<span style="color:var(--sage)">✓ VALID</span>';

  $("statAI").textContent = data.ai_accuracy != null ? `${data.ai_accuracy}%` : "—";
  $("trainingSize").textContent = `${data.training_size || 0} training samples`;

  const creds = data.credentials || [];
  $("credCount").textContent = creds.length;
  const highs = (data.threat_feed || []).filter(t => t.threat_level === "HIGH").length;
  $("threatCount").textContent = highs;

  const tags = $("merkleTags");
  const proof = data.merkle_proof_valid ? "Proof: VALID" : "Proof: INVALID";
  tags.innerHTML = `
    <span class="tag">${proof}</span>
    ${data.tamper_flag ? '<span class="tag" style="background:var(--rose-bg);color:var(--rose)">Tamper demo active</span>' : ""}
    <span class="tag">${(data.transaction_chain || []).length} transactions</span>
  `;

  $("networkBadge").textContent = (data.network_label || "LOCAL").toUpperCase();
  $("lastSync").textContent = new Date().toLocaleTimeString();
}

function renderWallets(data) {
  const grid = $("identitiesGrid");
  const rows = data.identities || [];
  if (!rows.length) {
    grid.innerHTML = '<div class="empty-msg">No wallet identities loaded</div>';
    return;
  }
  grid.innerHTML = rows.map(i => `
    <div class="wallet-card ${ROLE_CLASS[i.role] || ""}">
      <div class="wallet-avatar">${ROLE_EMOJI[i.role] || "👤"}</div>
      <h4>${i.role}</h4>
      <span class="role-tag">ECDSA Wallet</span>
      <p class="wallet-addr">${i.wallet_address}</p>
      <span class="session-pill ${i.session_status === "ACTIVE" ? "on" : "off"}">
        ${i.session_status === "ACTIVE" ? "● Session Active" : "○ Inactive"}
      </span>
    </div>
  `).join("");

  const perms = data.role_permissions || {};
  $("permissionsBox").innerHTML = `
    <h3>Role Permission Matrix</h3>
    ${Object.entries(perms).map(([role, p]) => `
      <div class="perm-row">
        <span class="perm-role">${role}</span>
        <span>${p.join(" · ")}</span>
      </div>
    `).join("")}
  `;
}

function renderCredentials(data) {
  const grid = $("credentialsGrid");
  const rows = data.credentials || [];
  if (!rows.length) {
    grid.innerHTML = '<div class="empty-msg">No credentials on chain yet</div>';
    return;
  }
  grid.innerHTML = rows.map(c => `
    <div class="cred-card ${c.status === "REVOKED" ? "revoked" : ""}">
      <div class="cred-header">
        <div class="cred-id">Credential #${c.credential_id}</div>
        <div class="cred-name">${c.student_name}</div>
      </div>
      <div class="cred-body">
        <div class="cred-row"><label>Registrar</label><span class="mono">${truncate(String(c.registrar), 24)}</span></div>
        <div class="cred-row"><label>Network</label><span>${(data.network_label || "ethereum").toUpperCase()}</span></div>
        <span class="status-ribbon ${c.status === "VALID" ? "valid" : "revoked"}">${c.status}</span>
      </div>
    </div>
  `).join("");
}

function renderThreats(data) {
  const feed = $("threatsFeed");
  const rows = data.threat_feed || [];
  if (!rows.length) {
    feed.innerHTML = '<div class="empty-msg">No threat events recorded</div>';
    return;
  }
  const icons = { HIGH: "🔴", MEDIUM: "🟡", LOW: "🟢" };
  feed.innerHTML = rows.slice(0, 12).map(t => {
    const lvl = (t.threat_level || "LOW").toLowerCase();
    const pct = Math.min(100, (t.confidence || 0) * 100);
    return `
    <div class="alert-card ${lvl}">
      <span class="alert-icon">${icons[t.threat_level] || "⚪"}</span>
      <div class="alert-body">
        <strong>${t.tx_id}</strong> — ${t.threat_level} threat
        <p class="alert-reason">${t.reason || ""}</p>
        <div class="alert-meta">
          <div class="confidence-bar"><div class="confidence-fill ${lvl}" style="width:${pct}%"></div></div>
          <small>${pct.toFixed(0)}% confidence</small>
        </div>
      </div>
    </div>`;
  }).join("");
}

function renderLedger(data) {
  const txs = data.transaction_chain || [];
  const ver = data.chain_verification || [];

  $("ledgerSummary").innerHTML = `
    <div class="summary-box"><label>Merkle Root</label><p>${data.merkle_root || "—"}</p></div>
    <div class="summary-box"><label>Tampered Root</label><p>${data.tampered_merkle_root || "—"}</p></div>
    <div class="summary-box"><label>Transactions</label><p>${txs.length} logged events</p></div>
    <div class="summary-box"><label>Proof Status</label><p>${data.merkle_proof_valid ? "✓ VALID" : "✗ INVALID"}</p></div>
  `;

  const tl = $("chainTimeline");
  if (!txs.length) {
    tl.innerHTML = '<div class="empty-msg">No ledger entries</div>';
    return;
  }
  tl.innerHTML = txs.slice(0, 15).map((tx, i) => {
    const st = ver[i]?.status || "—";
    return `
    <div class="tl-item ${st === "BROKEN" ? "broken" : ""}">
      <div class="tl-head">
        <span class="tl-id">${tx.tx_id}</span>
        <span class="tl-action">${tx.action}</span>
      </div>
      <div class="tl-hash">${truncate(tx.payload_hash, 32)} · ${st}</div>
    </div>`;
  }).join("");
}

function renderDocuments(data) {
  const list = $("documentsList");
  const docs = data.documents || [];
  if (!docs.length) {
    list.innerHTML = '<div class="empty-msg">No IPFS documents pinned</div>';
    return;
  }
  list.innerHTML = docs.map(d => `
    <div class="doc-card">
      <div class="doc-icon">📜</div>
      <h4>${d.filename}</h4>
      <p class="cid">SHA-256: ${d.cid}</p>
      ${d.pinata_ipfs_hash ? `<p class="cid">IPFS: ${d.pinata_ipfs_hash}</p>` : ""}
      ${d.pinata_url ? `<a href="${d.pinata_url}" target="_blank" rel="noopener">Open on Pinata ↗</a>` : ""}
    </div>
  `).join("");
}

function renderVerifyResults(data) {
  const container = $("verifyResults");
  const results = data.verify_results || [];
  if (!results.length) {
    container.innerHTML = "";
    return;
  }
  container.innerHTML = `<p style="font-size:0.78rem;color:var(--ink-muted);margin-bottom:8px">Recent verifications</p>` +
    results.map(r => `
    <div class="history-item ${r.result.toLowerCase()}">
      <strong>#${r.credential_id}</strong>
      <span style="font-weight:700;color:${r.result === "VALID" ? "var(--sage)" : "var(--rose)"}">${r.result}</span>
      <span style="color:var(--ink-muted);font-size:0.82rem">${truncate(r.details, 45)}</span>
    </div>
  `).join("");
}

function setVerifyVisual(result) {
  const ring = $("verifyRing");
  const icon = $("verifyIcon");
  const text = $("verifyStatusText");
  if (!ring) return;
  ring.className = "verify-ring";
  if (result === "VALID") {
    ring.classList.add("valid");
    icon.textContent = "✓";
    text.textContent = "Credential Verified";
  } else if (result === "REVOKED" || result === "FORGED") {
    ring.classList.add("revoked");
    icon.textContent = "✗";
    text.textContent = result === "FORGED" ? "Document Forged" : "Credential Revoked";
  } else if (result === "pending") {
    ring.classList.add("pending");
    icon.textContent = "";
    text.textContent = "Verifying…";
  } else {
    icon.textContent = "?";
    text.textContent = "Awaiting verification";
  }
}

async function loadDashboard() {
  try {
    const data = await fetchDashboard();
    lastData = data;
    renderOverview(data);
    renderWallets(data);
    renderCredentials(data);
    renderThreats(data);
    renderLedger(data);
    renderDocuments(data);
    renderVerifyResults(data);
    if (data.employer_session_token) sessionToken = data.employer_session_token;
    const loader = document.getElementById("bootLoader");
    if (loader) loader.classList.add("hidden");
  } catch {
    const loader = document.getElementById("bootLoader");
    if (loader) {
      loader.querySelector("p").textContent = "Still starting backend — wait for terminal to finish…";
    }
    toast("Backend initializing — please wait…", "error");
  }
}

async function demoLogin(role) {
  const res = await fetch(`${API}/api/demo-login`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ role }),
  });
  const data = await res.json();
  if (!res.ok) throw new Error(data.error || "Login failed");
  sessionToken = data.session_token;
  return data;
}

async function verifyCredential() {
  const credId = parseInt($("credentialId").value, 10);
  const role = $("loginRole").value;
  if (!credId) { toast("Please enter a credential ID", "error"); return; }

  $("verifyBtn").disabled = true;
  setVerifyVisual("pending");
  try {
    await demoLogin(role);
    const res = await fetch(`${API}/api/verify-credential`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ session_token: sessionToken, credential_id: credId }),
    });
    const data = await res.json();
    const result = data.result || "ERROR";
    setVerifyVisual(result);
    toast(
      result === "VALID" ? `✓ Credential #${credId} is VALID` : `✗ Credential #${credId}: ${result}`,
      result === "VALID" ? "success" : "error"
    );
    await loadDashboard();
  } catch (e) {
    setVerifyVisual("idle");
    toast(e.message || "Verification failed", "error");
  } finally {
    $("verifyBtn").disabled = false;
  }
}

$("verifyBtn").addEventListener("click", verifyCredential);
$("refreshBtn").addEventListener("click", () => { loadDashboard(); toast("Data synchronized"); });

loadDashboard();
setInterval(loadDashboard, 15000);
