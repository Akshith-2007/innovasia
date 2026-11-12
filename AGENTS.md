# AGENTS.md — Kisan Cold Link

## 1. Project identity

Kisan Cold Link is a public AgriTech website with an agricultural
market-intelligence backend.

The repository contains:
- React + TypeScript + Vite frontend.
- Python + FastAPI backend.
- Official government agricultural data integrations.
- Local data processing.
- A genuinely trained mandi-price forecasting model.

This is NOT the farmer mobile application.

## 2. Non-negotiable restrictions

- Do not create a farmer application. The admin-only farmer lot register of ADR-026 is the only exception.
- Do not introduce authentication beyond the single admin password and device key of ADR-024.
- Do not introduce a database.
- Do not add PostgreSQL, MongoDB or Redis.
- Do not generate synthetic market data.
- Do not fabricate market prices.
- Do not hardcode ML predictions.
- Do not fabricate model metrics.
- Do not silently substitute external datasets. The only permitted non-official source is the
  GODL-licensed Kaggle mirror of AGMARKNET in ADR-022, and it must always be labelled as such.
- Do not present cached data as live data.
- Do not expose API keys to the frontend.
- Do not claim untested cooling performance. PCM backup hours are a labelled physics estimate from entered values (ADR-025).

## 3. Data integrity

Use original government-published datasets and official APIs.

Primary market source:
AGMARKNET / data.gov.in.

Preserve original downloaded data under backend/data/raw/.

Never modify raw source files.

All transformations must be reproducible.

Every processed dataset must retain:
- Source.
- Retrieval timestamp.
- Observation dates.
- Original schema information.
- Record count.
- File checksum.

Missing values must be handled explicitly.

Never silently fill missing prices.

If data is insufficient, report insufficient data.

## 4. Machine learning rules

All training data must originate from government sources: official downloads, or the
ADR-022 Kaggle mirror of AGMARKNET (disclosed in model metadata and on the site).

Use chronological train/validation/test splits.

Prevent future-data leakage.

Compare against a simple baseline.

Report actual evaluation metrics.

Persist model metadata:
- Model version.
- Training date.
- Data cutoff.
- Dataset checksum.
- Feature schema.
- Evaluation results.

Never return fabricated predictions.

Never return a prediction for an unsupported market/commodity series.

## 5. Frontend rules

Use:
- React.
- TypeScript.
- Vite.
- Tailwind CSS.
- shadcn/ui.
- Recharts.
- Motion.
- Lucide.

Design must be premium, modern and consistent.

Avoid generic AI-generated website aesthetics.

Prefer reusable components.

Do not install dependencies without a clear need.

Every page must support mobile, tablet and desktop.

All charts must use real backend responses.

Include loading, empty and error states.

## 6. Backend rules

Use:
- FastAPI.
- Pydantic.
- Pandas.
- NumPy.
- Scikit-learn.
- XGBoost when justified.
- PyArrow.
- Joblib.

Keep external data providers isolated.

Keep API schemas explicit.

Use typed functions.

Handle timeouts, rate limits and schema changes.

Do not add unnecessary abstraction.

## 7. Engineering discipline

Before implementing:
1. Inspect existing code.
2. Read AGENTS.md.
3. Read CLAUDE.md.
4. Read DECISIONS.md.
5. Inspect the knowledge graph.
6. Reuse existing components and services.
7. Make the smallest complete change.

After implementing:
1. Run relevant tests.
2. Run type checks.
3. Run the frontend build.
4. Verify backend startup.
5. Update DECISIONS.md if a meaningful decision was made.
6. Update knowledge-graph files when dependencies change.
7. Update documentation.

## 8. Decision logging

All significant architecture, dependency, data-source, model,
security and design decisions must be recorded in DECISIONS.md.

Never rewrite accepted historical decisions.

Supersede old decisions with a new entry.

## 9. Knowledge graph

Maintain:
- docs/knowledge-graph.json
- docs/knowledge-graph.mmd

Track:
- Pages.
- Components.
- API endpoints.
- Backend services.
- Data providers.
- Dataset files.
- ML scripts.
- Model artifacts.
- External dependencies.

Update the graph when architecture changes.

## 10. Development commands

Start the entire application:

./dev.sh

Frontend:
http://127.0.0.1:5173

Backend:
http://127.0.0.1:8000

API documentation:
http://127.0.0.1:8000/docs

Data acquisition and model training must be explicit commands.
Do not run expensive downloads or training automatically.

## 11. Completion response

After each task report:
- What changed.
- Files modified.
- Tests executed.
- Tests passed/failed.
- Documentation updated.
- Decisions added.
- Knowledge graph updated.
- Known limitations.

## 12. Code map

- backend/app/providers/  — only code that calls data.gov.in.
- backend/app/pipeline/   — immutable raw store (ADR-009), validation (ADR-012), Parquet.
- backend/app/ml/         — features (ADR-013), training/selection (ADR-014), prediction.
- backend/app/services/   — read-only queries over processed files.
- backend/scripts/        — explicit CLIs: fetch, validate, preprocess, train, evaluate.
- frontend/src/components/ui — design primitives; tokens in src/styles/globals.css (ADR-016).
- Tests may build labelled test inputs in temp dirs only (ADR-017); never under backend/data or backend/models.
- Knowledge graph: edit docs/knowledge-graph.json, run `python docs/generate_graph.py`,
  and `python docs/generate_graph.py --check` must pass.
