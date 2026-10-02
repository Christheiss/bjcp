LEVELS = {
    "AUSENTE": 0, "VERY_LOW": 1, "LOW": 2, "MEDIUM_LOW": 3,
    "MEDIUM": 4, "MEDIUM_HIGH": 5, "HIGH": 6, "VERY_HIGH": 7,
}

BEER_COLORS = {"Palha": 0, "Amarelo": 1, "Ouro": 2, "Âmbar": 3, "Cobre": 4, "Marrom": 5, "Preto": 6}
HEAD_COLORS = {"Branco": 0, "Marfim": 1, "Creme": 2, "Bege": 3, "Moreno": 4, "Marrom": 5}

def _text(v):
    return str(v or "").strip()

def _level(v):
    return LEVELS.get(_text(v).upper())

def _color_match(obs, rule):
    palette = BEER_COLORS if _text(rule.get("range_type")).upper() == "COLOR_BEER" else HEAD_COLORS
    value = palette.get(_text(obs.get("Valor")))
    if value is None:
        return False
    lo_raw, hi_raw = rule.get("Min_Operacional"), rule.get("Max_Operacional")
    try:
        lo = palette.get(_text(lo_raw), int(lo_raw))
    except (ValueError, TypeError):
        lo = palette.get(_text(lo_raw))
    try:
        hi = palette.get(_text(hi_raw), int(hi_raw))
    except (ValueError, TypeError):
        hi = palette.get(_text(hi_raw))
    return lo is not None and hi is not None and lo <= value <= hi

def _matches(rule, obs):
    if obs is None:
        return False
    measurement = _text(rule.get("measurement_type")).upper()
    range_type = _text(rule.get("range_type")).upper()
    if measurement == "CHECKBOX":
        return _text(obs.get("Valor")).lower() == "presente"
    if range_type in ("COLOR_BEER", "COLOR_HEAD"):
        return _color_match(obs, rule)
    obs_v, lo_v, hi_v = _level(obs.get("Intensidade")), _level(rule.get("Min_Linguístico")), _level(rule.get("Max_Linguístico"))
    return obs_v is not None and lo_v is not None and hi_v is not None and lo_v <= obs_v <= hi_v

def calculate(observations, rules):
    obs_map = {(_text(o.get("Seção")), _text(o.get("Parâmetro"))): o for o in observations}
    details, matched, evaluated = [], 0, 0

    for rule in rules:
        rt = _text(rule.get("Regra")).upper()
        if rt not in ("REQUIRED", "OPTIONAL", "PROHIBITED"):
            continue
        key = (_text(rule.get("Seção")), _text(rule.get("Parâmetro")))
        obs = obs_map.get(key)
        if rt == "OPTIONAL":
            if obs is None:
                continue
            mt = _text(rule.get("measurement_type")).upper()
            if mt == "CHECKBOX":
                if _text(obs.get("Valor")).lower() != "presente":
                    continue
            elif _text(obs.get("Intensidade")).upper() == "AUSENTE":
                continue
        if rt == "PROHIBITED":
            if obs is None or _text(obs.get("Valor")).lower() != "presente":
                continue

        evaluated += 1
        ok = _matches(rule, obs)
        matched += int(ok)
        details.append({
            "Seção": rule.get("Seção"),
            "Parâmetro": rule.get("Parâmetro"),
            "Regra": rt,
            "Observado": obs.get("Valor") if obs else "Ausente",
            "Compatível": ok,
        })

    rule_keys = {(_text(r.get("Seção")), _text(r.get("Parâmetro"))) for r in rules}
    for obs in observations:
        key = (_text(obs.get("Seção")), _text(obs.get("Parâmetro")))
        if key not in rule_keys and _text(obs.get("Valor")).lower() == "presente":
            evaluated += 1
            details.append({
                "Seção": obs.get("Seção"),
                "Parâmetro": obs.get("Parâmetro"),
                "Regra": "UNEXPECTED",
                "Observado": "Presente",
                "Compatível": False,
            })

    return {"matched": matched, "evaluated": evaluated, "display": f"{matched} / {evaluated}"}, details
