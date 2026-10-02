import streamlit as st
from pathlib import Path
import pandas as pd
import importlib.util

st.set_page_config(
    page_title="BJCP Style Matcher",
    page_icon="🍺",
    layout="wide",
)

# =========================================================
# LOCALIZAÇÃO DOS ARQUIVOS
# =========================================================
BASE = Path(__file__).resolve().parent
DATA_DIR = BASE / "data"

# No seu GitHub, o Excel está em:
# data/bjcp_database.xlsx
DB_CANDIDATES = [
    DATA_DIR / "bjcp_database.xlsx",
    BASE / "bjcp_database.xlsx",
]

MOTOR_CANDIDATES = [
    BASE / "motor_matching_v3_generico.py",
    DATA_DIR / "motor_matching_v3_generico.py",
]


def find_database():
    for path in DB_CANDIDATES:
        if path.exists():
            return path
    return None


def load_motor():
    for path in MOTOR_CANDIDATES:
        if path.exists():
            spec = importlib.util.spec_from_file_location("bjcp_motor", path)
            motor = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(motor)
            return motor
    return None


@st.cache_data
def load_sheet(path, sheet_name):
    return pd.read_excel(path, sheet_name=sheet_name)


# =========================================================
# MOTOR DE EMERGÊNCIA
# =========================================================
# Permite que o app continue funcionando mesmo se o arquivo
# motor_matching_v3_generico.py ainda não tiver sido enviado.
def fallback_calculate(observations, rules):
    levels = {
        "NONE": 0,
        "VERY_LOW": 1,
        "LOW": 2,
        "MEDIUM_LOW": 3,
        "MEDIUM": 4,
        "MEDIUM_HIGH": 5,
        "HIGH": 6,
        "VERY_HIGH": 7,
    }

    required_weight = 5
    unexpected_weight = 3
    prohibited_weight = 10

    required = [
        r for r in rules
        if str(r.get("Regra", "")).upper() == "REQUIRED"
    ]

    obs_map = {
        (o["Seção"], o["Parâmetro"]): o
        for o in observations
    }

    points = 0
    details = []

    for rule in required:
        key = (rule.get("Seção"), rule.get("Parâmetro"))
        obs = obs_map.get(key)
        matched = False

        if obs is not None:
            if str(rule.get("measurement_type", "")).upper() == "CHECKBOX":
                matched = str(obs["Valor"]).lower() == "presente"
            else:
                observed = obs.get("Intensidade")
                lo = rule.get("Min_Linguístico")
                hi = rule.get("Max_Linguístico")

                if observed in levels and lo in levels and hi in levels:
                    matched = levels[lo] <= levels[observed] <= levels[hi]

        if matched:
            points += required_weight

        details.append([
            rule.get("Parâmetro"),
            "REQUIRED",
            matched,
        ])

    unexpected = 0

    for obs in observations:
        key = (obs["Seção"], obs["Parâmetro"])

        if (
            key not in {
                (r.get("Seção"), r.get("Parâmetro"))
                for r in rules
            }
            and str(obs["Valor"]).lower() == "presente"
        ):
            unexpected += 1
            details.append([
                obs["Parâmetro"],
                "UNEXPECTED",
                False,
            ])

    maximum = len(required) * required_weight
    penalty = unexpected * unexpected_weight

    score = 0 if maximum == 0 else ((points - penalty) / maximum) * 100
    score = max(0, min(100, score))

    return round(score, 2), details


# =========================================================
# INÍCIO
# =========================================================
st.title("🍺 BJCP Style Matcher")
st.caption(
    "Protótipo de identificação de estilo baseado em regras estruturadas do BJCP."
)

db = find_database()

if db is None:
    st.error("Banco Excel não encontrado.")
    st.write("O aplicativo está procurando em:")
    st.code(str(DATA_DIR / "bjcp_database.xlsx"))
    st.write("Confirme que o arquivo está em:")
    st.code("data/bjcp_database.xlsx")
    st.stop()

motor = load_motor()

if motor is None:
    st.warning(
        "O arquivo motor_matching_v3_generico.py não foi encontrado. "
        "O app usará o motor interno de emergência."
    )

st.success(f"Banco carregado: {db.relative_to(BASE)}")


# =========================================================
# REGRAS
# =========================================================
excel = pd.ExcelFile(db)

possible_rule_sheets = [
    "Regras_1A_v2",
    "Regras_1A",
]

rule_sheet = next(
    (s for s in possible_rule_sheets if s in excel.sheet_names),
    None,
)

if rule_sheet is None:
    st.error(
        "Não encontrei uma aba de regras estruturadas para o estilo 1A."
    )
    st.write("Abas encontradas no Excel:")
    st.code("\n".join(excel.sheet_names))
    st.stop()

rules = load_sheet(db, rule_sheet)


# =========================================================
# SIDEBAR
# =========================================================
with st.sidebar:
    st.header("Configuração")

    st.selectbox(
        "Estilo para testar",
        ["1A — American Light Lager"],
    )

    st.divider()

    st.write("**Banco**")
    st.code(str(db.relative_to(BASE)))

    st.write("**Aba de regras**")
    st.code(rule_sheet)

    if motor:
        st.write("**Motor**")
        st.code("motor_matching_v3_generico.py")
    else:
        st.write("**Motor**")
        st.code("interno / emergência")


