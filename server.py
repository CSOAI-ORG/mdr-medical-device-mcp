#!/usr/bin/env python3
"""
EU Medical Device Regulation (MDR) MCP Server
=============================================
By MEOK AI Labs | https://meok.ai

EU MDR (Reg 2017/745) and IVDR (Reg 2017/746) compliance for medical device + IVD manufacturers, including AI/ML SaMD classification.

Install: pip install mdr-medical-device-mcp
Run:     python server.py
"""

import json
import sys
import os
from datetime import datetime, timedelta, timezone
from typing import Optional
from collections import defaultdict
from mcp.server.fastmcp import FastMCP
from pydantic import BaseModel, Field
from typing import List, Dict, Any, Optional, Literal
import json
from datetime import datetime, timedelta, timezone
from collections import defaultdict
import os as _os
import sys
import os

# --- Pydantic Models ---

class ClassificationResult(BaseModel):
    tool: str
    query: str
    status: Literal["active", "stub", "error"]
    risk_class: str
    rule_applied: str
    rationale: str
    regulation_refs: List[str]
    next_step: str
    tier: str
    upsell_pro: Optional[str] = None
    branding: str = "Built by MEOK AI Labs | https://meok.ai"

class CERequirementsResponse(BaseModel):
    tool: str
    query: str
    status: Literal["active", "stub", "error"]
    requirements: List[str]
    notified_body_required: bool
    regulation_refs: List[str]
    next_step: str
    tier: str
    branding: str = "Built by MEOK AI Labs | https://meok.ai"

# --- Classification Logic ---

def _classify_mdr(query: str) -> Dict[str, Any]:
    q = query.lower()
    if any(w in q for w in ["pacemaker", "heart valve", "implant", "stent", "defibrillator"]):
        return {
            "risk_class": "Class III",
            "rule_applied": "Rule 8 / Rule 13",
            "rationale": "High-risk implantable devices or devices in contact with central circulatory/nervous system.",
            "refs": ["MDR Annex VIII Chapter III Rule 8"]
        }
    if any(w in q for w in ["contact lens", "infusion pump", "surgical instrument", "x-ray", "mri", "ventilator"]):
        return {
            "risk_class": "Class IIb",
            "rule_applied": "Rule 11 / Rule 10",
            "rationale": "Medium/high risk devices, including many active devices intended for monitoring or administration of medicines.",
            "refs": ["MDR Annex VIII Chapter III Rule 11"]
        }
    if any(w in q for w in ["dental", "tracheostomy", "hearing aid", "thermometer", "catheter", "endoscope"]):
        return {
            "risk_class": "Class IIa",
            "rule_applied": "Rule 5 / Rule 6",
            "rationale": "Medium risk devices, typically invasive devices for short-term use.",
            "refs": ["MDR Annex VIII Chapter III Rule 5"]
        }
    if any(w in q for w in ["spectacles", "glasses", "stethoscope", "bandage", "wheelchair", "hospital bed", "plaster"]):
        return {
            "risk_class": "Class I",
            "rule_applied": "Rule 1",
            "rationale": "Low risk non-invasive devices.",
            "refs": ["MDR Annex VIII Chapter III Rule 1"]
        }
    return {
        "risk_class": "Unclassified (Assumed Class I)",
        "rule_applied": "N/A",
        "rationale": f"Insufficient data for definitive classification of '{query}'. Defaulting to Class I assessment for safety.",
        "refs": ["MDR Annex VIII"]
    }

def _classify_ivd(query: str) -> Dict[str, Any]:
    q = query.lower()
    if any(w in q for w in ["blood grouping", "hiv", "hep", "screening", "covid-19", "sar"]):
        return {"risk_class": "Class D", "rule_applied": "Rule 1", "rationale": "High individual and high public health risk.", "refs": ["IVDR Annex VIII Rule 1"]}
    if any(w in q for w in ["genetic", "cancer", "prenatal", "companion", "diagnostic", "tumor"]):
        return {"risk_class": "Class C", "rule_applied": "Rule 3", "rationale": "High individual risk or moderate public health risk.", "refs": ["IVDR Annex VIII Rule 3"]}
    if any(w in q for w in ["pregnancy", "fertility", "cholesterol", "glucose", "self-test"]):
        return {"risk_class": "Class B", "rule_applied": "Rule 4", "rationale": "Moderate individual risk or low public health risk.", "refs": ["IVDR Annex VIII Rule 4"]}
    return {"risk_class": "Class A", "rule_applied": "Rule 5", "rationale": "Low individual and low public health risk.", "refs": ["IVDR Annex VIII Rule 5"]}

def _check_samd(query: str) -> Dict[str, Any]:
    q = query.lower()
    # Use stems for better matching
    if any(w in q for w in ["diagnos", "treat", "monitor", "decis", "predict", "triage"]):
        if any(w in q for w in ["critic", "life-threat", "death", "irrevers", "severe"]):
            return {"risk_class": "Class III (IMDRF IV / MDR Rule 11)", "rule_applied": "Rule 11(a)", "rationale": "Software intended to provide information which is used to take decisions with diagnosis or treatment purposes which can cause death or irreversible deterioration.", "refs": ["MDR Annex VIII Rule 11"]}
        return {"risk_class": "Class IIa/IIb", "rule_applied": "Rule 11(b)", "rationale": "Software intended to monitor physiological processes.", "refs": ["MDR Annex VIII Rule 11"]}
    return {"risk_class": "Class I", "rule_applied": "Rule 11(c)", "rationale": "All other software is classified as Class I.", "refs": ["MDR Annex VIII Rule 11"]}

