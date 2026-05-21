import streamlit as st
import requests
import json
import os
import re
from openai import OpenAI

# ── Page config ──────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="Obligo GTM Agent",
    page_icon="🏢",
    layout="wide"
)

# ── Styling ───────────────────────────────────────────────────────────────────
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=IBM+Plex+Mono:wght@400;500&family=Syne:wght@500;600;700&display=swap');

html, body, [class*="css"] { font-family: 'Syne', sans-serif; }

.agent-header {
    background: #1a3a5c;
    color: white;
    padding: 2rem 2.5rem;
    border-radius: 12px;
    margin-bottom: 2rem;
}
.agent-header h1 { font-size: 1.6rem; font-weight: 700; margin: 0; letter-spacing: -0.02em; }
.agent-header p  { font-size: 0.8rem; opacity: 0.6; margin: 6px 0 0; font-family: 'IBM Plex Mono', monospace; }

.step-card {
    background: white;
    border: 1px solid #e4e2db;
    border-radius: 10px;
    padding: 1.25rem 1.5rem;
    margin-bottom: 1rem;
}
.step-label {
    font-family: 'IBM Plex Mono', monospace;
    font-size: 0.65rem;
    text-transform: uppercase;
    letter-spacing: 0.08em;
    color: #6b6860;
    margin-bottom: 0.5rem;
}
.score-big {
    font-size: 3rem;
    font-weight: 700;
    line-height: 1;
}
.score-good  { color: #1a6b3c; }
.score-mid   { color: #b8600a; }
.score-low   { color: #c0392b; }

.email-box {
    background: #f7f6f3;
    border: 1px solid #e4e2db;
    border-radius: 8px;
    padding: 1.25rem;
    font-size: 0.85rem;
    line-height: 1.7;
    white-space: pre-wrap;
    font-family: inherit;
}
.hs-success {
    background: #edf7f2;
    border: 1px solid #a8dcc0;
    border-radius: 8px;
    padding: 1rem 1.25rem;
    color: #1a6b3c;
    font-size: 0.85rem;
}
.hs-error {
    background: #fdf0ee;
    border: 1px solid #f0b8b3;
    border-radius: 8px;
    padding: 1rem 1.25rem;
    color: #c0392b;
    font-size: 0.85rem;
}
.tag {
    display: inline-block;
    font-family: 'IBM Plex Mono', monospace;
    font-size: 0.65rem;
    padding: 3px 8px;
    border-radius: 4px;
    margin: 2px;
    font-weight: 500;
}
.tag-blue   { background: #e8eef5; color: #1a3a5c; }
.tag-green  { background: #edf7f2; color: #1a6b3c; }
.tag-orange { background: #fef6ec; color: #b8600a; }
.tag-red    { background: #fdf0ee; color: #c0392b; }

.reasoning-box {
    background: #f7f6f3;
    border-left: 3px solid #1a3a5c;
    padding: 0.75rem 1rem;
    font-size: 0.8rem;
    color: #6b6860;
    line-height: 1.6;
    border-radius: 0 6px 6px 0;
    margin-top: 0.5rem;
}
</style>
""", unsafe_allow_html=True)

# ── Secrets ───────────────────────────────────────────────────────────────────
OPENAI_KEY  = st.secrets.get("OPENAI_API_KEY", "")
HS_TOKEN    = st.secrets.get("HUBSPOT_TOKEN", "")
HS_BASE     = "https://api.hubapi.com"

# ── HubSpot helpers ───────────────────────────────────────────────────────────
def hs_create_contact(token, data):
    r = requests.post(
        f"{HS_BASE}/crm/v3/objects/contacts",
        headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
        json={"properties": data}
    )
    return r.json()

def hs_create_deal(token, data):
    r = requests.post(
        f"{HS_BASE}/crm/v3/objects/deals",
        headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
        json={"properties": data}
    )
    return r.json()

def hs_associate_contact_deal(token, contact_id, deal_id):
    requests.put(
        f"{HS_BASE}/crm/v3/objects/deals/{deal_id}/associations/contacts/{contact_id}/3",
        headers={"Authorization": f"Bearer {token}"}
    )

# ── JSON helpers ──────────────────────────────────────────────────────────────
def clean_json(text):
    """Strip markdown code fences from JSON text."""
    text = re.sub(r'^```json\s*', '', text.strip())
    text = re.sub(r'^```\s*', '', text)
    text = re.sub(r'```$', '', text.strip())
    return text.strip()

# ── OpenAI agent ──────────────────────────────────────────────────────────────
def run_agent(company_name, website, contact_name, contact_title):
    client = OpenAI(api_key=OPENAI_KEY)

    # ── Step 1: Enrich ────────────────────────────────────────────────────────
    enrich_prompt = f"""You are a B2B GTM research agent for Obligo, a fintech company that eliminates security deposits for landlords and renters.

Research this property management company and return a JSON object with the following fields:
- company_name: string
- estimated_units: number (how many rental units they likely manage)
- property_types: list of strings (e.g. ["multifamily", "single-family", "commercial"])
- markets: list of strings (cities or states they operate in)
- company_size: string ("small" = <500 units, "mid-market" = 500-5000, "enterprise" = 5000+)
- pain_points: list of strings (specific pain points this company likely has around security deposits)
- obligo_fit_signals: list of strings (reasons they would benefit from Obligo)
- tech_signals: list of strings (any property management software they likely use)
- summary: string (2-3 sentence company overview)

Company: {company_name}
Website: {website}

Return ONLY valid JSON, no markdown, no explanation."""

    with st.spinner(""):
        enrich_resp = client.chat.completions.create(
            model="gpt-4o",
            messages=[{"role": "user", "content": enrich_prompt}],
            temperature=0.3
        )
    
    try:
        enrichment = json.loads(clean_json(enrich_resp.choices[0].message.content))
    except:
        enrichment = {"summary": enrich_resp.choices[0].message.content, "estimated_units": 0, "company_size": "unknown", "pain_points": [], "obligo_fit_signals": [], "markets": [], "property_types": [], "tech_signals": []}

    # ── Step 2: Score ─────────────────────────────────────────────────────────
    score_prompt = f"""You are a GTM qualification agent for Obligo, a fintech that replaces security deposits with a fee-based model.

Ideal Obligo customer profile:
- Property managers or landlords with 50+ units (ESPECIALLY 5000+ units = enterprise = HIGH PRIORITY)
- Operate in competitive rental markets (major metros)
- Want to attract renters with deposit-free leasing
- Currently losing deals to competitors offering deposit alternatives
- Use modern property management software

SCORING GUIDELINES:
- Enterprise companies (5000+ units): Score 80-95 — they have massive unit counts, complex operations, and are losing deals to deposit alternatives
- Mid-market (500-5000 units): Score 60-80 — good fit, proven operations
- Small (<500 units): Score 40-60 — potential but lower priority
Adjust based on market competitiveness and pain points identified.

Score this company 0-100 for Obligo fit and return JSON:
- score: number (0-100)
- tier: string ("hot" = 75+, "warm" = 50-74, "cold" = <50)
- reasoning: string (2-3 sentences explaining the score)
- recommended_action: string ("book demo", "nurture sequence", "deprioritize")
- key_talking_points: list of 3 strings (specific things to mention in outreach)

Company data:
{json.dumps(enrichment, indent=2)}

Return ONLY valid JSON, no markdown."""

    with st.spinner(""):
        score_resp = client.chat.completions.create(
            model="gpt-4o",
            messages=[{"role": "user", "content": score_prompt}],
            temperature=0.2
        )

    try:
        scoring = json.loads(clean_json(score_resp.choices[0].message.content))
    except:
        scoring = {"score": 50, "tier": "warm", "reasoning": score_resp.choices[0].message.content, "recommended_action": "nurture sequence", "key_talking_points": []}

    # ── Step 3: Write email ───────────────────────────────────────────────────
    email_prompt = f"""You are a senior SDR at Obligo, a fintech company that eliminates security deposits for property managers and landlords.

Write a personalized cold outbound email to this contact. The email should:
- Be 4-6 sentences max, no fluff
- Reference something specific about their company (not generic)
- Connect their specific pain point to Obligo's value prop
- Have a single soft CTA (15 min call)
- Sound human, not like a template
- NO subject line needed, just the email body
- End with exactly "Best," on its own line — no name, no contact info, no placeholders after it

Contact: {contact_name}, {contact_title} at {company_name}
Company summary: {enrichment.get('summary', '')}
Their pain points: {', '.join(enrichment.get('pain_points', []))}
Key talking points to use: {', '.join(scoring.get('key_talking_points', []))}

Write ONLY the email body, no subject line, no labels."""

    with st.spinner(""):
        email_resp = client.chat.completions.create(
            model="gpt-4o",
            messages=[{"role": "user", "content": email_prompt}],
            temperature=0.7
        )

    email_body = email_resp.choices[0].message.content.strip()

    return enrichment, scoring, email_body


# ── UI ────────────────────────────────────────────────────────────────────────
st.markdown("""
<div class="agent-header">
  <h1>🏢 Obligo GTM Agent</h1>
  <p>ai-powered lead enrichment · fit scoring · personalized outreach · hubspot sync &nbsp;·&nbsp; <a href="https://github.com/ShahDev007/obligo-gtm-agent" target="_blank" style="color:rgba(255,255,255,0.5);text-decoration:none;">GitHub ↗</a></p>
</div>
""", unsafe_allow_html=True)

# ── Sidebar ───────────────────────────────────────────────────────────────────
with st.sidebar:
    push_to_hs = st.toggle("Push results to HubSpot", value=True)
    st.divider()
    st.markdown("### 📋 How it works")
    st.markdown("""
1. **Enrich** — GPT-4o researches the company and extracts key signals
2. **Score** — Agent scores fit against Obligo's ICP (0-100)
3. **Email** — Generates a personalized first-touch outbound email
4. **Sync** — Pushes contact + deal + score into HubSpot automatically
""")

effective_openai = OPENAI_KEY
effective_hs     = HS_TOKEN

# ── Input form ────────────────────────────────────────────────────────────────
st.markdown("### Target account")

col1, col2 = st.columns(2)
with col1:
    company_name  = st.text_input("Company name")
    contact_name  = st.text_input("Contact name")
with col2:
    website       = st.text_input("Website")
    contact_title = st.text_input("Contact title")

run = st.button("▶ Run Agent", type="primary", disabled=not (company_name and website and contact_name and contact_title and effective_openai))

if not effective_openai:
    st.warning("OpenAI API key not found. Add OPENAI_API_KEY to your Streamlit secrets.")

# ── Agent execution ───────────────────────────────────────────────────────────
if run and company_name and website:
    st.divider()
    st.markdown("### Agent output")

    # Progress
    prog = st.progress(0, text="Starting agent...")

    # Step 1
    prog.progress(10, text="Step 1 of 3 — Enriching company data with GPT-4o...")
    enrichment, scoring, email_body = run_agent(company_name, website, contact_name, contact_title)
    prog.progress(100, text="Agent complete ✓")

    # ── Layout: 3 cols for top stats ──────────────────────────────────────────
    c1, c2, c3 = st.columns(3)

    with c1:
        st.markdown('<div class="step-card"><div class="step-label">Step 1 — Enrichment</div>', unsafe_allow_html=True)
        st.markdown(f"**{enrichment.get('company_name', company_name)}**")
        st.caption(enrichment.get('summary', ''))

        markets = enrichment.get('markets', [])
        ptypes  = enrichment.get('property_types', [])
        tech    = enrichment.get('tech_signals', [])
        pain    = enrichment.get('pain_points', [])

        if markets:
            tags = " ".join([f'<span class="tag tag-blue">{m}</span>' for m in markets[:4]])
            st.markdown(f"**Markets** {tags}", unsafe_allow_html=True)
        if ptypes:
            tags = " ".join([f'<span class="tag tag-blue">{t}</span>' for t in ptypes[:3]])
            st.markdown(f"**Property types** {tags}", unsafe_allow_html=True)
        if tech:
            tags = " ".join([f'<span class="tag tag-blue">{t}</span>' for t in tech[:3]])
            st.markdown(f"**Tech signals** {tags}", unsafe_allow_html=True)
        if pain:
            tags = " ".join([f'<span class="tag tag-orange">{p}</span>' for p in pain[:5]])
            st.markdown(f"**Pain points** {tags}", unsafe_allow_html=True)

        units = enrichment.get('estimated_units', 0)
        size  = enrichment.get('company_size', '—')
        st.metric("Est. units managed", f"{units:,}" if isinstance(units, int) else units)
        st.metric("Company size tier", size.title())
        st.markdown('</div>', unsafe_allow_html=True)

    with c2:
        score = scoring.get('score', 0)
        tier  = scoring.get('tier', 'warm')
        score_color = "#1a6b3c" if score >= 75 else ("#b8600a" if score >= 50 else "#c0392b")
        tier_bg     = "#edf7f2" if tier == "hot" else ("#fef6ec" if tier == "warm" else "#fdf0ee")
        tier_fg     = "#1a6b3c" if tier == "hot" else ("#b8600a" if tier == "warm" else "#c0392b")
        action      = scoring.get('recommended_action', '—')

        st.markdown(f"""
<div class="step-card">
  <div class="step-label">Step 2 — Fit Score</div>
  <div style="font-size:3rem;font-weight:700;line-height:1;color:{score_color};margin-bottom:8px">{score}</div>
  <div style="margin-bottom:10px">
    <span style="display:inline-block;font-family:'IBM Plex Mono',monospace;font-size:.65rem;padding:3px 8px;border-radius:4px;background:{tier_bg};color:{tier_fg};font-weight:500">{tier.upper()}</span>
  </div>
  <div style="font-size:.75rem;font-weight:600;text-transform:uppercase;letter-spacing:.05em;color:#6b6860;margin-bottom:4px">Recommended action</div>
  <div style="font-size:.9rem;color:#1a3a5c;font-weight:700;margin-bottom:10px">{action.title()}</div>
  <div class="reasoning-box">{scoring.get('reasoning','')}</div>
</div>
""", unsafe_allow_html=True)

        st.markdown("**Key talking points**")
        for pt in scoring.get('key_talking_points', []):
            st.markdown(f"- {pt}")

    with c3:
        st.markdown('<div class="step-card"><div class="step-label">Step 3 — Personalized Email</div>', unsafe_allow_html=True)
        st.markdown(f"**To:** {contact_name}, {contact_title}")
        st.markdown(f"**Re:** {company_name}")
        st.markdown(f'<div class="email-box">{email_body}</div>', unsafe_allow_html=True)
        st.markdown('</div>', unsafe_allow_html=True)

    # ── Step 4: HubSpot push ──────────────────────────────────────────────────
    st.divider()
    st.markdown("### Step 4 — HubSpot sync")

    if not push_to_hs:
        st.info("HubSpot push is disabled. Toggle it on in the sidebar to sync.")
    elif not effective_hs:
        st.warning("No HubSpot token found. Add it in the sidebar or Streamlit secrets.")
    else:
        with st.spinner("Pushing to HubSpot..."):
            # Create contact
            contact_parts = contact_name.strip().split(" ", 1)
            firstname = contact_parts[0]
            lastname  = contact_parts[1] if len(contact_parts) > 1 else ""

            contact_payload = {
                "firstname": firstname,
                "lastname": lastname,
                "jobtitle": contact_title,
                "company": company_name,
                "website": website,
                "lifecyclestage": "salesqualifiedlead" if score >= 75 else ("marketingqualifiedlead" if score >= 50 else "lead"),
                "hs_lead_status": "NEW",
            }

            contact_resp = hs_create_contact(effective_hs, contact_payload)
            contact_id   = contact_resp.get("id")

            # Create deal
            tier_to_stage = {"hot": "qualifiedtobuy", "warm": "appointmentscheduled", "cold": "appointmentscheduled"}
            deal_payload = {
                "dealname": f"{company_name} — Obligo Outbound",
                "dealstage": tier_to_stage.get(tier, "appointmentscheduled"),
                "pipeline": "default",
                "amount": str(units * 5) if isinstance(units, (int, float)) and units else "5000",
                "closedate": "2026-09-01",
            }

            deal_resp = hs_create_deal(effective_hs, deal_payload)
            deal_id   = deal_resp.get("id")

            # Associate
            if contact_id and deal_id:
                hs_associate_contact_deal(effective_hs, contact_id, deal_id)

        if contact_id and deal_id:
            st.markdown(f"""
            <div class="hs-success">
              ✅ <strong>Synced to HubSpot</strong><br/>
              Contact <code>{contact_name}</code> created with lifecycle stage <strong>{"SQL" if score >= 75 else "MQL"}</strong><br/>
              Deal <code>{company_name} — Obligo Outbound</code> created and linked<br/>
              Contact ID: <code>{contact_id}</code> · Deal ID: <code>{deal_id}</code>
            </div>
            """, unsafe_allow_html=True)
        else:
            err = contact_resp.get("message", "Unknown error")
            st.markdown(f'<div class="hs-error">⚠️ HubSpot sync failed: {err}</div>', unsafe_allow_html=True)

    # ── Email copy button ─────────────────────────────────────────────────────
    st.divider()
    st.markdown("### Copy email to clipboard")
    st.code(email_body, language=None)
