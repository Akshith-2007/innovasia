"""Raithanna advisory scripts (ADR-030): fixed greeting/goodbye texts and a deterministic report template.

Every number in a report comes from lot_service.compare (storage planner + trained forecasts, ADR-023/026).
Nothing here calculates money; it only formats values the backend already computed. The assistant is
always Raithanna (రైతన్న) and the farmer is always addressed as Babai (బాబాయ్), never by name.
"""

from __future__ import annotations

import re
from datetime import date
from typing import Any, Literal

Language = Literal["te", "en"]

# Telugu names for common AGMARKNET commodities (translation only, no data). Unknown crops keep their name.
_CROP_TE: list[tuple[str, str]] = [
    (r"paddy|dhan", "వరి"), (r"\brice\b", "బియ్యం"), (r"tomato", "టమాటా"), (r"onion", "ఉల్లిపాయ"),
    (r"green chilli", "పచ్చిమిర్చి"), (r"dry chill|red chill|chilli red|chillies", "ఎండు మిర్చి"),
    (r"chilli", "మిర్చి"), (r"cotton", "పత్తి"), (r"maize", "మొక్కజొన్న"), (r"groundnut", "వేరుశనగ"),
    (r"brinjal", "వంకాయ"), (r"turmeric", "పసుపు"), (r"potato", "బంగాళాదుంప"), (r"bhindi|ladies finger", "బెండకాయ"),
    (r"cabbage", "క్యాబేజీ"), (r"cauliflower", "కాలీఫ్లవర్"), (r"carrot", "క్యారెట్"), (r"banana", "అరటి"),
    (r"mango", "మామిడి"), (r"arhar|tur\b|red gram", "కంది"), (r"moong|green gram", "పెసర"),
    (r"bengal gram|\bgram\b", "శనగ"), (r"black gram|urad", "మినుము"), (r"jowar", "జొన్న"), (r"bajra", "సజ్జ"),
    (r"ragi", "రాగి"), (r"soyabean|soybean", "సోయాబీన్"), (r"sunflower", "పొద్దుతిరుగుడు"),
    (r"bitter gourd", "కాకరకాయ"), (r"bottle gourd", "సొరకాయ"), (r"cluster beans", "గోరుచిక్కుడు"),
    (r"beans", "బీన్స్"), (r"cucumb", "దోసకాయ"), (r"drumstick", "మునగకాయ"), (r"coriander", "కొత్తిమీర"),
    (r"garlic", "వెల్లుల్లి"), (r"ginger", "అల్లం"), (r"papaya", "బొప్పాయి"), (r"guava", "జామ"),
    (r"pomegranate", "దానిమ్మ"), (r"lemon", "నిమ్మ"), (r"coconut", "కొబ్బరి"), (r"sesam|gingelly", "నువ్వులు"),
]


def crop_name(commodity: str, lang: Language) -> str:
    """Speakable crop name: Telugu word when known, otherwise the commodity without AGMARKNET qualifiers."""
    plain = re.sub(r"\s*\(.*?\)", "", commodity).strip() or commodity
    if lang == "en":
        return plain
    low = commodity.lower()
    return next((te for pat, te in _CROP_TE if re.search(pat, low)), plain)


_MONTHS_TE = ["జనవరి", "ఫిబ్రవరి", "మార్చి", "ఏప్రిల్", "మే", "జూన్", "జూలై", "ఆగస్టు", "సెప్టెంబర్",
              "అక్టోబర్", "నవంబర్", "డిసెంబర్"]
_MONTHS_EN = ["January", "February", "March", "April", "May", "June", "July", "August", "September",
              "October", "November", "December"]
_STORAGE_TE = {"home_ambient": "ఇంటి వద్ద లేదా షెడ్‌లో నిల్వ", "zecc": "జీరో ఎనర్జీ కూల్ ఛాంబర్",
               "onion_ventilated": "గాలి ఆడే ఉల్లి నిల్వ గది", "cold_storage": "అద్దె కోల్డ్ స్టోరేజ్",
               "warehouse": "గోదాము (వేర్‌హౌస్)"}


def spoken_date(iso: str, lang: Language) -> str:
    """'2025-10-17' -> '17 అక్టోబర్ 2025' / '17 October 2025' (ISO dates read badly aloud)."""
    try:
        d = date.fromisoformat(iso[:10])
    except ValueError:
        return iso
    return f"{d.day} {(_MONTHS_TE if lang == 'te' else _MONTHS_EN)[d.month - 1]} {d.year}"