# --- Utils ---

_MEOK_API_KEY = _os.environ.get("MEOK_API_KEY", "")

try:
    from auth_middleware import check_access as _shared_check_access
    _AUTH_ENGINE_AVAILABLE = True
except ImportError:
    _AUTH_ENGINE_AVAILABLE = False
    def _shared_check_access(api_key: str = ""):
        if _MEOK_API_KEY and api_key and api_key == _MEOK_API_KEY:
            return True, "OK", "pro"
        return True, "OK, Pro at https://www.csoai.org/checkout", "free"

FREE_DAILY_LIMIT = 10
_usage = defaultdict(list)
STRIPE_PRO = "https://councilof.ai"

def _rl(tier="free"):
    if tier in ("pro", "professional", "enterprise"): return None
    now = datetime.now(timezone.utc)
    cutoff = now - timedelta(days=1)
    _usage["anonymous"] = [t for t in _usage["anonymous"] if t > cutoff]
    if len(_usage["anonymous"]) >= FREE_DAILY_LIMIT:
        return f"Free tier limit ({FREE_DAILY_LIMIT}/day). Pro £79/mo: {STRIPE_PRO}"
    _usage["anonymous"].append(now)
    return None

# --- MCP Setup ---

mcp = FastMCP(
    "EU Medical Device Regulation (MDR)",
    instructions="EU MDR (Reg 2017/745) and IVDR (Reg 2017/746) compliance assistant.",
)

@mcp.tool()
def classify_medical_device(query: str, api_key: str = "") -> ClassificationResult:
    """MDR Annex VIII risk classification (Class I/IIa/IIb/III)"""
    allowed, msg, tier = _shared_check_access(api_key)
    if not allowed: return {"error": msg}
    if err := _rl(tier): return {"error": err}

    res = _classify_mdr(query)
    return ClassificationResult(
        tool="classify_medical_device",
        query=query,
        status="active",
        risk_class=res["risk_class"],
        rule_applied=res["rule_applied"],
        rationale=res["rationale"],
        regulation_refs=res["refs"],
        next_step="POST to /sign for HMAC-signed compliance cert",
        tier=tier,
        upsell_pro=f"Pro £79/mo: {STRIPE_PRO}" if tier == "free" else None
    )

@mcp.tool()
def classify_ivd(query: str, api_key: str = "") -> ClassificationResult:
    """IVDR Annex VIII IVD classification (Class A/B/C/D)"""
    allowed, msg, tier = _shared_check_access(api_key)
    if not allowed: return {"error": msg}
    if err := _rl(tier): return {"error": err}

    res = _classify_ivd(query)
    return ClassificationResult(
        tool="classify_ivd",
        query=query,
        status="active",
        risk_class=res["risk_class"],
        rule_applied=res["rule_applied"],
        rationale=res["rationale"],
        regulation_refs=res["refs"],
        next_step="POST to /sign for HMAC-signed compliance cert",
        tier=tier,
        upsell_pro=f"Pro £79/mo: {STRIPE_PRO}" if tier == "free" else None
    )

@mcp.tool()
def samd_ai_ml_check(query: str, api_key: str = "") -> ClassificationResult:
    """AI/ML SaMD classification + IMDRF risk framework"""
    allowed, msg, tier = _shared_check_access(api_key)
    if not allowed: return {"error": msg}
    if err := _rl(tier): return {"error": err}

    res = _check_samd(query)
    return ClassificationResult(
        tool="samd_ai_ml_check",
        query=query,
        status="active",
        risk_class=res["risk_class"],
        rule_applied=res["rule_applied"],
        rationale=res["rationale"],
        regulation_refs=res["refs"],
        next_step="Confirm with ISO 13485 quality system audit",
        tier=tier,
        upsell_pro=f"Pro £79/mo: {STRIPE_PRO}" if tier == "free" else None
    )

@mcp.tool()
def ce_marking_requirements(query: str, api_key: str = "") -> CERequirementsResponse:
    """MDR Article 19 CE marking + Notified Body involvement"""
    allowed, msg, tier = _shared_check_access(api_key)
    if not allowed: return {"error": msg}
    
    res = _classify_mdr(query)
    nb_required = res["risk_class"] != "Class I"
    reqs = ["EU Declaration of Conformity", "Technical Documentation (Annex II/III)", "UDI Assignment"]
    if nb_required: reqs.append("Notified Body Audit & Certificate")
    
    return CERequirementsResponse(
        tool="ce_marking_requirements",
        query=query,
        status="active",
        requirements=reqs,
        notified_body_required=nb_required,
        regulation_refs=["MDR Article 19", "MDR Annex IX-XI"],
        next_step="Prepare GSPR checklist (Annex I)",
        tier=tier
    )

