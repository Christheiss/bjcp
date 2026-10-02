from openpyxl import load_workbook

WEIGHTS = {"REQUIRED": 5, "OPTIONAL": 1, "UNEXPECTED": 3, "PROHIBITED": 10}
LEVELS = {"NONE":0, "VERY_LOW":1, "LOW":2, "MEDIUM_LOW":3,
          "MEDIUM":4, "MEDIUM_HIGH":5, "HIGH":6, "VERY_HIGH":7}

def load_rules(xlsx_path, sheet_name="Regras_1A_v2"):
    wb = load_workbook(xlsx_path, data_only=True)
    ws = wb[sheet_name]
    headers = [c.value for c in ws[1]]
    return [dict(zip(headers, row)) for row in ws.iter_rows(min_row=2, values_only=True)]

def range_match(observed, minimum, maximum):
    if observed not in LEVELS or minimum not in LEVELS or maximum not in LEVELS:
        return False
    return LEVELS[minimum] <= LEVELS[observed] <= LEVELS[maximum]

def checkbox_match(observed):
    return str(observed).strip().lower() == "presente"

def calculate(observations, rules):
    by_key = {(r["Seção"], r["Parâmetro"]): r for r in observations}
    required = [r for r in rules if r["Regra"] == "REQUIRED"]
    points = 0
    maximum = len(required) * WEIGHTS["REQUIRED"]
    details = []

    for rule in required:
        obs = by_key.get((rule["Seção"], rule["Parâmetro"]))
        matched = False
        if obs:
            if rule["measurement_type"] == "CHECKBOX":
                matched = checkbox_match(obs["Valor"])
            else:
                matched = range_match(obs["Intensidade"], rule["Min_Linguístico"], rule["Max_Linguístico"])
        points += WEIGHTS["REQUIRED"] if matched else 0
        details.append((rule["Parâmetro"], "REQUIRED", matched))

    unexpected = 0
    prohibited = 0
    for obs in observations:
        key = (obs["Seção"], obs["Parâmetro"])
        matching_rules = [r for r in rules if (r["Seção"], r["Parâmetro"]) == key]
        if not matching_rules and str(obs["Valor"]).lower() == "presente":
            unexpected += 1
            details.append((obs["Parâmetro"], "UNEXPECTED", False))

    penalty = unexpected * WEIGHTS["UNEXPECTED"] + prohibited * WEIGHTS["PROHIBITED"]
    score = 0 if maximum == 0 else max(0, min(100, (points - penalty) / maximum * 100))
    return round(score, 2), details

if __name__ == "__main__":
    print("Motor genérico carregado. Use load_rules() + calculate() para qualquer estilo que possua regras estruturadas.")
