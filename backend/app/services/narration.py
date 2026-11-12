"""Optional AWS Bedrock narration of a deterministic report (ADR-030).

Bedrock never calculates anything: it receives the finished template (every number already computed by
lot_service/storage_planner) and may only rephrase it. The reply must be JSON {"script": "..."} (Pydantic).
It is rejected, and the template is used, if it changes, drops or adds any number, mentions the farmer's
name, stops addressing the farmer as Babai, or invites a spoken answer. Results are cached on disk by a hash
of the template, language, model and prompt version, so identical reports never call Bedrock twice.
"""

from __future__ import annotations

import hashlib
import json
import logging
import re
from pathlib import Path
from typing import Any

from pydantic import BaseModel, Field, ValidationError

from app.core.config import get_settings
from app.services.advisory_script import Language

log = logging.getLogger(__name__)
PROMPT_VERSION = "raithanna-narration-v1"

SYSTEM = (
    "You are Raithanna (రైతన్న), a warm, respectful Telugu-speaking village companion of Kisan Cold Link. "
    "You rewrite a market report so it sounds natural when read aloud to a farmer. Always address the farmer "
    "as Babai (బాబాయ్); never use any personal name. Keep every number exactly as written (same digits, same "
    "commas), keep every mandi name and crop name exactly, and do not add, remove, round or recompute any number. "
    "Do not add facts, prices, advice or promises that are not in the report. Keep stated uncertainty and any "
    "'not recorded' or 'not enough data' statements. The listener cannot speak back: never ask questions or "
    "invite a reply. Use simple everyday words, no headings, no lists, no markdown. "
    'Reply with only a JSON object: {"script": "<the rewritten report>"}.'
)

# Phrases that ask the farmer to answer out loud; the app cannot listen (no microphone, ADR-030).
_REPLY_PROMPTS = ["?", "ఏమంటావ", "చెప్పండి", "చెప్పు బాబాయ్", "what do you think", "tell me", "let me know"]
_NUM = re.compile(r"\d[\d,]*(?:\.\d+)?")


class NarrationOut(BaseModel):
    script: str = Field(min_length=20, max_length=20_000)


def numbers(text: str) -> list[str]:
    return sorted(n.replace(",", "").rstrip(".") for n in _NUM.findall(text))


def validate(template: str, candidate: str, lang: Language, forbidden: list[str]) -> str | None:
    """None if the candidate is acceptable, else the reason it was rejected."""
    if numbers(template) != numbers(candidate):
        return "numbers changed"
    if ("బాబాయ్" if lang == "te" else "babai") not in candidate.lower():
        return "farmer not addressed as Babai"
    low = candidate.casefold()
    if any(f and f.casefold() in low for f in forbidden):
        return "contains the farmer's name"
    if any(p in low and p not in template.casefold() for p in _REPLY_PROMPTS):
        return "invites a spoken reply"
    return None


def _cache(key: str) -> Path:
    d = get_settings().data_dir / "advisory" / "scripts"
    d.mkdir(parents=True, exist_ok=True)
    return d / f"{key}.json"


def _parse(raw: str) -> NarrationOut:
    raw = raw.strip()
    m = re.search(r"\{.*\}", raw, re.S)  # tolerate code fences around the JSON
    return NarrationOut.model_validate_json(m.group(0) if m else raw)


def _invoke(model_id: str, template: str, lang: Language) -> str:
    import boto3  # imported lazily: only needed when Bedrock is configured
    from botocore.config import Config

    s = get_settings()
    client = boto3.client("bedrock-runtime", region_name=s.aws_region,
                          config=Config(read_timeout=s.bedrock_timeout_seconds, retries={"max_attempts": 2}))
    language = "Telugu" if lang == "te" else "Indian English"
    resp = client.converse(
        modelId=model_id,
        system=[{"text": SYSTEM}],
        messages=[{"role": "user", "content": [{"text": f"Language: {language}.\nReport:\n{template}"}]}],
        inferenceConfig={"maxTokens": 4000},
    )
    return "".join(b.get("text", "") for b in resp["output"]["message"]["content"])


def narrate(template: str, lang: Language, forbidden: list[str]) -> dict[str, Any]:
    """Return {script, narration: 'bedrock'|'template', note}. Never raises; failures fall back to the template."""
    model_id = get_settings().bedrock_model_id.strip()
    if not model_id:
        return {"script": template, "narration": "template", "note": "Bedrock not configured"}
    key = hashlib.sha256(json.dumps([PROMPT_VERSION, model_id, lang, template]).encode()).hexdigest()
    path = _cache(key)
    if path.exists():
        return json.loads(path.read_text(encoding="utf-8"))
    try:
        out = _parse(_invoke(model_id, template, lang)).script.strip()
    except (ValidationError, ValueError) as exc:
        return {"script": template, "narration": "template", "note": f"Bedrock reply was not valid JSON: {type(exc).__name__}"}
    except Exception as exc:  # network, credentials, throttling: never block the advisory
        log.warning("Bedrock narration failed: %s", type(exc).__name__)
        return {"script": template, "narration": "template", "note": f"Bedrock unavailable: {type(exc).__name__}"}
    reason = validate(template, out, lang, forbidden)
    result = ({"script": template, "narration": "template", "note": f"Bedrock output rejected: {reason}"}
              if reason else {"script": out, "narration": "bedrock", "note": model_id})
    path.write_text(json.dumps(result, ensure_ascii=False), encoding="utf-8")
    return result