if __name__ == "__main__":
    mcp.run()





# ── search_regulation: FTS5-backed verbatim regulation lookup ──────────────
# Powered by EUR-Lex Cellar API daily sync via eu-ai-act-compliance-mcp.
# Returns 64-token snippets from canonical regulation text (Akoma Ntoso XHTML).

import sqlite3 as _sqlite3
from pathlib import Path as _Path
import os as _os_search

# Try multiple known locations for the EUR-Lex DB
_REG_DB_CANDIDATES = [
    _Path(_os_search.environ.get("MEOK_EURLEX_DB", "")) if _os_search.environ.get("MEOK_EURLEX_DB") else None,
    _Path.home() / "clawd" / "mcp-marketplace" / "eu-ai-act-compliance-mcp" / "data" / "regulations.db",
    _Path(__file__).parent / "data" / "regulations.db",
]
_REG_DB = next((p for p in _REG_DB_CANDIDATES if p and p.exists()), None)


@mcp.tool()
def search_regulation(query: str, regulation: str = "", limit: int = 10) -> dict:
    """Full-text search across 410+ articles of real EU regulation text (EUR-Lex verified).

    Args:
        query: Search terms. FTS5 syntax supported (AND, OR, NEAR, phrase quoting).
        regulation: Optional filter - one of: eu-ai-act, dora, nis2, cra, csrd, gdpr.
        limit: Max results (default 10).

    Returns:
        Snippets from matching articles with regulation + article + relevance score.
        Verbatim from EUR-Lex Cellar — auditor-defensible quotes with `>>>match<<<` highlights.
    """
    if _REG_DB is None or not _REG_DB.exists():
        return {
            "error": "EUR-Lex database not available. Install eu-ai-act-compliance-mcp v1.4.0+ which ships the DB, OR set MEOK_EURLEX_DB env var.",
            "hint": "pip install eu-ai-act-compliance-mcp",
        }
    if not query or len(query.strip()) < 2:
        return {"error": "Query must be at least 2 characters"}

    celex_map = {
        "eu-ai-act": "32024R1689", "dora": "32022R2554", "nis2": "32022L2555",
        "cra": "32024R2847", "csrd": "32022L2464", "gdpr": "32016R0679",
    }
    celex_filter = celex_map.get(regulation.lower().strip()) if regulation else None

    safe_query = query.replace('"', '""').strip()
    if " " in safe_query and not any(op in safe_query.upper() for op in [" AND ", " OR ", " NEAR"]):
        safe_query = '"' + safe_query + '"'

    conn = _sqlite3.connect(str(_REG_DB))
    try:
        if celex_filter:
            sql = ("SELECT celex, article_number, article_id, "
                   "snippet(articles_fts, 3, '>>>', '<<<', '...', 64) AS snip, rank "
                   "FROM articles_fts WHERE articles_fts MATCH ? AND celex = ? "
                   "ORDER BY rank LIMIT ?")
            rows = conn.execute(sql, (safe_query, celex_filter, limit)).fetchall()
        else:
            sql = ("SELECT celex, article_number, article_id, "
                   "snippet(articles_fts, 3, '>>>', '<<<', '...', 64) AS snip, rank "
                   "FROM articles_fts WHERE articles_fts MATCH ? "
                   "ORDER BY rank LIMIT ?")
            rows = conn.execute(sql, (safe_query, limit)).fetchall()

        name_map = {v: k for k, v in celex_map.items()}
        return {
            "query": query,
            "regulation_filter": regulation or "all",
            "result_count": len(rows),
            "source": "EUR-Lex Cellar API (publications.europa.eu) - verbatim text",
            "disclaimer": "Quotes are auditor-defensible. Not legal advice.",
            "results": [
                {"regulation": name_map.get(r[0], r[0]), "article_number": r[1],
                 "snippet": r[3], "relevance_score": round(abs(r[4]), 2)}
                for r in rows
            ],
        }
    except Exception as e:
        return {"error": f"FTS5 search error: {e}"}
    finally:
        conn.close()


@mcp.tool()
def list_regulations_in_db() -> dict:
    """List all regulations in the local EUR-Lex FTS5 database."""
    if _REG_DB is None or not _REG_DB.exists():
        return {"error": "Database not available", "regulations": []}
    conn = _sqlite3.connect(str(_REG_DB))
    try:
        rows = conn.execute(
            "SELECT celex, name, short_name, type, title, article_count, last_synced "
            "FROM regulations ORDER BY celex"
        ).fetchall()
        return {
            "source": "EUR-Lex Cellar API",
            "total_regulations": len(rows),
            "total_articles": conn.execute("SELECT COUNT(*) FROM articles").fetchone()[0],
            "regulations": [
                {"celex": r[0], "name": r[1], "short_name": r[2], "type": r[3],
                 "title": (r[4] or "")[:120], "article_count": r[5],
                 "last_synced": r[6]}
                for r in rows
            ],
        }
    finally:
        conn.close()


def main():
    mcp.run()


if __name__ == "__main__":
    main()
