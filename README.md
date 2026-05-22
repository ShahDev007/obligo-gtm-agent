# 🏢 Obligo GTM Agent

An AI-powered go-to-market agent for [Obligo](https://obligo.com) that enriches target accounts, scores them against Obligo's ICP, writes personalized outbound emails, and syncs everything to HubSpot — in one click.

Built with **Claude Code** · [Watch demo ↗](https://www.loom.com/share/94922cf5bd284829a66412aa12307ac4)

---

## What it does

Enter a company name, website, and contact — the agent runs four steps automatically:

| Step | What happens |
|------|-------------|
| **1. Enrich** | GPT-4o researches the company: unit count, markets, property types, tech stack, and deposit-related pain points |
| **2. Score** | Agent scores the company 0–100 against Obligo's ICP with a tier (Hot / Warm / Cold), reasoning, and recommended action |
| **3. Email** | Writes a personalized cold outbound email referencing the company's specific situation and pain points |
| **4. HubSpot sync** | Creates a contact + deal in HubSpot, sets lifecycle stage (SQL/MQL/Lead), and links them |

---

## Stack

- **Frontend** — [Streamlit](https://streamlit.io)
- **AI** — GPT-4o via OpenAI API (enrichment, scoring, email generation)
- **CRM** — HubSpot CRM API v3
- **Built with** — [Claude Code](https://claude.ai/code)

---

## Setup

### 1. Clone the repo

```bash
git clone https://github.com/shahdev007/obligo-gtm-agent.git
cd obligo-gtm-agent
```

### 2. Install dependencies

```bash
pip install streamlit openai requests
```

### 3. Add secrets

Create a `secrets.toml` file in the project root:

```toml
OPENAI_API_KEY = "sk-proj-..."
HUBSPOT_TOKEN  = "pat-na2-..."
```

> These are loaded via `st.secrets` and never committed to the repo.

### 4. Run

```bash
streamlit run app.py
```

Open [http://localhost:8501](http://localhost:8501) in your browser.

---

## ICP scoring logic

The agent scores companies against Obligo's ideal customer profile:

- **Hot (75–100)** — Enterprise operators (5,000+ units) in competitive metro markets losing deals to deposit-free competitors → book demo
- **Warm (50–74)** — Mid-market operators (500–5,000 units) with modern tech stack → nurture sequence
- **Cold (< 50)** — Small operators or low-competition markets → deprioritize

---

## HubSpot sync

When enabled, the agent:
- Creates a **contact** with lifecycle stage set to SQL, MQL, or Lead based on score
- Creates a **deal** (`[Company] — Obligo Outbound`) with estimated deal value and pipeline stage
- **Associates** the contact to the deal automatically

Toggle HubSpot sync on/off from the sidebar without re-running the agent.

---

## Notes

- Enrichment is powered by GPT-4o's training knowledge — works best for well-known property management companies. For real prospecting at scale, wire in a live data source (Apollo.io, Clearbit, or Perplexity API).
- `secrets.toml` is gitignored. Never commit API keys.
