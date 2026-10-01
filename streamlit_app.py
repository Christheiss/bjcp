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

@st.cache_data
def load_database(path_str, file_mtime_ns, file_size):
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
    str(DB_PATH), DB_PATH.stat().st_mtime_ns, DB_PATH.stat().st_size
)
if db_error:
    st.error(f"Erro ao carregar o banco: {db_error}")
    st.stop()

styles = db.get("Estilos", pd.DataFrame())
categories = db.get("Categorias_Parametros", pd.DataFrame())
references = db.get("Valores_Referencia_BJCP", pd.DataFrame())
aroma_ui = db.get("Vocabulario_Aroma_UI", pd.DataFrame())
appearance_ui = db.get("Vocabulario_Aparencia_UI", pd.DataFrame())
intensity_df = db.get("Escala_Intensidade_BJCP", pd.DataFrame())
srm_df = db.get("Referencia_Cor_SRM", pd.DataFrame())
appearance_scale = db.get("Escala_Aparencia_UI", pd.DataFrame())
color_ref = db.get("Referencia_Cor_BJCP", pd.DataFrame())

DEFAULT_INTENSITY = {
    0: "Ausente", 1: "Muito baixa", 2: "Muito baixa", 3: "Baixa",
    4: "Baixa–moderada", 5: "Moderada", 6: "Moderada–alta",
    7: "Moderada–alta", 8: "Alta", 9: "Muito alta", 10: "Intensa"
}

DEFAULT_APPEARANCE = {
    0: "Ausente / não perceptível", 1: "Muito baixa", 2: "Baixa",
    3: "Baixa–moderada", 4: "Moderada-baixa", 5: "Moderada",
    6: "Moderada-alta", 7: "Alta", 8: "Muito alta",
    9: "Muito alta / proeminente", 10: "Extrema / máxima referência"
}

def label_intensity(value, appearance=False):
    df = appearance_scale if appearance else intensity_df
    if not df.empty and "Valor_0_10" in df.columns:
        row = df[df["Valor_0_10"] == int(value)]
        if not row.empty:
            return str(row.iloc[0].get("Rótulo_UI", row.iloc[0].get("Rótulo_BJCP_UI", "")))
    return (DEFAULT_APPEARANCE if appearance else DEFAULT_INTENSITY).get(int(value), "")

def slider_with_label(label, key, value=0, appearance=False):
    value = st.slider(label, 0, 10, int(value), 1, key=key)
    st.caption(f"**{value}/10 — {label_intensity(value, appearance)}**")
    return value

# -----------------------------
# Cor / SRM
# -----------------------------
def srm_sample_hex(srm):
    """Amostra gráfica aproximada para visualização do SRM."""
    try:
        value = float(srm)
    except Exception:
        return "#D9A441"

    # Interpolação simples entre pontos de referência.
    points = [
        (2.0, "#FFE699"), (3.5, "#F5D76E"), (5.5, "#D9A441"),
        (7.5, "#B87333"), (12.0, "#9A5A2A"), (15.5, "#8A4B24"),
        (17.5, "#70452A"), (20.5, "#5A3825"), (26.0, "#3F2619"),
        (32.5, "#2A1A13"), (35.0, "#17110E"), (40.0, "#090706")
    ]

    if value <= points[0][0]:
        return points[0][1]
    if value >= points[-1][0]:
        return points[-1][1]

    def hex_rgb(h):
        h = h.lstrip("#")
        return tuple(int(h[i:i+2], 16) for i in (0, 2, 4))

    for (x1, c1), (x2, c2) in zip(points, points[1:]):
        if x1 <= value <= x2:
            t = (value - x1) / (x2 - x1)
            a = hex_rgb(c1)
            b = hex_rgb(c2)
            rgb = tuple(round(a[i] + (b[i] - a[i]) * t) for i in range(3))
            return "#{:02X}{:02X}{:02X}".format(*rgb)

    return "#D9A441"

