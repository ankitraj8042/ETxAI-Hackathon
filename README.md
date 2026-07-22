# DCBrain — Autonomous AI Project Manager for Data Centre EPC

> **AI-powered EPC Project Intelligence Platform** that unifies specifications, procurement, schedules, quality records, and commissioning into a living intelligence layer with autonomous multi-agent decision-making.

## 🏗️ Problem

India's data centre capacity is growing from 900 MW (2024) to 2,700 MW by 2027 — representing **$15B+ in capital deployment**. A single hyperscale facility involves:

- **15,000–40,000** equipment line items
- **200+** concurrent trade contractors
- **Thousands** of commissioning test procedures
- **Zero tolerance** for errors that compromise uptime SLAs

Yet **67% of data centre EPC projects** in Asia-Pacific experience schedule overruns >10%, with procurement misalignment and commissioning failures as leading causes.

**DCBrain solves this** with an autonomous AI Project Manager that coordinates 5 specialized AI agents through a cascade event bus, powered by a Knowledge Graph and Graph RAG.

---

## ✨ Key Features

### 🧠 AI Cascade Bus (Core Innovation)
- **5 coordinated AI agents** that react to each other's findings
- One event triggers a chain: `Upload → NCR → Schedule Impact → Alternative Vendor → Commissioning Block → Knowledge Update`
- Full explainability at every step with evidence chains

### 🏢 Interactive Digital Twin
- Zone-based floor plan (Power Room, Cooling Plant, IT Hall, Fire Safety)
- Equipment nodes with live status badges, risk scores, and glow effects
- Click any equipment → slide-out panel with intelligence from all 5 agents

### 🕸️ Knowledge Graph Explorer
- Force-directed graph visualization of project relationships
- Click nodes to explore connections, double-click to re-center
- Entity type filters and relationship labels

### 📋 3 Hero AI Modules
| Module | Capability |
|---|---|
| **Compliance Agent** | Upload submittals → AI detects spec violations → auto-generates NCRs |
| **Commissioning Copilot** | Test failure diagnosis → root cause + specific fix suggestions |
| **Knowledge Agent** | Graph RAG chat with citations + RFI similarity detection |

### 📊 Executive Command Center
- Real-time KPI dashboard with health, risks, delays, compliance, commissioning
- AI-generated recommendations with **[Approve]** action buttons
- Live cascade event timeline with agent activity stream
- **AI Daily Brief** — one-click executive summary generation

### ⏱️ Time Machine
- 4 pre-computed weekly snapshots showing project evolution
- Slider moves KPIs and Digital Twin between historical states

---

## 🏛️ Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                     FRONTEND (Next.js 15)                       │
│                                                                 │
│  ┌───────────────────────────────────────────────────────────┐  │
│  │        AI EXECUTIVE COMMAND CENTER (Homepage)             │  │
│  │  Health │ Risks │ Recommendations │ [Approve] │ Timeline │  │
│  └───────────────────────────────────────────────────────────┘  │
│  ┌───────────────────────────────────────────────────────────┐  │
│  │  DIGITAL TWIN — Click → Highlight → Detail Panel          │  │
│  └───────────────────────────────────────────────────────────┘  │
│  ┌─────────────┐ ┌─────────────────┐ ┌───────────────────┐    │
│  │ Compliance  │ │ Commissioning   │ │ Knowledge Agent   │    │
│  │ (Hero)      │ │ Copilot (Hero)  │ │ (Hero + Graph RAG)│    │
│  └─────────────┘ └─────────────────┘ └───────────────────┘    │
│  ┌───────────────────────────────────────────────────────────┐  │
│  │  Knowledge Graph Explorer (Force-Directed)                │  │
│  └───────────────────────────────────────────────────────────┘  │
├─────────────────────────────────────────────────────────────────┤
│  API LAYER: FastAPI (REST + WebSocket)                          │
├─────────────────────────────────────────────────────────────────┤
│  AGENT CASCADE BUS                                              │
│  Compliance ←→ Schedule ←→ Supply Chain ←→ Commissioning ←→    │
│  Knowledge ←→ Explainability Engine                             │
├─────────────────────────────────────────────────────────────────┤
│  DATA: SQLite/PostgreSQL │ Neo4j/In-Memory │ ChromaDB │ Redis  │
└─────────────────────────────────────────────────────────────────┘
```

---

## 🛠️ Tech Stack

| Layer | Technology |
|---|---|
| **Frontend** | Next.js 15, TypeScript, Tailwind CSS, Zustand |
| **UI** | Custom dark industrial theme, Framer Motion |
| **Digital Twin** | Custom React component with zone layout |
| **Graph Viz** | Custom SVG force-directed graph |
| **Charts** | Recharts |
| **Backend** | FastAPI, Python 3.11+ |
| **Agents** | LangGraph, LangChain |
| **LLM** | Google Gemini 2.5 Flash |
| **Knowledge Graph** | Neo4j (with in-memory fallback) |
| **Vector Store** | ChromaDB |
| **Database** | PostgreSQL / SQLite (auto-fallback) |
| **Cache** | Redis (with mock fallback) |
| **Deployment** | Docker Compose |

---

## 🚀 Quick Start

### Prerequisites
- **Node.js** 18+ and **npm**
- **Python** 3.11+
- **Google Gemini API Key** (for AI features)

### 1. Clone and Setup

```bash
git clone <repo-url>
cd "ETxAI Data centre EPC"
```

### 2. Backend Setup

```bash
cd backend

