import streamlit as st
from pathlib import Path
import pandas as pd
import importlib.util

st.set_page_config(
    page_title="BJCP Style Matcher",
    page_icon="🍺",
    layout="wide",
)

BASE = Path(__file__).resolve().parent

# Arquivos esperados no mesmo diretório do app
MOTOR_FILE = BASE / "motor_matching_v3_generico.py"
DB_CANDIDATES = [
    BASE / "bjcp_database_v29_motor_generico.xlsx",
    BASE / "bjcp_database_v26_motor_python_1A.xlsx",
    BASE / "bjcp_database_v25_calculo_matching_1A.xlsx",
]

def load_motor():
    if not MOTOR_FILE.exists():
        return None
    spec = importlib.util.spec_from_file_location("bjcp_motor", MOTOR_FILE)
    motor = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(motor)
    return motor

def find_database():
    for path in DB_CANDIDATES:
        if path.exists():
            return path
    return None

@st.cache_data
def load_sheet(path, sheet_name):
    return pd.read_excel(path, sheet_name=sheet_name)

st.title("🍺 BJCP Style Matcher")
st.caption("Protótipo de identificação de estilo baseado em regras estruturadas do BJCP.")

db = find_database()
motor = load_motor()

if db is None:
    st.error(
        "Banco Excel não encontrado. Coloque o arquivo do banco na mesma pasta "
        "do streamlit_app.py."
    )
    st.stop()

if motor is None:
    st.error(
        "motor_matching_v3_generico.py não encontrado. "
        "Coloque o motor na mesma pasta do streamlit_app.py."
    )
    st.stop()

st.success(f"Banco carregado: {db.name}")

# ---------------------------------------------------------
# Carregamento das regras
# ---------------------------------------------------------
try:
    rules = load_sheet(db, "Regras_1A_v2")
except Exception as e:
    st.error(f"Não foi possível carregar a aba Regras_1A_v2: {e}")
    st.stop()

# ---------------------------------------------------------
# Sidebar
# ---------------------------------------------------------
with st.sidebar:
    st.header("Configuração")

    style = st.selectbox(
        "Estilo para testar",
        ["1A — American Light Lager"],
    )

    st.divider()
    st.write("**Arquivos**")
    st.code(db.name)
    st.code("motor_matching_v3_generico.py")

# ---------------------------------------------------------
# Entrada sensorial
# ---------------------------------------------------------
st.header("1. Avaliação sensorial")

tab_aroma, tab_aparencia, tab_sabor, tab_boca = st.tabs(
    ["🌸 Aroma", "👁️ Aparência", "👅 Sabor", "💧 Sensação na boca"]
)

observations = []

def add_range_observation(section, parameter, label, levels):
    value = st.selectbox(label, levels, key=f"{section}_{parameter}")
    observations.append({
        "Seção": section,
        "Parâmetro": parameter,
        "Tipo": "RANGE",
        "Valor": value,
        "Intensidade": value,
    })

def add_checkbox_observation(section, parameter, label):
    present = st.checkbox(label, key=f"{section}_{parameter}")
    observations.append({
        "Seção": section,
        "Parâmetro": parameter,
        "Tipo": "CHECKBOX",
        "Valor": "presente" if present else "ausente",
        "Intensidade": "",
    })

with tab_aroma:
    st.subheader("Aroma")

    add_range_observation(
        "Aroma", "Malte", "Intensidade de malte",
        ["NONE", "VERY_LOW", "LOW", "MEDIUM_LOW", "MEDIUM", "MEDIUM_HIGH", "HIGH", "VERY_HIGH"]
    )

    add_checkbox_observation("Aroma", "Floral", "Floral")
    add_checkbox_observation("Aroma", "Herbal", "Herbal")
    add_checkbox_observation("Aroma", "Especiaria", "Especiaria")

with tab_aparencia:
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

    add_range_observation(
        "Aparência", "Limpidez", "Limpidez",
        ["NONE", "VERY_LOW", "LOW", "MEDIUM_LOW", "MEDIUM", "MEDIUM_HIGH", "HIGH", "VERY_HIGH"]
    )

    add_range_observation(
        "Aparência", "Retenção do colarinho", "Retenção do colarinho",
        ["NONE", "VERY_LOW", "LOW", "MEDIUM_LOW", "MEDIUM", "MEDIUM_HIGH", "HIGH", "VERY_HIGH"]
    )

with tab_sabor:
    st.subheader("Sabor")

    add_range_observation(
        "Sabor", "Malte", "Intensidade de malte",
        ["NONE", "VERY_LOW", "LOW", "MEDIUM_LOW", "MEDIUM", "MEDIUM_HIGH", "HIGH", "VERY_HIGH"]
    )

    add_range_observation(
        "Sabor", "Amargor", "Amargor",
        ["NONE", "VERY_LOW", "LOW", "MEDIUM_LOW", "MEDIUM", "MEDIUM_HIGH", "HIGH", "VERY_HIGH"]
    )

    add_checkbox_observation("Sabor", "Cítrico", "Cítrico")
    add_checkbox_observation("Sabor", "Floral", "Floral")
    add_checkbox_observation("Sabor", "Herbal", "Herbal")
    add_checkbox_observation("Sabor", "Especiaria", "Especiaria")

with tab_boca:
    st.subheader("Sensação na boca")

    add_range_observation(
        "Sensação na Boca", "Corpo", "Corpo",
        ["NONE", "VERY_LOW", "LOW", "MEDIUM_LOW", "MEDIUM", "MEDIUM_HIGH", "HIGH", "VERY_HIGH"]
    )

    add_range_observation(
        "Sensação na Boca", "Carbonatação", "Carbonatação",
        ["NONE", "VERY_LOW", "LOW", "MEDIUM_LOW", "MEDIUM", "MEDIUM_HIGH", "HIGH", "VERY_HIGH"]
    )

# ---------------------------------------------------------
# Resultado
# ---------------------------------------------------------
st.divider()
st.header("2. Resultado")

if st.button("🍺 Calcular compatibilidade", type="primary", use_container_width=True):
    try:
        score, details = motor.calculate(observations, rules)

        col1, col2, col3 = st.columns(3)
        col1.metric("Compatibilidade", f"{score:.2f}%")
        col2.metric("Estilo", "1A")
        col3.metric("Regras avaliadas", len(details))

        if score >= 80:
            st.success("Alta compatibilidade operacional.")
        elif score >= 60:
            st.warning("Compatibilidade intermediária.")
        else:
            st.error("Baixa compatibilidade operacional.")

        st.subheader("Detalhamento")

        detail_df = pd.DataFrame(
            details,
            columns=["Parâmetro", "Regra", "Compatível"]
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
    "Protótipo em desenvolvimento. Pesos, escalas operacionais e fórmula de "
    "compatibilidade são regras do aplicativo, não uma pontuação oficial do BJCP."
)