def color_swatch(hex_color, label):
    st.markdown(
        f"""
        <div style="
            display:flex;
            align-items:center;
            gap:12px;
            margin:8px 0 12px 0;
        ">
            <div style="
                width:72px;
                height:48px;
                border-radius:8px;
                background:{hex_color};
                border:1px solid rgba(255,255,255,.35);
                box-shadow:0 2px 8px rgba(0,0,0,.25);
            "></div>
            <div>
                <div style="font-weight:600;">Amostra visual</div>
                <div style="opacity:.7;font-size:.85rem;">{label}</div>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

# -----------------------------
# Estado
# -----------------------------
if "step" not in st.session_state:
    st.session_state.step = "Aroma"

if "aroma_main" not in st.session_state:
    st.session_state.aroma_main = {"Lúpulo": 0, "Malte": 0, "Fermentação": 0}
if "aroma_selected" not in st.session_state:
    st.session_state.aroma_selected = {}
if "aroma_values" not in st.session_state:
    st.session_state.aroma_values = {}

if "appearance_main" not in st.session_state:
    st.session_state.appearance_main = {
        "Limpidez": 5,
        "Turbidez": 0,
        "Formação da espuma": 5,
        "Retenção da espuma": 5,
        "Pernas / viscosidade visual": 0,
    }
if "appearance_selected" not in st.session_state:
    st.session_state.appearance_selected = {}
if "appearance_values" not in st.session_state:
    st.session_state.appearance_values = {}
if "appearance_color" not in st.session_state:
    st.session_state.appearance_color = ""
if "appearance_highlights" not in st.session_state:
    st.session_state.appearance_highlights = []
if "appearance_srm" not in st.session_state:
    st.session_state.appearance_srm = None
if "appearance_last_color" not in st.session_state:
    st.session_state.appearance_last_color = ""

# -----------------------------
# Header
# -----------------------------
st.title("🍺 BeerSense")
st.subheader("Avaliação Sensorial baseada no BJCP")

c1, c2 = st.columns(2)
with c1:
    st.success("✓ Base BJCP conectada")
with c2:
    st.metric("Estilos", len(styles))

step = st.radio(
    "Etapa da avaliação",
    ["Aroma", "Aparência"],
    index=0 if st.session_state.step == "Aroma" else 1,
    horizontal=True,
    key="step_selector",
)
st.session_state.step = step

progress = 0.20 if step == "Aroma" else 0.40
st.progress(progress, text=f"Etapa {'1' if step == 'Aroma' else '2'} de 5 — {step}")

# -----------------------------
# AROMA
# -----------------------------
if step == "Aroma":
    st.info(
        "A escala numérica de 0–10 é operacional do aplicativo. "
        "Ela não é uma escala oficial do BJCP."
    )
    st.header("AROMA")
    st.markdown("### Intensidade geral")

    cols = st.columns(3)
    for col, (label, key) in zip(
        cols,
        [("Lúpulo", "aroma_main_hop"), ("Malte", "aroma_main_malt"),
         ("Fermentação", "aroma_main_fermentation")]
    ):
        with col:
            value = st.slider(label, 0, 10, int(st.session_state.aroma_main[label]), 1, key=key)
            st.session_state.aroma_main[label] = value
            st.caption(f"**{value}/10 — {label_intensity(value)}**")

    st.divider()
    st.markdown("### Identificar nuances")
    st.caption("Selecione apenas as características percebidas e depois indique a intensidade.")

    if aroma_ui.empty:
        st.warning("A aba Vocabulario_Aroma_UI não foi encontrada.")
    else:
        group_order = [
            "🌿 Lúpulo", "🌾 Malte", "🍑 Frutado",
            "🍺 Fermentação / levedura", "🍋 Acidez / fermentação mista",
            "🪵 Madeira", "💧 Água / mineral", "Brett / Funky",
            "⚠️ Defeitos / indesejáveis", "🍯 Percepções"
        ]
        existing = set(aroma_ui["Grupo_UI"].dropna().astype(str))
        group_order += sorted(existing - set(group_order))

        for group in group_order:
            df = aroma_ui[aroma_ui["Grupo_UI"] == group].copy()
            if df.empty:
                continue
            options = df["Rótulo_PT"].astype(str).tolist()
            option_to_id = dict(zip(df["Rótulo_PT"].astype(str), df["Parametro_ID"].astype(str)))
            previous = st.session_state.aroma_selected.get(group, [])

            with st.expander(f"{group} · {len(options)} descritores"):
                selected = st.multiselect(
                    "Nuances percebidas",
                    options=options,
                    default=[x for x in previous if x in options],
                    key=f"aroma_select_{re.sub(r'[^a-zA-Z0-9]+','_',group)}"
                )
                st.session_state.aroma_selected[group] = selected

                for label in selected:
                    pid = option_to_id[label]
                    value = st.session_state.aroma_values.get(pid, 0)
                    value = st.slider(label, 0, 10, int(value), 1, key=f"aroma_n_{pid}")
                    st.session_state.aroma_values[pid] = value
                    st.caption(f"{value}/10 — {label_intensity(value)}")

# -----------------------------
# APARÊNCIA
# -----------------------------
else:
    st.info(
        "Na Aparência, alguns atributos são categóricos (como a cor) e outros "
        "podem ser registrados em intensidade. O SRM é uma referência de densidade "
        "de cor; o próprio BJCP alerta que as condições de visualização afetam a percepção."
    )
    st.header("APARÊNCIA")

    # Cor
    st.markdown("### 🎨 Cor")

    # O avaliador escolhe apenas o SRM. A amostra visual e o nome
    # da cor aparecem automaticamente.
    srm = st.number_input(
        "SRM",
        min_value=0.0,
        max_value=50.0,
        value=float(st.session_state.appearance_srm or 0),
        step=0.5,
        key="appearance_srm_input",
    )
    st.session_state.appearance_srm = srm if srm > 0 else None

    def color_name_from_srm(value):
        if value <= 0:
            return "Sem cor informada"

        ranges = [
            ("Palha", 2, 3),
            ("Amarelo", 3, 4),
            ("Dourado", 5, 6),
            ("Âmbar", 6, 9),
            ("Âmbar profundo / cobre claro", 10, 14),
            ("Cobre", 14, 17),
            ("Cobre profundo / marrom claro", 17, 18),
            ("Marrom", 19, 22),
            ("Marrom escuro", 22, 30),
            ("Muito marrom escuro", 30, 35),
            ("Preto", 30, 40),
            ("Preto opaco", 40, 50),
        ]

        candidates = [
            (name, low, high, abs(value - ((low + high) / 2)))
            for name, low, high in ranges
            if low <= value <= high
        ]

        if candidates:
            return min(candidates, key=lambda x: x[3])[0]
        if value < 2:
            return "Mais claro que palha"
        return "Mais escuro que preto opaco"

    if srm > 0:
        color_name = color_name_from_srm(srm)
        sample_hex = srm_sample_hex(srm)

        color_swatch(
            sample_hex,
            f"SRM {srm:g} · {color_name}"
        )

        st.markdown(f"### {color_name}")
        st.caption(
            "Nome aproximado a partir da referência de cor do BJCP. "
            "A percepção visual pode variar conforme iluminação, recipiente e observador."
        )
    else:
        st.caption("Escolha o SRM para visualizar a cor e o nome correspondente.")

    st.markdown("### 🔎 Clareza e turbidez")
    c1, c2 = st.columns(2)
    with c1:
        v = st.slider(
            "Limpidez",
            0, 10, int(st.session_state.appearance_main["Limpidez"]), 1,
            key="appearance_clarity"
        )
        st.session_state.appearance_main["Limpidez"] = v
        st.caption(f"**{v}/10 — {label_intensity(v, True)}**")
        st.caption("0 = opaca · 10 = cristalina")
    with c2:
        v = st.slider(
            "Turbidez / haze",
            0, 10, int(st.session_state.appearance_main["Turbidez"]), 1,
            key="appearance_haze"
        )
        st.session_state.appearance_main["Turbidez"] = v
        st.caption(f"**{v}/10 — {label_intensity(v, True)}**")

    st.divider()

    # Head
    st.markdown("### 🫧 Espuma")
    c1, c2 = st.columns(2)
    with c1:
        v = st.slider(
            "Formação / tamanho da espuma",
            0, 10, int(st.session_state.appearance_main["Formação da espuma"]), 1,
            key="appearance_head_size"
        )
        st.session_state.appearance_main["Formação da espuma"] = v
        st.caption(f"**{v}/10 — {label_intensity(v, True)}**")
    with c2:
        v = st.slider(
            "Retenção da espuma",
            0, 10, int(st.session_state.appearance_main["Retenção da espuma"]), 1,
            key="appearance_head_retention"
        )
        st.session_state.appearance_main["Retenção da espuma"] = v
        st.caption(f"**{v}/10 — {label_intensity(v, True)}**")

    foam_color_df = appearance_ui[
        (appearance_ui["Grupo_UI"] == "🫧 Espuma — cor") &
        (appearance_ui["Controle_UI"] == "espuma_cor")
    ]
    if not foam_color_df.empty:
        st.multiselect(
            "Cor da espuma",
            foam_color_df["Rótulo_PT"].drop_duplicates().tolist(),
            key="appearance_foam_color"
        )

    st.divider()

    # Legs
    st.markdown("### 💧 Pernas / viscosidade visual")
    v = st.slider(
        "Pernas / presença de gotículas",
        0, 10, int(st.session_state.appearance_main["Pernas / viscosidade visual"]), 1,
        key="appearance_legs"
    )
    st.session_state.appearance_main["Pernas / viscosidade visual"] = v
    st.caption(f"**{v}/10 — {label_intensity(v, True)}**")
    st.caption("O BJCP observa que pernas não são indicador de qualidade; podem indicar maior álcool, açúcar ou glicerol.")

    st.divider()

    # Nuances
    st.markdown("### Identificar características visuais")
    st.caption("Use esta seção para registrar descritores específicos como renda belga, bolhas finas, cristalina, turva, etc.")

    if appearance_ui.empty:
        st.warning("A aba Vocabulario_Aparencia_UI não foi encontrada.")
    else:
        groups = [
            "🫧 Espuma — formação e textura",
            "🫧 Espuma — formação e retenção",
            "🫧 Espuma — retenção",
            "🫧 Espuma — renda",
            "🔎 Limpidez",
            "🌫️ Turbidez",
        ]
        for group in groups:
            df = appearance_ui[appearance_ui["Grupo_UI"] == group].copy()
            if df.empty:
                continue
            options = df["Rótulo_PT"].astype(str).tolist()
            id_map = dict(zip(df["Rótulo_PT"].astype(str), df["Aparencia_ID"].astype(str)))
            prev = st.session_state.appearance_selected.get(group, [])

            with st.expander(f"{group} · {len(options)} descritores"):
                selected = st.multiselect(
                    "Características percebidas",
                    options,
                    default=[x for x in prev if x in options],
                    key=f"appearance_select_{re.sub(r'[^a-zA-Z0-9]+','_',group)}"
                )
                st.session_state.appearance_selected[group] = selected
                for label in selected:
                    aid = id_map[label]
                    value = st.session_state.appearance_values.get(aid, 0)
                    value = st.slider(label, 0, 10, int(value), 1, key=f"appearance_n_{aid}")
                    st.session_state.appearance_values[aid] = value
                    st.caption(f"{value}/10 — {label_intensity(value, True)}")

    st.divider()
    st.subheader("Resumo da Aparência")

    st.write(f"**Cor:** {st.session_state.appearance_color or 'não informada'}")
    if st.session_state.appearance_srm:
        st.write(f"**SRM medido:** {st.session_state.appearance_srm:g}")
    if st.session_state.appearance_highlights:
        st.write(f"**Reflexos:** {', '.join(st.session_state.appearance_highlights)}")

    c1, c2, c3 = st.columns(3)
    c1.metric("Limpidez", f"{st.session_state.appearance_main['Limpidez']}/10")
    c2.metric("Espuma", f"{st.session_state.appearance_main['Formação da espuma']}/10")
    c3.metric("Retenção", f"{st.session_state.appearance_main['Retenção da espuma']}/10")

st.caption(
    f"Banco: {len(styles)} estilos · {len(references)} referências · "
    f"{len(aroma_ui)} descritores de aroma · {len(appearance_ui)} descritores de aparência"
)
