# Kisan Cold Link — Claude Code

Read these files before starting work:

1. @AGENTS.md
2. @DECISIONS.md
3. @docs/knowledge-graph.mmd
4. @README.md

## Project

Public AgriTech website and agricultural intelligence backend.

Frontend: React + TypeScript + Vite.
Backend: FastAPI.
ML: Scikit-learn / XGBoost.
Data: Official government agricultural datasets.
Storage: CSV / Parquet / model artifacts.
Database: None.

## Important commands

Start everything (Git Bash on Windows):
./dev.sh

Frontend:
cd frontend && npm run dev

Backend (venv python is `.venv/Scripts/python` on Windows, `.venv/bin/python` elsewhere):
cd backend && .venv/Scripts/python -m uvicorn app.main:app --reload

Tests and checks:
cd backend && .venv/Scripts/python -m pytest
cd frontend && npm test && npm run typecheck && npm run build
python docs/generate_graph.py --check

Data and training (explicit only, never automatic; see README):
python -m scripts.fetch_official_data probe|current|history|crop-api|crop-import
python -m scripts.validate_data
python -m scripts.preprocess_data
python -m scripts.train_price_model
python -m scripts.evaluate_model

Knowledge graph: edit docs/knowledge-graph.json, then run `python docs/generate_graph.py`.

## Development workflow

- Inspect before changing.
- Reuse before creating.
- Follow AGENTS.md.
- Follow Ponytail principles.
- Keep changes minimal.
- Test important behaviour.
- Do not introduce mock data.
- Do not fabricate ML predictions.
- Update DECISIONS.md for significant decisions.
- Update the knowledge graph when architecture changes.

## Design requirements

Build a premium AgriTech website.

Avoid generic templates.
Use intentional typography, layout, spacing and motion.
Keep all pages visually consistent.
Use real API data for market visualizations.
Use the design tokens in frontend/src/styles/globals.css and primitives in frontend/src/components/ui (ADR-016).
