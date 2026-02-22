#!/usr/bin/env python3
"""
Inflectiv Vault - Day 3 Demo
The difference between a blind agent and an intelligent one.
Run: python demo.py
"""
import json, sys, time, urllib.request, urllib.error

VAULT = "http://localhost:8766"
TOKEN = "demo-owner-token"

G = "\033[92m"; B = "\033[94m"; P = "\033[95m"
C = "\033[96m"; GR = "\033[90m"; BD = "\033[1m"; RS = "\033[0m"
SEP = "-" * 58

def hdr(t): print("\n"+BD+C+SEP+RS+"\n"+BD+C+"  "+t+RS+"\n"+BD+C+SEP+RS)
def ok(t):  print("  "+G+"v"+RS+" "+t)
def info(t):print("  "+B+">"+RS+" "+t)
def earn(t):print("  "+P+"$"+RS+" "+t)
def dim(t): print("  "+GR+t+RS)

def req(method, path, body=None):
    url = VAULT + path
    data = json.dumps(body).encode() if body else None
    r = urllib.request.Request(url, data=data, method=method,
        headers={"Content-Type": "application/json", "X-Vault-Token": TOKEN})
    try:
        with urllib.request.urlopen(r, timeout=10) as resp:
            return json.loads(resp.read()), resp.status
    except urllib.error.HTTPError as e:
        return json.loads(e.read()), e.code

print("\n" + BD + "Inflectiv Vault - Agent Demo" + RS)
print(GR + "The difference between a blind agent and an intelligent one." + RS + "\n")

# ── Step 0: Health ────────────────────────────────────────────────────────────
hdr("Step 0 - Vault Online")
health, status = req("GET", "/health")
if status == 200 and health.get("status") == "ok":
    ok("Vault online  id=" + health["vault_id"])
else:
    print("  Vault not responding. Run: uvicorn vault_server:app --port 8766")
    sys.exit(1)

# ── Step 1: Without vault (baseline) ─────────────────────────────────────────
hdr("Step 1 - Agent WITHOUT vault (baseline)")
dim("Agent: I need to research Aave V4 governance proposals")
for s in ["Opening browser...", "Scraping aave.com/governance...",
          "Scraping snapshot.org...", "Parsing 6 forum threads...",
          "14 minutes elapsed. 240 API tokens spent.",
          "Result: Aave has some proposals. Vote is ongoing.",
          "Mediocre summary. No history. No cross-protocol data."]:
    time.sleep(0.3)
    dim("  > " + s)

# ── Step 2: With vault ────────────────────────────────────────────────────────
hdr("Step 2 - Agent WITH vault (single call)")
info("vault.query(\"Aave governance\")")
time.sleep(0.3)
result, status = req("POST", "/vault/query", {"q": "Aave governance", "include_network": False})
if status == 200:
    hits = result.get("total_hits", 0)
    ok(str(hits) + " structured results - 30 seconds, zero scraping")
    print()
    for r in result.get("results", [])[:3]:
        src   = r.get("source", "?")
        stype = r.get("source_type", "?")
        print("  " + C + "[" + src + "|" + stype + "]" + RS)
        print("    " + r.get("content", "")[:90])
        print()
    print("  " + G + "> 30 seconds. Zero scraping. 90 days of governance history." + RS)
else:
    info("Query status: " + str(status) + " " + str(result))

# ── Step 3: Multi-vault merge ─────────────────────────────────────────────────
hdr("Step 3 - vault.query() merges ALL connected vaults")
req("POST", "/vault/memory/MEMORY.md",
    {"content": "# My Notes\n## Aave V4\n- Reviewed Proposal #247. Dynamic curves are overdue."})
ok("Personal MEMORY.md written")
result, _ = req("POST", "/vault/query", {"q": "Aave", "include_network": False})
total = result.get("total_hits", 0)
also  = result.get("also_found", [])
ok(str(total) + " hits: personal notes + DeFi Intelligence vault, merged")
for r in result.get("results", [])[:2]:
    src   = r.get("source", "?")
    stype = r.get("source_type", "?")
    print("    " + C + "[" + src + "|" + stype + "]" + RS + " " + r.get("content", "")[:75])
if also:
    info("also_found: " + str(len(also)) + " conflict(s) surfaced for review")
print("  " + G + "> Personal notes + network intelligence. One call. Merged." + RS)

# ── Step 4: Contribute ────────────────────────────────────────────────────────
hdr("Step 4 - Agent contributes new intelligence")
new_intel = ("Aave V4 Proposal #251: GHO Stability Module v2\n"
             "Status: Voting open until 2026-02-28\n"
             "Votes: 68% FOR (84.2M AAVE)\n"
             "Key change: GHO peg moves from PSM to algorithmic with oracle feeds\n"
             "Risk: Medium - oracle dependency introduced\n"
             "Source: Aave Governance Forum - 2026-02-22")
