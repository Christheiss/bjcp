import streamlit as st
import pandas as pd
import re
from pathlib import Path

st.set_page_config(
    page_title="BeerSense — BJCP",
    page_icon="🍺",
    layout="centered",
    initial_sidebar_state="collapsed",
)

DB_PATH = Path("data/bjcp_database.xlsx")

# -----------------------------
# Dados
# -----------------------------
@st.cache_data
def load_database(path_str, file_mtime_ns, file_size):
    # O mtime/tamanho entram na chave do cache para que o Streamlit
    # recarregue automaticamente quando o Excel do GitHub for substituído.
    path = Path(path_str)

    if not path.exists():
        return None, f"Banco não encontrado em: {path}"

    try:
        xls = pd.ExcelFile(path, engine="openpyxl")
        sheets = {
            name: pd.read_excel(path, sheet_name=name, engine="openpyxl")
            for name in xls.sheet_names
        }
        return sheets, None
    except Exception as e:
        return None, str(e)


if not DB_PATH.exists():
    st.error(f"Banco não encontrado em: {DB_PATH}")
    st.stop()

db, db_error = load_database(
    str(DB_PATH),
    DB_PATH.stat().st_mtime_ns,
    DB_PATH.stat().st_size,
)

if db_error:
    st.error(f"Erro ao carregar o banco: {db_error}")
    st.stop()

styles = db.get("Estilos", pd.DataFrame())
categories = db.get("Categorias_Parametros", pd.DataFrame())
references = db.get("Valores_Referencia_BJCP", pd.DataFrame())
aroma_ui = db.get("Vocabulario_Aroma_UI", pd.DataFrame())
intensity_df = db.get("Escala_Intensidade_BJCP", pd.DataFrame())

# -----------------------------
# Escala operacional
# -----------------------------
DEFAULT_INTENSITY = {
    0: "Ausente",
    1: "Muito baixa",
    2: "Muito baixa",
    3: "Baixa",
    4: "Baixa–moderada",
    5: "Moderada",
    6: "Moderada–alta",
    7: "Moderada–alta",
    8: "Alta",
    9: "Muito alta",
    10: "Intensa",
}

def intensity_label(value):
    try:
        value = int(value)
    except Exception:
        return ""
    if not intensity_df.empty and "Valor_0_10" in intensity_df.columns:
        row = intensity_df[intensity_df["Valor_0_10"] == value]
        if not row.empty:
            return str(row.iloc[0]["Rótulo_BJCP_UI"])
    return DEFAULT_INTENSITY.get(value, "")

def intensity_slider(label, key, value=0):
    value = st.slider(
        label,
        min_value=0,
        max_value=10,
        value=int(value),
        step=1,
        key=key,
        help="0–10 é uma normalização operacional do aplicativo. O rótulo abaixo traduz a intensidade para linguagem próxima à usada nas descrições BJCP."
    )
    st.caption(f"**{value}/10 — {intensity_label(value)}**")
    return value

# -----------------------------
# Estado
# -----------------------------
if "aroma_main" not in st.session_state:
    st.session_state.aroma_main = {
        "Lúpulo": 0,
        "Malte": 0,
        "Fermentação": 0,
    }

if "aroma_selected" not in st.session_state:
    st.session_state.aroma_selected = {}

if "aroma_values" not in st.session_state:
    st.session_state.aroma_values = {}

# -----------------------------
# Cabeçalho
# -----------------------------
st.title("🍺 BeerSense")
st.subheader("Avaliação Sensorial baseada no BJCP")

col1, col2 = st.columns(2)
with col1:
    st.success("✓ Base BJCP conectada")
with col2:
    st.metric("Estilos", len(styles))

st.progress(0.20, text="Etapa 1 de 5 — Aroma")

st.info(
    "A escala numérica de 0–10 é **operacional do aplicativo**. "
    "Ela não é uma escala oficial do BJCP. Os rótulos abaixo servem para aproximar "
    "a leitura da linguagem descritiva usada nas diretrizes."
)

# -----------------------------
# Aroma — intensidades principais
# -----------------------------
st.header("AROMA")

st.markdown("### Intensidade geral")

main_cols = st.columns(3)

main_defs = [
    ("Lúpulo", "aroma_main_hop"),
    ("Malte", "aroma_main_malt"),
    ("Fermentação", "aroma_main_fermentation"),
]

