"""
Motor de matching BJCP — versão inicial
---------------------------------------
Este módulo é separado da interface Streamlit.

Entrada:
    observations: lista de observações sensoriais
    rules: lista de regras estruturadas do estilo

Saída:
    score: compatibilidade de 0 a 100
    details: detalhamento das regras avaliadas
"""

WEIGHTS = {
    "REQUIRED": 5,
    "OPTIONAL": 1,
    "UNEXPECTED": 3,
    "PROHIBITED": 10,
}

LEVELS = {
    "NONE": 0,
    "VERY_LOW": 1,
    "LOW": 2,
    "MEDIUM_LOW": 3,
    "MEDIUM": 4,
    "MEDIUM_HIGH": 5,
    "HIGH": 6,
    "VERY_HIGH": 7,
}


def _text(value):
    if value is None:
        return ""
    return str(value).strip()


def _level(value):
    return LEVELS.get(_text(value).upper())


def compare_range(observed, minimum, maximum):
    """
    Compara uma intensidade observada com o intervalo linguístico
    definido pela regra.
    """
    obs = _level(observed)
    lo = _level(minimum)
    hi = _level(maximum)

    if obs is None or lo is None or hi is None:
        return False

    return lo <= obs <= hi


def compare_checkbox(value):
    return _text(value).lower() == "presente"


def _matches(rule, observation):
    if observation is None:
        return False

    measurement_type = _text(
        rule.get("measurement_type")
    ).upper()

    if measurement_type == "CHECKBOX":
        return compare_checkbox(observation.get("Valor"))

    return compare_range(
        observation.get("Intensidade"),
        rule.get("Min_Linguístico"),
        rule.get("Max_Linguístico"),
    )


def calculate(observations, rules):
    """
    Calcula a compatibilidade de uma avaliação com um estilo.

    REQUIRED:
        cada regra atendida recebe peso 5.

    OPTIONAL:
        não aumenta o teto da pontuação e não penaliza quando ausente.

    UNEXPECTED:
        uma característica presente sem regra correspondente gera
        penalidade 3.

    PROHIBITED:
        uma característica explicitamente proibida gera penalidade 10.
    """

    observations = observations or []
    rules = rules or []

    # Indexa as observações pela dimensão sensorial + parâmetro.
    observation_map = {}

    for obs in observations:
        key = (
            _text(obs.get("Seção")),
            _text(obs.get("Parâmetro")),
        )
        observation_map[key] = obs

    required_rules = [
        r for r in rules
        if _text(r.get("Regra")).upper() == "REQUIRED"
    ]

    points = 0
    maximum = len(required_rules) * WEIGHTS["REQUIRED"]

    details = []

    # -----------------------------------------------------
    # REQUIRED
    # -----------------------------------------------------
    for rule in required_rules:
        key = (
            _text(rule.get("Seção")),
            _text(rule.get("Parâmetro")),
        )

        observation = observation_map.get(key)
        matched = _matches(rule, observation)

        if matched:
            points += WEIGHTS["REQUIRED"]

        details.append([
            rule.get("Parâmetro"),
            "REQUIRED",
            matched,
        ])

    # -----------------------------------------------------
    # Detecta características presentes sem regra.
    # -----------------------------------------------------
    rule_keys = {
        (
            _text(r.get("Seção")),
            _text(r.get("Parâmetro")),
        )
        for r in rules
    }

    unexpected = 0

    for obs in observations:
        key = (
            _text(obs.get("Seção")),
            _text(obs.get("Parâmetro")),
        )

        if key not in rule_keys:
            if _text(obs.get("Valor")).lower() == "presente":
                unexpected += 1

                details.append([
                    obs.get("Parâmetro"),
                    "UNEXPECTED",
                    False,
                ])

    # -----------------------------------------------------
    # PROHIBITED explícito
    # -----------------------------------------------------
    prohibited = 0

    for rule in rules:
        if _text(rule.get("Regra")).upper() != "PROHIBITED":
            continue

        key = (
            _text(rule.get("Seção")),
            _text(rule.get("Parâmetro")),
        )

        observation = observation_map.get(key)

        if observation is not None and _text(
            observation.get("Valor")
        ).lower() == "presente":
            prohibited += 1

            details.append([
                rule.get("Parâmetro"),
                "PROHIBITED",
                False,
            ])

    # -----------------------------------------------------
    # Resultado
    # -----------------------------------------------------
    penalty = (
        unexpected * WEIGHTS["UNEXPECTED"]
        + prohibited * WEIGHTS["PROHIBITED"]
    )

    if maximum <= 0:
        score = 0.0
    else:
        score = ((points - penalty) / maximum) * 100

    score = max(0.0, min(100.0, score))

    return round(score, 2), details