def money(v: float) -> str:
    """Rupees as a whole number with Indian digit grouping (1,17,389)."""
    n = int(round(abs(v)))
    s = str(n)
    if len(s) > 3:
        head, tail = s[:-3], s[-3:]
        head = ",".join([head[max(0, i - 2):i] for i in range(len(head), 0, -2)][::-1])
        s = f"{head},{tail}"
    return s


def qty(v: float) -> str:
    return f"{v:g}"


# --- fixed texts (wording from the product brief) ---------------------------------------------------
def greeting(crop: str, lang: Language) -> str:
    if lang == "te":
        return (f"బాబాయ్... శుభోదయం! నేను రైతన్నను మాట్లాడుతున్నాను. బాబాయ్, మీ {crop} పంట ధరలు "
                "తెలుసుకోవాలనుకుంటున్నారా? తెలుసుకోవాలంటే ఒకటి నొక్కండి. వద్దనుకుంటే రెండు నొక్కండి.")
    return (f"Good morning, Babai! This is Raithanna from Kisan Cold Link. Would you like to know today's prices "
            f"for your {crop}? Press 1 to hear the report, or press 2 if you don't want it now.")


def report_intro(lang: Language) -> str:
    if lang == "te":
        return ("సరే బాబాయ్! ఈరోజు మీ పంట ధరలు, ఏ మండిలో అమ్మితే ఎక్కువ డబ్బులు మిగులుతాయో, "
                "రవాణా ఖర్చులు ఎంత అవుతాయో అన్నీ చెప్తాను. జాగ్రత్తగా వినండి.")
    return ("Alright Babai! I'll tell you today's prices for your crop, which mandi leaves you the most money, "
            "and what transport will cost. Please listen carefully.")


def goodbye(lang: Language) -> str:
    if lang == "te":
        return ("సరే బాబాయ్! ధన్యవాదాలు. మీ రోజు మంచిగా గడవాలని కోరుకుంటున్నాను. మీ పంటకు మంచి ధర "
                "రావాలని ఆశిస్తున్నాను. మళ్లీ మాట్లాడుకుందాం బాబాయ్!")
    return "Alright Babai, thank you! Have a wonderful day. Wishing you a great price for your produce. See you again!"


def not_registered(lang: Language) -> str:
    if lang == "te":
        return "బాబాయ్, మీ వివరాలు ఇంకా నమోదు కాలేదు. దయచేసి మా నిర్వాహకులను సంప్రదించండి."
    return "Babai, your details are not registered yet. Please contact our team."


# --- report template ----------------------------------------------------------------------------------
def _gross(o: dict[str, Any]) -> float:
    return o["sellable_quintals"] * o["price_per_quintal"]


def _reason(reason: str, lang: Language) -> str:
    """Planner reasons are English; the two known ones are translated, anything else is kept as written."""
    if lang == "en":
        return reason
    m = re.search(r"keeps this produce about (\d+) days", reason)
    if m:
        return f"ఈ నిల్వలో పంట సుమారు {m.group(1)} రోజులు మాత్రమే నిలుస్తుంది."
    if reason.startswith("No evaluated forecast"):
        return "ఈ కాలానికి పరీక్షించిన ధరల అంచనా లేదు."
    return reason


def _when(o: dict[str, Any], lang: Language) -> str:
    if o["days"] == 0:
        return "ఇప్పుడే" if lang == "te" else "now"
    return f"{o['days']} రోజులు నిల్వ చేసి" if lang == "te" else f"after storing for {o['days']} days"