# =========================================================
# ENTRADA SENSORIAL
# =========================================================
st.header("1. Avaliação sensorial")

tabs = st.tabs([
    "🌸 Aroma",
    "👁️ Aparência",
    "👅 Sabor",
    "💧 Sensação na boca",
])

observations = []

LEVEL_OPTIONS = [
    "NONE",
    "VERY_LOW",
    "LOW",
    "MEDIUM_LOW",
    "MEDIUM",
    "MEDIUM_HIGH",
    "HIGH",
    "VERY_HIGH",
]


def add_range(section, parameter, label):
    value = st.selectbox(
        label,
        LEVEL_OPTIONS,
        key=f"{section}_{parameter}",
    )

    observations.append({
        "Seção": section,
        "Parâmetro": parameter,
        "Tipo": "RANGE",
        "Valor": value,
        "Intensidade": value,
    })


def add_checkbox(section, parameter, label):
    value = st.checkbox(
        label,
        key=f"{section}_{parameter}",
    )

    observations.append({
        "Seção": section,
        "Parâmetro": parameter,
        "Tipo": "CHECKBOX",
        "Valor": "presente" if value else "ausente",
        "Intensidade": "",
    })


with tabs[0]:
    st.subheader("Aroma")

    add_range("Aroma", "Malte", "Intensidade de malte")
    add_checkbox("Aroma", "Floral", "Floral")
    add_checkbox("Aroma", "Herbal", "Herbal")
    add_checkbox("Aroma", "Especiaria", "Especiaria")


with tabs[1]:
    st.subheader("Aparência")

    cor = st.selectbox(
        "Cor da cerveja",
        ["Palha", "Amarelo", "Dourado", "Âmbar", "Cobre", "Marrom", "Preto"],
    )

    observations.append({
        "Seção": "Aparência",
        "Parâmetro": "Cor da cerveja",
        "Tipo": "RANGE",
        "Valor": cor,
        "Intensidade": "LOW" if cor in ["Palha", "Amarelo"] else "MEDIUM",
    })

    colarinho = st.selectbox(
        "Cor do colarinho",
        ["Branco", "Marfim", "Creme", "Bege", "Moreno", "Marrom"],
    )

    observations.append({
        "Seção": "Aparência",
        "Parâmetro": "Cor do colarinho",
        "Tipo": "RANGE",
        "Valor": colarinho,
        "Intensidade": "",
    })

    add_range("Aparência", "Limpidez", "Limpidez")
    add_range("Aparência", "Retenção do colarinho", "Retenção do colarinho")


with tabs[2]:
    st.subheader("Sabor")

    add_range("Sabor", "Malte", "Intensidade de malte")
    add_range("Sabor", "Amargor", "Amargor")

    add_checkbox("Sabor", "Cítrico", "Cítrico")
    add_checkbox("Sabor", "Floral", "Floral")
    add_checkbox("Sabor", "Herbal", "Herbal")
    add_checkbox("Sabor", "Especiaria", "Especiaria")


with tabs[3]:
    st.subheader("Sensação na boca")

    add_range("Sensação na Boca", "Corpo", "Corpo")
    add_range("Sensação na Boca", "Carbonatação", "Carbonatação")


# =========================================================
# RESULTADO
# =========================================================
st.divider()
st.header("2. Resultado")

if st.button(
    "🍺 Calcular compatibilidade",
    type="primary",
    use_container_width=True,
):

    try:
        if motor and hasattr(motor, "calculate"):
            score, details = motor.calculate(
                observations,
                rules.to_dict("records"),
            )
        else:
            score, details = fallback_calculate(
                observations,
                rules.to_dict("records"),
            )

        col1, col2, col3 = st.columns(3)

        col1.metric(
            "Compatibilidade",
            f"{score:.2f}%",
        )

        col2.metric(
            "Estilo",
            "1A",
        )

        col3.metric(
            "Regras avaliadas",
            len(details),
        )

        if score >= 80:
            st.success("Alta compatibilidade operacional.")
        elif score >= 60:
            st.warning("Compatibilidade intermediária.")
        else:
            st.error("Baixa compatibilidade operacional.")

        st.subheader("Detalhamento")

        detail_df = pd.DataFrame(
            details,
            columns=[
                "Parâmetro",
                "Regra",
                "Compatível",
            ],
        )

        st.dataframe(
            detail_df,
            use_container_width=True,
            hide_index=True,
        )

        with st.expander("Ver observações enviadas"):
            st.dataframe(
                pd.DataFrame(observations),
                use_container_width=True,
                hide_index=True,
            )

    except Exception as e:
        st.error(f"Erro no cálculo: {e}")
        st.exception(e)


st.divider()

st.caption(
    "Protótipo em desenvolvimento. Pesos, escalas operacionais e fórmula "
    "de compatibilidade são regras do aplicativo, não uma pontuação oficial do BJCP."
)
