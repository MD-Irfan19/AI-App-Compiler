# AI App Compiler

> Natural Language → Structured App Configuration → Validated → Executable Application

A system that behaves like a compiler for software generation. It takes an open-ended natural language prompt describing an application and converts it into a strict, validated, cross-consistent configuration — covering UI schema, API schema, database schema, auth rules, and business logic — then generates an actual runnable Next.js application from that configuration.

This is not a single prompt-to-JSON wrapper. It is a multi-stage pipeline with dedicated validation, automatic repair, and cross-layer consistency enforcement at every step.

🔗 **Live Demo:** _[coming soon]_
🎥 **Walkthrough Video:** _[coming soon]_

---

## Table of Contents

- [Overview](#overview)
- [Architecture](#architecture)
- [Tech Stack](#tech-stack)
- [Project Structure](#project-structure)
- [Setup & Installation](#setup--installation)
- [Running the Project](#running-the-project)
- [API Reference](#api-reference)
- [Validation & Repair Engine](#validation--repair-engine)
- [Runtime Generator](#runtime-generator)
- [Known Limitations](#known-limitations)
- [Future Improvements](#future-improvements)

---

## Overview

Given a prompt like:

> "Build a CRM with login, contacts, dashboard, role-based access, and premium plan with payments. Admins can see analytics."

The system produces:

- A structured **intent** (app type, features, roles, assumptions)
- A **system design** (entities, flows, external services)
- A **database schema** (tables, fields, relations, foreign keys)
- An **API schema** (REST endpoints, request/response shapes, role-based access)
- A **UI schema** (pages, components, data bindings)
- An **auth schema** (roles, permissions, JWT config)
- **Business logic** (triggers, rules, premium feature gating)

...and optionally generates a fully styled, buildable Next.js application from that configuration — proving the output is executable, not just descriptive JSON.

---

## Architecture

The system is deliberately split into four independent pipeline stages, each backed by its own LLM call and its own validation pass. This is the core design decision: a single mega-prompt cannot guarantee structural validity, cross-layer consistency, or graceful failure handling. A staged pipeline can.

```
User Prompt
    │
    ▼
┌─────────────────────┐
│ Stage 1: Intent      │  → Extracts app_name, app_type, features,
│ Extraction           │     roles, assumptions, clarifications
└─────────┬────────────┘
          ▼
┌─────────────────────┐
│ Stage 2: System      │  → Entities, flows, external services
│ Design               │
└─────────┬────────────┘
          ▼
┌─────────────────────┐
│ Stage 3: Schema       │  → 5 sequential sub-generators:
│ Generation            │     Database → API → UI → Auth → Business Logic
└─────────┬────────────┘
          ▼
┌─────────────────────┐
│ Stage 4: Refinement   │  → Cross-layer consistency check
│ & Validation          │     LLM-assisted repair if critical errors found
└─────────┬────────────┘
          ▼
   Final AppConfig (validated Pydantic model)
          │
          ▼ (optional)
┌─────────────────────┐
│ Runtime Generator     │  → Writes a real, buildable Next.js app
└──────────────────────┘
```

### Why this design

- **Dependency-aware generation** — Stage 3's sub-generators run in a deliberate order (Database → API → UI) because each depends on the output of the previous one. The API schema references real table names; the UI schema references real API paths.
- **Validation is not optional or cosmetic** — every stage's raw LLM output passes through a repair engine before it's accepted, regardless of which model produced it.
- **Refinement is conditional, not automatic** — Stage 4 only triggers a costly LLM-based refinement pass when consistency checks find *critical* errors (e.g. an undefined role). Non-blocking warnings (e.g. minor data-source path mismatches) are logged but don't trigger an expensive re-prompt — this was a deliberate latency optimization after profiling showed refinement could otherwise add 5+ minutes per run for zero correctness benefit.

---

## Tech Stack

| Layer | Technology |
|---|---|
| Backend framework | Python, FastAPI |
| LLM provider | Nvidia NIM (OpenAI-compatible API), `meta/llama-3.3-70b-instruct` |
| Schema validation | Pydantic v2 |
| JSON repair | `json-repair` library + custom field-level repair logic |
| Frontend framework | Next.js 14 (App Router), TypeScript |
| Styling | Tailwind CSS |
| Animation | Framer Motion |
| Icons | lucide-react |
| Generated app output | Next.js 14, TypeScript, Tailwind (same stack, standalone) |

---

## Project Structure

```
ai-app-compiler/
├── backend/
│   ├── pipeline/
│   │   ├── stage1_intent.py        # Intent extraction
│   │   ├── stage2_design.py        # System architecture design
│   │   ├── stage3_schema.py        # DB, API, UI, Auth, Business Logic generators
│   │   ├── stage4_refine.py        # Cross-layer refinement & assembly
│   │   └── llm_client.py           # Shared Nvidia NIM client wrapper
│   ├── validation/
│   │   ├── schemas.py              # All Pydantic models (the contract)
│   │   └── repair.py               # JSON repair + field repair + consistency checks
│   ├── runtime/
│   │   └── generator.py            # Generates a real Next.js app from AppConfig
│   ├── main.py                     # FastAPI app — /compile, /compile/stream, /health, /metrics
│   ├── requirements.txt
│   └── .env                        # NVIDIA_API_KEY (not committed)
│
├── frontend/
│   ├── app/
│   │   ├── page.tsx                # Main UI — prompt input, pipeline progress, results tabs
│   │   ├── layout.tsx
│   │   └── globals.css
│   ├── package.json
│   ├── tsconfig.json
│   └── .env.local  
│
├── evaluation/
│   ├── test_prompts.json           # 20 test prompts (real-world + edge cases)
│   └── runner.py                   # Batch evaluation runner with metrics
│
└── README.md
```

---

## Setup & Installation

### Prerequisites

- Python 3.11+
- Node.js 18+ and npm
- An Nvidia NIM API key — get one free at [build.nvidia.com](https://build.nvidia.com)

### 1. Clone the repository

```bash
git clone https://github.com/MD-Irfan19/AI-App-Compiler.git
cd ai-app-compiler
```

### 2. Backend Setup

```bash
cd backend
```

Create a virtual environment (recommended):

```bash
python -m venv venv

# Windows
venv\Scripts\activate

# macOS / Linux
source venv/bin/activate
```

Install dependencies:

```bash
pip install -r requirements.txt --break-system-packages
```

Create a `.env` file in the `backend/` directory:

```env
NVIDIA_API_KEY=nvapi-your-key-here
```

> Get your free API key at [build.nvidia.com](https://build.nvidia.com) — new accounts receive $100 in free credits, more than enough to run this project extensively.

### 3. Frontend Setup

```bash
cd ../frontend
npm install
```

No environment variables are required for the frontend in local development — it talks to the backend at `http://localhost:8000` by default. If you deploy the backend elsewhere, update the fetch URLs in `frontend/app/page.tsx` accordingly.

---

## Running the Project

You need **two terminals** running simultaneously.

### Terminal 1 — Backend

```bash
cd backend
python -m uvicorn main:app --reload --port 8000
```

The API will be available at `http://localhost:8000`. Interactive API docs (Swagger UI) are available at `http://localhost:8000/docs`.

### Terminal 2 — Frontend

```bash
cd frontend
npm run dev
```

The UI will be available at `http://localhost:3000`.

### Try it

Open `http://localhost:3000`, enter a prompt such as:

```
Build a CRM with login, contacts, dashboard, role-based access,
and premium plan with payments. Admins can see analytics.
```

Click **Compile App** and watch the pipeline run through all four stages in real time, with live progress synced to actual backend execution via Server-Sent Events.

---

## API Reference

### `POST /compile`

Runs the full 4-stage pipeline synchronously and returns the complete result in a single response.

**Request body:**

```json
{
  "prompt": "Build a CRM with login, contacts, and a dashboard.",
  "generate_app_files": false
}
```

**Response:**

```json
{
  "success": true,
  "prompt": "...",
  "app_config": {
    "intent": { ... },
    "system_design": { ... },
    "database": { ... },
    "api": { ... },
    "ui": { ... },
    "auth": { ... },
    "business_logic": { ... },
    "generation_metadata": { ... }
  },
  "stages": [
    { "stage": "intent_extraction", "status": "success", "duration_ms": 15000, "output_summary": { ... } },
    ...
  ],
  "validation": {
    "is_valid": true,
    "errors": [],
    "warnings": []
  },
  "generated_app_path": null,
  "total_duration_ms": 240000,
  "timestamp": "2026-06-08T12:00:00"
}
```

### `POST /compile/stream`

Same pipeline, but streamed via Server-Sent Events — emits real-time `stage_start`, `substep_done`, `stage_done`, and a final `complete` event as each stage genuinely finishes on the backend. This is what powers the live progress UI in the frontend.

### `GET /health`

Basic health check — returns model name, pipeline stage count, and current timestamp.

### `GET /metrics`

Returns aggregate statistics from all past `/compile` and `/compile/stream` runs logged to `evaluation/results.json` — total runs, success rate, average duration, and the 5 most recent runs.

---

## Validation & Repair Engine

This is the core differentiator of the system. Every layer of LLM output passes through multiple defensive checks before being accepted:

**JSON-level repair**
- Strips markdown code fences the model sometimes wraps output in
- Falls back to the `json-repair` library when direct `json.loads()` fails on malformed output

**Field-level repair**
- Injects default values for missing required keys per layer
- Detects and fixes invalid or empty `type` fields (handles both *missing key* and *empty string* cases — these are different failure modes from the LLM and both occur in practice)
- Repairs malformed API endpoint objects missing `method` or `description`, inferring a sensible HTTP method from the path when possible
- Guards every loop against non-dict list items, since LLMs occasionally return malformed list structures (e.g. `[null, {}, "string"]` instead of a clean object list)

**Cross-layer consistency checks**
- Verifies every role referenced in UI pages and API endpoints actually exists in the auth schema
- Verifies UI component `data_source` values map to real, defined API endpoint paths
- Verifies API field `foreign_key` references point to real database tables
- Classifies issues as **critical errors** (block and trigger refinement) vs **warnings** (logged, non-blocking) — this distinction is what keeps the pipeline fast without sacrificing correctness on the issues that actually matter

**Conditional refinement**
- Stage 4 only re-prompts the LLM for a repair pass when critical errors are present — not on warnings alone. If refinement is triggered, any layer the LLM drops or returns malformed in its refined output falls back to the original pre-refinement data, so no layer is ever silently lost.

---

## Runtime Generator

When `generate_app_files: true` is passed to `/compile`, the system writes a complete, styled, buildable Next.js 14 application to disk based on the final validated `AppConfig`. This includes:

- `package.json`, `tsconfig.json`, `tailwind.config.js`, `postcss.config.js`, `next.config.js`
- A dark-themed `globals.css` with reusable component classes
- `layout.tsx` with a sticky navigation bar built from the generated nav items
- A home page with stats and a card grid linking to every generated page
- One `page.tsx` per UI page, with styled table/form/chart/card/list components matching the schema
- One `route.ts` per API endpoint, scaffolded with role/auth comments
- `docs/database.md` and `docs/auth.md` — human-readable schema documentation
- `app-config.json` — the full compiled configuration
- `README.md` for the generated app itself

The generated output is verified to pass `npm run build` cleanly — this is the proof that the system's output is genuinely executable, not just well-formed JSON.

---

## Known Limitations

- Pipeline latency is currently dominated by Stage 3 (schema generation), which makes 5 sequential LLM calls. This could be parallelized further since some sub-generators (auth, business logic) don't strictly depend on each other.
- The evaluation framework (20 test prompts covering real-world and edge cases) is built but has not yet been run at full scale to produce aggregate success-rate metrics.
- Refinement repair currently relies on the LLM returning a complete corrected config; while missing layers are safely backfilled from the pre-refinement version, partial corruption within a single layer's nested fields is not yet individually repaired post-refinement.
- No persistent database — generated configs and evaluation results are stored as local JSON files, suitable for demonstration but not production scale.

## Future Improvements

- Parallelize independent Stage 3 sub-generators to reduce total pipeline latency
- Run the full evaluation suite and publish real success-rate, retry-count, and latency metrics
- Add constrained decoding / structured output mode if the LLM provider supports it, to reduce reliance on post-hoc JSON repair
- Persist generated apps and configs to a real database instead of local disk
- Add authentication to the API itself so multiple users can run compiles without shared rate limits
#