# Create virtual environment
python -m venv venv
venv\Scripts\activate    # Windows
# source venv/bin/activate  # Linux/Mac

# Install dependencies
pip install -r requirements.txt

# Configure environment
copy .env.example .env
# Edit .env and set GEMINI_API_KEY=your_key_here

# Seed the database
python data/seed_all.py

# Start backend
uvicorn app.main:app --reload --port 8000
```

### 3. Frontend Setup

```bash
cd frontend

# Install dependencies
npm install

# Start development server
npm run dev
```

### 4. Open in Browser

Navigate to **http://localhost:3000**

---

## 🐳 Docker Compose (Full Stack)

```bash
docker compose up --build
```

This starts:
- **Frontend** → http://localhost:3000
- **Backend** → http://localhost:8000
- **PostgreSQL** → port 5432
- **Neo4j** → port 7474 (browser), 7687 (bolt)
- **Redis** → port 6379
- **ChromaDB** → port 8001

---

## 📁 Project Structure

```
├── frontend/                    # Next.js 15 App
│   ├── src/app/
│   │   ├── page.tsx            # Command Center
│   │   ├── digital-twin/       # Interactive floor plan
│   │   ├── compliance/         # Spec analysis + NCR
│   │   ├── commissioning/      # Test management
│   │   ├── knowledge/          # Graph RAG chat
│   │   └── graph-explorer/     # Knowledge Graph viz
│   ├── src/components/         # Shared components
│   └── src/lib/                # API client, store, utils
│
├── backend/
│   ├── app/
│   │   ├── main.py             # FastAPI application
│   │   ├── api/routes/         # REST endpoints
│   │   ├── api/websockets/     # WebSocket cascade
│   │   ├── agents/             # AI agent implementations
│   │   │   ├── cascade_bus.py  # Event routing bus
│   │   │   ├── orchestrator.py # Agent lifecycle
│   │   │   ├── compliance_agent.py
│   │   │   ├── schedule_agent.py
│   │   │   ├── supply_chain_agent.py
│   │   │   ├── commissioning_agent.py
│   │   │   └── knowledge_agent.py
│   │   ├── graph/              # Neo4j client + queries
│   │   ├── rag/                # Graph RAG pipeline
│   │   ├── models/             # SQLAlchemy models
│   │   ├── schemas/            # Pydantic schemas
│   │   ├── services/           # Business logic
│   │   └── core/               # Config, DB, LLM
│   ├── data/                   # Seed data + DB files
│   └── requirements.txt
│
├── docker-compose.yml
├── .env.example
└── README.md
```

---

## 🎯 Demo Scenario

The demo showcases the full AI cascade in action:

1. **Vendor uploads UPS submittal** → Compliance Agent catches voltage mismatch (380V vs 400V spec)
2. **NCR auto-generated** → NCR-023 raised with severity "critical" and schedule impact assessment
3. **Cascade fires** → 5 agents react in real-time on the cascade timeline
4. **Schedule Agent** → Predicts 10-day critical path delay, generates 3 recovery plans
5. **Supply Chain Agent** → Sources Vertiv as alternative vendor with 92% reliability score
6. **Digital Twin** → UPS-2 node turns red, connected dependencies highlighted
7. **Recommendation appears** → Manager clicks [Approve] → entire project updates
8. **Knowledge Graph** → Shows UPS-2 → Vendor → NCR → Task → Test relationship path

---

## 📊 Business Impact

| Metric | Value |
|---|---|
| **Document Review Time** | 85% reduction (hours → minutes) |
| **Specification Compliance** | >90% violation detection rate |
| **Schedule Risk Prediction** | 3 recovery plans per risk event |
| **Commissioning Efficiency** | AI-guided diagnosis with fix suggestions |
| **Knowledge Access** | 70% faster with Graph RAG citations |

---

## 🔮 Production Roadmap

- [ ] Multi-project support with portfolio dashboard
- [ ] Mobile companion app for site engineers
- [ ] BIM integration (IFC model sync)
- [ ] Real-time IoT sensor feeds for commissioning
- [ ] Automated compliance report generation (PDF)
- [ ] Integration with Primavera P6 / MS Project

---

## 👥 Team

Built for the **ETxAI Hackathon 2026** — AI Intelligence Platform for Data Centre EPC Project Delivery.

---

## 📄 License

This project is built for competition purposes. All rights reserved.
