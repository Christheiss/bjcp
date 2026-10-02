"""
BJCP Matching Engine v5

Two-stage logic:
1) Eliminatory rules:
   - REQUIRED not satisfied => style eliminated
   - UNEXPECTED detected => style eliminated
   - PROHIBITED detected => style eliminated
2) Surviving styles are compared using non-eliminatory parameters:
   - OPTIONAL
   - ranges/intensities/colors/balance
   - other compatible characteristics

The engine returns a dictionary for the selected style and also exposes
rank_styles() for the Possibilities tab.
"""

LEVELS = {
    "AUSENTE": 0,
    "VERY_LOW": 1,
    "LOW": 2,
    "MEDIUM_LOW": 3,
    "MEDIUM": 4,
    "MEDIUM_HIGH": 5,
    "HIGH": 6,
    "VERY_HIGH": 7,
}

BEER_COLORS = {
    "Palha": 0,
    "Amarelo": 1,
    "Ouro": 2,
    "Âmbar": 3,
    "Cobre": 4,
    "Marrom": 5,
    "Preto": 6,
}

HEAD_COLORS = {
    "Branco": 0,
    "Marfim": 1,
    "Creme": 2,
    "Bege": 3,
    "Moreno": 4,
    "Marrom": 5,
}

def _s(v):
    return "" if v is None else str(v).strip()

def _upper(v):
    return _s(v).upper()

def _is_present(obs):
    return _s(obs.get("Valor")).lower() == "presente"

def _obs_code(obs):
    return _upper(obs.get("Intensidade"))

def _range_match(obs, rule):
    range_type = _upper(rule.get("range_type"))

    if range_type == "COLOR_BEER":
        value = _s(obs.get("Valor"))
        if value not in BEER_COLORS:
            return False
        lo = _s(rule.get("Min_Operacional"))
        hi = _s(rule.get("Max_Operacional"))
        if lo in BEER_COLORS and hi in BEER_COLORS:
            return BEER_COLORS[lo] <= BEER_COLORS[value] <= BEER_COLORS[hi]
        return False

    if range_type == "COLOR_HEAD":
        value = _s(obs.get("Valor"))
        if value not in HEAD_COLORS:
            return False
        lo = _s(rule.get("Min_Operacional"))
        hi = _s(rule.get("Max_Operacional"))
        if lo in HEAD_COLORS and hi in HEAD_COLORS:
            return HEAD_COLORS[lo] <= HEAD_COLORS[value] <= HEAD_COLORS[hi]
        return False

    obs_level = LEVELS.get(_obs_code(obs))
    min_level = LEVELS.get(_upper(rule.get("Min_Linguístico")))
    max_level = LEVELS.get(_upper(rule.get("Max_Linguístico")))

    if obs_level is None or min_level is None or max_level is None:
        return False

    return min_level <= obs_level <= max_level

def _matches(obs, rule):
    measurement = _upper(rule.get("measurement_type"))
    rule_type = _upper(rule.get("Regra"))

    if measurement == "CHECKBOX":
        present = _is_present(obs)
        if rule_type == "PROHIBITED":
            return not present
        if rule_type == "REQUIRED":
            return present
        if rule_type == "UNEXPECTED":
            return not present
        if rule_type == "OPTIONAL":
            return True if not present else True
        return True

    return _range_match(obs, rule)

def _key(item):
    return (_s(item.get("Seção")), _s(item.get("Parâmetro")))

def _rule_groups(rule_records):
    groups = {}
    for rule in rule_records:
        groups.setdefault(_key(rule), []).append(rule)
    return groups

def _observation_map(observations):
    return {_key(o): o for o in observations}

def evaluate_style(observations, rule_records):
    """
    Evaluate one style's structured rules.

    Returns:
      eliminated: bool
      elimination_reasons: list
      matched: int
      evaluated: int
      display: "matched / evaluated"
      details: list of tuples
    """
    obs_map = _observation_map(observations)
    matched = 0
    evaluated = 0
    details = []
    elimination_reasons = []

    for rule in rule_records:
        rtype = _upper(rule.get("Regra"))
        key = _key(rule)
        obs = obs_map.get(key)

        if rtype == "REQUIRED":
            evaluated += 1
            ok = obs is not None and _matches(obs, rule)
            if ok:
                matched += 1
            else:
                elimination_reasons.append(
                    f"REQUIRED não atendido: {_s(rule.get('Seção'))} / {_s(rule.get('Parâmetro'))}"
                )
            details.append((_s(rule.get("Parâmetro")), rtype, ok))
            continue

        if rtype in ("UNEXPECTED", "PROHIBITED"):
            # Only a detected characteristic creates an elimination.
            if obs is not None and _is_present(obs):
                evaluated += 1
                ok = False
                elimination_reasons.append(
                    f"{rtype} detectado: {_s(rule.get('Seção'))} / {_s(rule.get('Parâmetro'))}"
                )
                details.append((_s(rule.get("Parâmetro")), rtype, ok))
            continue

        if rtype == "OPTIONAL":
            if obs is None:
                continue

            # Optional checkbox only matters when present.
            if _upper(rule.get("measurement_type")) == "CHECKBOX":
                if not _is_present(obs):
                    continue
            else:
                if _obs_code(obs) == "AUSENTE":
                    continue

            evaluated += 1
            ok = _matches(obs, rule)
            if ok:
                matched += 1
            details.append((_s(rule.get("Parâmetro")), rtype, ok))

    eliminated = bool(elimination_reasons)

    return {
        "eliminated": eliminated,
        "elimination_reasons": elimination_reasons,
        "matched": matched,
        "evaluated": evaluated,
        "display": f"{matched} / {evaluated}",
        "details": details,
    }

def calculate(observations, rule_records):
    result = evaluate_style(observations, rule_records)
    return (
        {
            "matched": result["matched"],
            "evaluated": result["evaluated"],
            "display": result["display"],
            "eliminated": result["eliminated"],
            "elimination_reasons": result["elimination_reasons"],
        },
        result["details"],
    )

def rank_styles(observations, rules_df):
    """
    Rank styles using the agreed two-stage logic.

    Expected columns in rules_df:
      Estilo/Código or style identifier, plus the normal rule columns.

    Returns a list of survivors sorted by matched/evaluated.
    """
    if hasattr(rules_df, "to_dict"):
        rows = rules_df.to_dict("records")
    else:
        rows = list(rules_df)

    # Identify a style column without assuming one exact spelling.
    style_col = next(
        (
            c for c in ("Código", "Codigo", "Código_Estilo", "Estilo", "Style")
            if rows and c in rows[0]
        ),
        None,
    )

    if style_col is None:
        return []

    by_style = {}
    for row in rows:
        style_id = _s(row.get(style_col))
        if not style_id:
            continue
        by_style.setdefault(style_id, []).append(row)

    ranked = []

    for style_id, rules in by_style.items():
        result = evaluate_style(observations, rules)

        if result["eliminated"]:
            continue

        ranked.append({
            "Código": style_id,
            "Estilo": style_id,
            "matched": result["matched"],
            "evaluated": result["evaluated"],
            "display": result["display"],
            "eliminated": False,
            "elimination_reasons": [],
        })

    ranked.sort(
        key=lambda x: (
            x["matched"],
            x["matched"] / x["evaluated"] if x["evaluated"] else 0,
            x["evaluated"],
        ),
        reverse=True,
    )

    return ranked