for col, (label, key) in zip(main_cols, main_defs):
    with col:
        current = st.session_state.aroma_main.get(label, 0)
        new_value = st.slider(
            label,
            0, 10, int(current), 1,
            key=key
        )
        st.session_state.aroma_main[label] = new_value
        st.caption(f"**{new_value}/10 — {intensity_label(new_value)}**")

st.divider()

# -----------------------------
# Nuances
# -----------------------------
st.markdown("### Identificar nuances")
st.caption(
    "Selecione apenas as características que você percebe. "
    "Depois, atribua a intensidade individual de cada uma."
)

if aroma_ui.empty:
    st.warning(
        "A aba Vocabulario_Aroma_UI não foi encontrada. "
        "Atualize o banco de dados para a versão que contém o vocabulário completo."
    )
else:
    group_order = [
        "🌿 Lúpulo",
        "🌾 Malte",
        "🍑 Frutado",
        "🍺 Fermentação / levedura",
        "🍋 Acidez / fermentação mista",
        "🪵 Madeira",
        "💧 Água / mineral",
        "Brett / Funky",
        "⚠️ Defeitos / indesejáveis",
        "🍯 Percepções",
    ]

    existing_groups = set(aroma_ui["Grupo_UI"].dropna().astype(str))
    group_order += sorted(existing_groups - set(group_order))

    for group in group_order:
        group_df = aroma_ui[aroma_ui["Grupo_UI"] == group].copy()
        if group_df.empty:
            continue

        options = group_df["Rótulo_PT"].astype(str).tolist()
        option_to_id = dict(
            zip(
                group_df["Rótulo_PT"].astype(str),
                group_df["Parametro_ID"].astype(str)
            )
        )

        selected_key = f"selected_{group}"
        previous = st.session_state.aroma_selected.get(group, [])

        with st.expander(f"{group}  ·  {len(options)} descritores", expanded=False):
            selected = st.multiselect(
                "Nuances percebidas",
                options=options,
                default=[x for x in previous if x in options],
                key=selected_key,
                placeholder="Selecione uma ou mais nuances..."
            )

            st.session_state.aroma_selected[group] = selected

            if selected:
                st.markdown("**Intensidade das nuances selecionadas**")

                for label in selected:
                    param_id = option_to_id[label]
                    safe_id = re.sub(r"[^a-zA-Z0-9_]+", "_", param_id)

                    value_key = f"nuance_{safe_id}"
                    old_value = st.session_state.aroma_values.get(param_id, 0)

                    value = st.slider(
                        label,
                        0, 10, int(old_value), 1,
                        key=value_key
                    )
                    st.session_state.aroma_values[param_id] = value
                    st.caption(f"{value}/10 — {intensity_label(value)}")

# -----------------------------
# Resumo da entrada
# -----------------------------
st.divider()
st.subheader("Resumo do Aroma")

active_nuances = []
for group, labels in st.session_state.aroma_selected.items():
    for label in labels:
        row = aroma_ui[
            (aroma_ui["Grupo_UI"] == group) &
            (aroma_ui["Rótulo_PT"] == label)
        ]
        if not row.empty:
            pid = str(row.iloc[0]["Parametro_ID"])
            active_nuances.append({
                "Grupo": group,
                "Nuance": label,
                "Intensidade": st.session_state.aroma_values.get(pid, 0),
                "Linguagem": intensity_label(
                    st.session_state.aroma_values.get(pid, 0)
                ),
                "ID": pid,
            })

if active_nuances:
    summary = pd.DataFrame(active_nuances)
    st.dataframe(
        summary[["Grupo", "Nuance", "Intensidade", "Linguagem"]],
        use_container_width=True,
        hide_index=True,
    )
else:
    st.caption("Nenhuma nuance específica selecionada ainda.")

# -----------------------------
# Diagnóstico técnico
# -----------------------------
with st.expander("ℹ️ Como esta etapa será usada no matching"):
    st.write(
        "Cada nuance fica registrada com seu identificador e intensidade. "
        "Na etapa de matching, o sistema poderá cruzar esses registros com "
        "as referências específicas de cada estilo."
    )
    st.write(
        "Importante: um descritor como chocolate, torrado, caramelo ou fruta "
        "não será considerado automaticamente 'bom' ou 'ruim'. "
        "A condição esperada, opcional ou indesejável deverá ser determinada "
        "pelo estilo BJCP correspondente."
    )

st.caption(
    f"Banco carregado: {len(styles)} estilos · "
    f"{len(categories)} parâmetros gerais · "
    f"{len(references)} referências · "
    f"{len(aroma_ui)} descritores de aroma"
)
