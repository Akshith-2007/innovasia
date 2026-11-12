"""Raithanna Android app support (ADR-030): farmer identification, lot views and advisory audio.

Farmers never create lots; they read the admin's lots (ADR-026). Identification is a demo flow, not OTP:
the name AND mobile number must both match an admin-created lot. The reply carries one token per lot,
HMAC(MOBILE_LINK_SECRET, lot id + phone), which every later request must present, so knowing a phone
number alone does not open anyone's records. Mismatches return the same "not registered" error whether
or not the number exists.
"""

from __future__ import annotations

import hashlib
import hmac
import re
import time
from datetime import date
from threading import Lock
from typing import Any

import pandas as pd

from app.core.config import get_settings
from app.core.exceptions import AppError, NotConfiguredError, NotFoundError
from app.ml import features as F
from app.services import advisory_script as S
from app.services import data_service, lot_service, market_service, narration, tts

COMPARE_TTL_SECONDS = 600
_compare_cache: dict[str, tuple[float, dict[str, Any]]] = {}
_cache_lock = Lock()


class FarmerUnauthorized(AppError):
    status_code = 401
    code = "unauthorized"


class FarmerNotRegistered(AppError):
    status_code = 404
    code = "farmer_not_registered"


def phone_key(phone: str | None) -> str:
    """Last 10 digits, so '+91 98480 12345' and '9848012345' match."""
    return re.sub(r"\D", "", phone or "")[-10:]


def _name_key(name: str) -> str:
    return " ".join(name.casefold().split())


def _secret() -> bytes:
    s = get_settings().mobile_link_secret.strip()
    if not s:
        raise NotConfiguredError("MOBILE_LINK_SECRET is not configured in backend/.env.")
    return s.encode()


def lot_token(lot: dict[str, Any]) -> str:
    return hmac.new(_secret(), f"{lot['id']}:{phone_key(lot.get('phone'))}".encode(), hashlib.sha256).hexdigest()[:40]


def _summary(lot: dict[str, Any], lang: S.Language = "te") -> dict[str, Any]:
    return {
        "lot_id": lot["id"], "farmer_name": lot["farmer_name"], "village": lot.get("village"),
        "state": lot["state"], "district": lot.get("district"), "commodity": lot["commodity"],
        "crop_te": S.crop_name(lot["commodity"], "te"), "crop_en": S.crop_name(lot["commodity"], "en"),
        "quantity_quintals": lot["quantity_quintals"], "storage_option": lot.get("storage_option") or "sell_now",
        "mandi_count": len(lot["mandis"]), "created_at": lot["created_at"],
    }


def identify(name: str, phone: str) -> list[dict[str, Any]]:
    _secret()  # fail closed when the feature is not configured
    pk, nk = phone_key(phone), _name_key(name)
    if len(pk) != 10 or not nk:
        raise FarmerNotRegistered(S.not_registered("te"))
    lots = [lot for lot in lot_service.list_lots()
            if phone_key(lot.get("phone")) == pk and _name_key(lot["farmer_name"]) == nk]
    if not lots:
        raise FarmerNotRegistered(S.not_registered("te"))
    return [{**_summary(lot), "token": lot_token(lot)} for lot in lots]


def authorize(lot_id: str, token: str | None) -> dict[str, Any]:
    try:
        lot = lot_service.get_lot(lot_id)
    except NotFoundError as exc:
        raise FarmerUnauthorized("This lot is not available.") from exc
    if not token or not hmac.compare_digest(token, lot_token(lot)):
        raise FarmerUnauthorized("This lot is not available.")
    return lot


def _comparison(lot: dict[str, Any]) -> dict[str, Any]:
    with _cache_lock:
        hit = _compare_cache.get(lot["id"])
    if hit and time.time() - hit[0] < COMPARE_TTL_SECONDS:
        return hit[1]
    c = lot_service.compare(lot["id"])
    with _cache_lock:
        _compare_cache[lot["id"]] = (time.time(), c)
    return c


def _stored_latest(m: dict[str, Any]) -> dict[str, Any] | None:
    """Latest stored observation (with min/max) of the exact series the comparison used."""
    series = m.get("series")
    if not series:
        return None
    df = data_service.market_prices()
    mask = pd.Series(True, index=df.index)
    for k in F.SERIES_KEYS:
        mask &= df[k].fillna("").astype(str) == str(series.get(k) or "")
    rows = df[mask]
    if rows.empty:
        return None
    r = rows.sort_values("arrival_date").iloc[-1]
    num = lambda v: None if pd.isna(v) else float(v)  # noqa: E731
    return {"arrival_date": str(r["arrival_date"])[:10], "min_price": num(r["min_price"]),
            "max_price": num(r["max_price"]), "modal_price": float(r["modal_price"]),
            "price_unit": r.get("price_unit") or "INR/quintal", "source_kind": r.get("source_kind"),
            "live": False}


def lot_view(lot: dict[str, Any]) -> dict[str, Any]:
    """Lot, its full comparison and the stored market snapshot per mandi. All numbers come from the backend."""
    cmp = _comparison(lot)
    market = {m["market"]: snap for m in cmp["mandis"] if m["available"] and (snap := _stored_latest(m))}
    safe_lot = {k: v for k, v in lot.items() if k != "phone"}
    return {"lot": safe_lot, "summary": _summary(lot), "comparison": cmp, "market": market,
            "source": market_service.local_source().model_dump()}


def live_market(lot: dict[str, Any], market: str) -> dict[str, Any]:
    """Today's price for one of the lot's mandis from data.gov.in, or the stored one, always labelled."""
    if market not in {m["market"] for m in lot["mandis"]}:
        raise NotFoundError("That mandi is not part of this lot.")
    try:
        records, source, meta = market_service.latest_prices(lot["state"], None, market, lot["commodity"])
    except NotFoundError as exc:
        return {"records": [], "source": None, "meta": {"error": exc.message}}
    return {"records": records, "source": source.model_dump(), "meta": meta}


STAGES = ("greeting", "report", "goodbye")


def advisory(lot: dict[str, Any], stage: str, lang: S.Language, with_audio: bool = True) -> dict[str, Any]:
    crop = S.crop_name(lot["commodity"], lang)
    narration_info: dict[str, Any] = {"narration": "fixed", "note": "fixed wording"}
    if stage == "greeting":
        script = S.greeting(crop, lang)
    elif stage == "goodbye":
        script = S.goodbye(lang)
    else:
        view = lot_view(lot)
        body = S.report_body(view, lang, today=date.today())
        narration_info = narration.narrate(body, lang, forbidden=[lot["farmer_name"]])
        script = f"{S.report_intro(lang)} {narration_info['script']}"
    out: dict[str, Any] = {
        "stage": stage, "language": lang, "script": script, "crop": crop,
        "narration": narration_info["narration"], "narration_note": narration_info.get("note"),
        "audio": None, "tts_error": None,
    }
    if with_audio:
        try:
            key, voice = tts.synthesize_cached(lot["id"], stage, lang, script)
            out["audio"] = {"key": key, "voice": voice, "format": "audio/mpeg",
                            "path": f"/mobile/lots/{lot['id']}/audio/{key}"}
        except AppError as exc:  # not configured, timeout, upstream error: text still shown, retry allowed
            out["tts_error"] = {"code": exc.code, "message": exc.message}
    return out


def audio_file(key: str):
    if not re.fullmatch(r"[0-9a-f]{40}", key):
        raise NotFoundError("Unknown audio.")
    path = tts.audio_dir() / f"{key}.mp3"
    if not path.exists():
        raise NotFoundError("Audio not generated yet.")
    return path