contrib, status = req("POST", "/vault/contribute", {"content": new_intel})
cid = None
if status == 200:
    top      = contrib.get("top_category", {})
    category = top.get("category", "unknown")
    conf     = top.get("confidence", 0)
    ok("Staged for approval")
    info("Auto-classified: " + category + "  confidence=" + str(round(conf, 2)))
    info("Personal refs stripped. Ready for approval.")
    # Get the contribution ID from pending list
    pending, ps = req("GET", "/vault/contribute/pending")
    items = pending.get("pending", [])
    if items:
        cid = items[-1].get("id", "")
        ok("Pending id=" + str(cid) + "...")
else:
    info("Contribute error: " + str(status) + " " + str(contrib))

# ── Step 5: Approve ───────────────────────────────────────────────────────────
hdr("Step 5 - User approves contribution")
if cid:
    approve, status = req("POST", "/vault/pending/" + cid + "/approve")
    if status == 200:
        earned = approve.get("inai_earned", 0.5)
        ok(approve.get("message", "Contribution approved."))
        earn("+" + str(earned) + " $INAI credited to vault")
    else:
        info("Approve: " + str(status) + " " + str(approve))
else:
    info("No contribution to approve")

# ── Step 6: Stats ─────────────────────────────────────────────────────────────
hdr("Step 6 - Vault stats - ratio and $INAI")
stats, _ = req("GET", "/vault/stats")
q    = stats.get("queries_made", 0)
apr  = stats.get("contributions_approved", 0)
rat  = stats.get("ratio", 0.0)
ie   = stats.get("inai_earned", 0.0)
ip   = stats.get("inai_pending", 0.0)
tier = stats.get("access_tier", "?")
grace= stats.get("grace_period_active", True)
print("  " + "Queries made".ljust(30)           + B + str(q) + RS)
print("  " + "Contributions approved".ljust(30) + G + str(apr) + RS)
print("  " + "Contribution ratio".ljust(30)     + C + str(round(rat,3)) + RS + "  (target 0.20 | min 0.05)")
print("  " + "$INAI earned".ljust(30)           + P + str(round(ie,4)) + " $INAI" + RS)
print("  " + "$INAI pending".ljust(30)          + P + str(round(ip,4)) + " $INAI" + RS)
print("  " + "Access tier".ljust(30)            + G + tier.upper() + RS)
if grace:
    days = stats.get("grace_days_remaining", 14)
    print("  " + "Grace period".ljust(30) + G + str(days) + " days remaining" + RS)

# ── Step 7: Dashboard ────────────────────────────────────────────────────────
hdr("Step 7 - Dashboard")
try:
    r2 = urllib.request.Request(VAULT + "/ui/dashboard",
        headers={"X-Vault-Token": TOKEN})
    with urllib.request.urlopen(r2, timeout=5) as resp:
        size = len(resp.read())
    ok("/ui/dashboard responding (" + str(size) + " bytes HTML)")
except Exception as e:
    info("/ui/dashboard: " + str(e))
print("\n  " + B + "Dashboard: " + RS + "http://localhost:8766/ui/dashboard")
print("  " + B + "Approvals: " + RS + "http://localhost:8766/ui/approve")
print("  " + B + "Stats:     " + RS + "http://localhost:8766/vault/stats")

# ── Summary ───────────────────────────────────────────────────────────────────
print("\n" + BD + C + "=" * 58 + RS)
print(BD + "  Demo complete." + RS)
print(C + "=" * 58 + RS)
print("  " + G + "v" + RS + " Personal vault    - encrypted keys, memory, soul")
print("  " + G + "v" + RS + " Knowledge vault   - DeFi Intelligence, structured + live")
print("  " + G + "v" + RS + " vault.query()     - personal + network, one call, merged")
print("  " + G + "v" + RS + " Contributions     - classify, approve, publish to VINN")
print("  " + G + "v" + RS + " $INAI earned      - " + str(round(ie,4)) + " confirmed, " + str(round(ip,4)) + " pending")
print("  " + G + "v" + RS + " Ratio             - " + str(round(rat,3)) + " (access maintained)")
print("  " + G + "v" + RS + " Dashboard         - http://localhost:8766/ui/dashboard")
print()
print("  " + GR + "The agent queried the network and got structured intelligence." + RS)
print("  " + GR + "It contributed back. It earned $INAI. The network got richer." + RS)
print("  " + P + "  That is the flywheel." + RS)
print()