def report_body(view: dict[str, Any], lang: Language, today: date | None = None) -> str:
    """Report sections A-E from the deterministic comparison. `view` is mobile_service.lot_view()."""
    today = today or date.today()
    lot, cmp, market = view["lot"], view["comparison"], view.get("market") or {}
    crop = crop_name(lot["commodity"], lang)
    te = lang == "te"
    q = lot["quantity_quintals"]
    out: list[str] = []

    # A. lot summary
    out.append(f"బాబాయ్, నీ దగ్గర ప్రస్తుతం {qty(q)} క్వింటాళ్ల, అంటే {qty(q * 100)} కిలోల {crop} ఉంది."
               if te else f"Babai, you currently have {qty(q)} quintals, that is {qty(q * 100)} kilos, of {crop}.")
    storage = lot.get("storage_option") or "sell_now"
    avail = [m for m in cmp["mandis"] if m["available"]]
    if storage != "sell_now" and avail:
        opt = avail[0]["storage_option"]
        name = _STORAGE_TE.get(opt["id"], opt["name"]) if te else opt["name"]
        out.append(f"నిల్వ కోసం {name} నమోదు చేశారు." if te else f"The storage option on record is {name}.")

    # B. prices (observed, with date and freshness)
    for m in avail:
        obs = market.get(m["market"]) or {}
        d = obs.get("arrival_date") or m["latest_observation"]["date"]
        modal = obs.get("modal_price", m["latest_observation"]["modal_price"])
        stale = d != today.isoformat()
        has_range = (obs.get("min_price") is not None and obs.get("max_price") is not None
                     and obs["min_price"] != obs["max_price"])
        d = spoken_date(d, lang)
        if te:
            line = f"{m['market']} మార్కెట్‌లో {d} నాటికి నమోదైన ధర క్వింటాల్‌కు సుమారుగా {money(modal)} రూపాయలు, అంటే కిలోకు {modal / 100:.0f} రూపాయలు."
            if has_range:
                line += f" కనిష్ఠ ధర {money(obs['min_price'])}, గరిష్ఠ ధర {money(obs['max_price'])} రూపాయలు."
            if stale:
                line += " ఇది నిల్వ ఉన్న అధికారిక సమాచారం, ఈరోజు ప్రత్యక్ష ధర కాదు."
        else:
            line = f"At {m['market']} market, the price recorded on {d} was about {money(modal)} rupees per quintal, that is {modal / 100:.0f} rupees per kilo."
            if has_range:
                line += f" The minimum was {money(obs['min_price'])} and the maximum {money(obs['max_price'])} rupees."
            if stale:
                line += " This is stored official data, not today's live price."
        out.append(line)

    # C. mandi comparison (sell now at each mandi)
    fee_known = lot.get("market_fee_pct") is not None
    for m in avail:
        now = m["options"][0]
        if te:
            line = (f"{m['market']} మండికి {qty(m['distance_km'])} కిలోమీటర్లు దూరం. అక్కడ ఇప్పుడే అమ్మితే వచ్చే మొత్తం "
                    f"{money(_gross(now))} రూపాయలు. రవాణా ఖర్చు {money(now['transport_cost'])} రూపాయలు.")
            line += f" కమీషన్ {money(now['market_fee'])} రూపాయలు." if fee_known else " కమీషన్ వివరాలు నమోదు కాలేదు, అందుకే లెక్కలో చేర్చలేదు."
            line += f" అన్నీ తీసేస్తే మిగిలేది {money(now['net_revenue'])} రూపాయలు." if now["net_revenue"] >= 0 else \
                f" అన్నీ తీసేస్తే {money(now['net_revenue'])} రూపాయల నష్టం."
        else:
            line = (f"{m['market']} mandi is {qty(m['distance_km'])} kilometres away. Selling there now brings "
                    f"{money(_gross(now))} rupees. Transport costs {money(now['transport_cost'])} rupees.")
            line += f" Commission is {money(now['market_fee'])} rupees." if fee_known else " No commission was recorded, so it is not included."
            line += f" After all costs you keep {money(now['net_revenue'])} rupees." if now["net_revenue"] >= 0 else \
                f" After all costs that is a loss of {money(now['net_revenue'])} rupees."
        out.append(line)
    out.append("లోడింగ్, అన్‌లోడింగ్ ఖర్చులు నమోదు కాలేదు, అవి ఈ లెక్కలో లేవు."
               if te else "Loading and unloading charges were not recorded, so they are not included.")
    for m in cmp["mandis"]:
        if not m["available"]:
            out.append(f"{m['market']} మండికి సరిపడా ధరల సమాచారం లేదు, అందుకే అక్కడి లెక్క చెప్పలేను."
                       if te else f"There is not enough price data for {m['market']}, so I can't give figures there.")

    # D. selling versus storage (best mandi only)
    rec = cmp.get("recommendation")
    best = next((m for m in avail if rec and m["market"] == rec["market"]), None)
    if storage == "sell_now":
        out.append("నిల్వ ఎంపిక నమోదు కాలేదు, అందుకే ఇప్పుడే అమ్మే లెక్క మాత్రమే చెప్పాను."
                   if te else "No storage option is on record, so I only compared selling now.")
    elif best:
        for o in best["options"][1:]:
            mape = o.get("forecast_test_mape")
            if te:
                line = (f"{best['market']}లో {o['days']} రోజులు నిల్వ చేసి అమ్మితే అంచనా ధర క్వింటాల్‌కు {money(o['price_per_quintal'])} రూపాయలు. "
                        f"నిల్వ ఖర్చు {money(o['storage_cost'])} రూపాయలు, నష్టం తర్వాత అమ్మే సరుకు {qty(round(o['sellable_quintals'], 2))} క్వింటాళ్లు. "
                        f"మిగిలేది {money(o['net_revenue'])} రూపాయలు.")
                if mape is not None:
                    line += f" ఇది అంచనా మాత్రమే, పరీక్షలో సగటు తేడా సుమారు {mape:.0f} శాతం."
            else:
                line = (f"Storing for {o['days']} days and selling at {best['market']}: forecast price {money(o['price_per_quintal'])} rupees per quintal, "
                        f"storage cost {money(o['storage_cost'])} rupees, {qty(round(o['sellable_quintals'], 2))} quintals left after losses, "
                        f"leaving {money(o['net_revenue'])} rupees.")
                if mape is not None:
                    line += f" This is only a forecast; in testing it was off by about {mape:.0f} percent on average."
            out.append(line)
        for u in best.get("unavailable_horizons", []):
            out.append(f"{u['days']} రోజుల నిల్వ లెక్క చెప్పలేను: {_reason(u['reason'], lang)}" if te
                       else f"I can't give a {u['days']}-day storage figure: {u['reason']}")

    # E. recommendation (decision stays with the farmer)
    if rec:
        o = rec["option"]
        if o["net_revenue"] >= 0:
            out.append(f"నా లెక్క ప్రకారం బాబాయ్, {rec['market']}లో {_when(o, lang)} అమ్మితే అన్ని ఖర్చులు తీసేసిన తర్వాత సుమారుగా "
                       f"{money(o['net_revenue'])} రూపాయలు మిగిలే అవకాశం ఉంది. అందుకే ఆ మండిని ఒకసారి పరిశీలించమని చెప్తున్నాను."
                       if te else
                       f"By my calculation, Babai, selling at {rec['market']} {_when(o, lang)} could leave you about "
                       f"{money(o['net_revenue'])} rupees after all costs. That's why I suggest you consider that mandi.")
        else:
            out.append(f"బాబాయ్, అన్ని ఎంపికల్లోనూ ఖర్చులు ఎక్కువగా ఉన్నాయి. తక్కువ నష్టం {rec['market']}లో, సుమారు {money(o['net_revenue'])} రూపాయలు."
                       if te else
                       f"Babai, every option costs more than it brings in. The smallest loss is at {rec['market']}, about {money(o['net_revenue'])} rupees.")
        gain = o.get("vs_sell_now")
        if o["days"] > 0 and gain is not None and best and gain < 0.02 * abs(best["options"][0]["net_revenue"]):
            # Stated rule: a storage gain under 2% of selling now is smaller than the forecast's tested error.
            out.append(f"కానీ బాబాయ్, ఇప్పుడే అమ్మడానికి, నిల్వ చేసి అమ్మడానికి తేడా కేవలం {money(gain)} రూపాయలే. అంచనాలో తేడా దీనికంటే ఎక్కువ ఉండవచ్చు, కాబట్టి ఇప్పుడే అమ్మడం కూడా మంచి ఎంపికే."
                       if te else
                       f"But Babai, storing beats selling now by only {money(gain)} rupees, which is smaller than the forecast's usual error, so selling now is also a sound choice.")
        out.append("చివరి నిర్ణయం మీదే బాబాయ్." if te else "The final decision is always yours, Babai.")
    else:
        out.append("బాబాయ్, ఈ మండీల్లో దేనికీ నమ్మదగిన లెక్క చేయలేకపోయాను, అందుకే ఏ సలహా ఇవ్వడం లేదు."
                   if te else "Babai, I couldn't make a reliable calculation for any of these mandis, so I'm not giving a recommendation.")
    return " ".join(out)
