import streamlit as st
import streamlit.components.v1 as components
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

def foam_hex_from_name(name):
    colors = {
        "espuma branca": "#F8F8F3",
        "branco": "#F8F8F3",
        "branco quebrado": "#F2EBDD",
        "espuma branco-quebrada": "#F2EBDD",
        "bege / castanho claro": "#D8C49A",
        "bege claro": "#E2D2AA",
        "bege pálido": "#E9DCC0",
        "espuma bege clara": "#E2D2AA",
        "bege": "#D4BF91",
        "espuma bege pálida": "#E9DCC0",
    }
    return colors.get(str(name).strip().lower(), "#F8F8F3")

def beer_glass_svg(srm, foam_size, foam_color_name):
    """Desenha um copo estilizado e dinâmico para a avaliação visual."""
    beer_color = srm_sample_hex(srm) if srm > 0 else "#E8E8E8"
    foam_color = foam_hex_from_name(foam_color_name)

    # Área interna do copo: x=82..238, y=36..300.
    # Foam size controla diretamente a altura do colarinho.
    max_foam = 92
    min_foam = 8
    foam_h = min_foam + (max_foam - min_foam) * (foam_size / 10.0)
    beer_top = 300 - foam_h

    # Bolhas decorativas; não representam carbonatação medida.
    bubble_y = beer_top + foam_h * 0.45

    return f"""
    <div style="display:flex;justify-content:center;margin:10px 0 18px 0;">
      <svg viewBox="0 0 320 360" width="100%" style="max-width:320px;height:auto;">
        <defs>
          <linearGradient id="glassBeer" x1="0" y1="0" x2="0" y2="1">
            <stop offset="0%" stop-color="{beer_color}" stop-opacity="0.88"/>
            <stop offset="100%" stop-color="{beer_color}" stop-opacity="1"/>
          </linearGradient>
          <linearGradient id="glassFoam" x1="0" y1="0" x2="0" y2="1">
            <stop offset="0%" stop-color="{foam_color}" stop-opacity="0.98"/>
            <stop offset="100%" stop-color="{foam_color}" stop-opacity="0.92"/>
          </linearGradient>
          <clipPath id="glassClip">
            <path d="M72 38 L248 38 L230 306 Q228 320 214 320 L106 320 Q92 320 90 306 Z"/>
          </clipPath>
        </defs>

        <!-- Líquido -->
        <g clip-path="url(#glassClip)">
          <rect x="80" y="{beer_top:.1f}" width="160" height="{300-beer_top:.1f}" fill="url(#glassBeer)"/>

          <!-- Colarinho -->
          <rect x="80" y="36" width="160" height="{foam_h:.1f}" fill="url(#glassFoam)"/>

          <!-- Topo irregular da espuma -->
          <path d="M80 {beer_top:.1f}
                   C96 {beer_top-8:.1f}, 104 {beer_top+5:.1f}, 118 {beer_top-3:.1f}
                   C132 {beer_top-11:.1f}, 144 {beer_top+4:.1f}, 158 {beer_top-4:.1f}
                   C174 {beer_top-13:.1f}, 188 {beer_top+6:.1f}, 202 {beer_top-2:.1f}
                   C218 {beer_top-8:.1f}, 228 {beer_top+3:.1f}, 240 {beer_top:.1f}
                   L240 36 L80 36 Z"
                fill="{foam_color}"/>

          <!-- Bolhas sutis na espuma -->
          <g fill="none" stroke="#ffffff" stroke-opacity="0.42" stroke-width="2">
            <circle cx="108" cy="{bubble_y-8:.1f}" r="4"/>
            <circle cx="136" cy="{bubble_y+5:.1f}" r="3"/>
            <circle cx="170" cy="{bubble_y-5:.1f}" r="5"/>
            <circle cx="204" cy="{bubble_y+7:.1f}" r="3"/>
          </g>
        </g>

        <!-- Contorno do copo -->
        <path d="M72 38 L248 38 L230 306 Q228 320 214 320 L106 320 Q92 320 90 306 Z"
              fill="rgba(255,255,255,0.035)"
              stroke="rgba(220,230,235,0.72)"
              stroke-width="4"/>

        <!-- Borda -->
        <path d="M68 38 Q160 30 252 38" fill="none"
              stroke="rgba(220,230,235,0.85)" stroke-width="5"/>

        <!-- Reflexo -->
        <path d="M92 55 L106 286" stroke="white" stroke-opacity="0.22" stroke-width="7"
              stroke-linecap="round"/>

        <!-- Base -->
        <path d="M98 320 L222 320 L238 335 L82 335 Z"
              fill="rgba(220,230,235,0.10)"
              stroke="rgba(220,230,235,0.55)" stroke-width="3"/>

        <!-- Informação -->
        <text x="160" y="355" text-anchor="middle"
              fill="currentColor" font-size="15" font-family="sans-serif">
          SRM {srm:g} · {foam_size}/10 espuma
        </text>
      </svg>
    </div>
    """


# -----------------------------
# Visualização do copo
# -----------------------------
def beer_color_from_srm(srm):
    """Cor gráfica aproximada a partir do SRM."""
    points = [
        (0, "#F7F0B5"),
        (2, "#F4E6A0"),
        (3.5, "#F0D36A"),
        (5.5, "#D9A441"),
        (7.5, "#B87333"),
        (12, "#9A5A2A"),
        (15.5, "#8A4B24"),
        (17.5, "#70452A"),
        (20.5, "#5A3825"),
        (26, "#3F2619"),
        (32.5, "#2A1A13"),
        (40, "#17110E"),
        (50, "#090706"),
    ]
    value = max(0.0, min(50.0, float(srm or 0)))

    if value <= points[0][0]:
        return points[0][1]

    def rgb(h):
        h = h.lstrip("#")
        return tuple(int(h[i:i+2], 16) for i in (0, 2, 4))

    for (x1, c1), (x2, c2) in zip(points, points[1:]):
        if x1 <= value <= x2:
            t = (value - x1) / (x2 - x1)
            a, b = rgb(c1), rgb(c2)
            return "#{:02X}{:02X}{:02X}".format(
                *[round(a[i] + (b[i] - a[i]) * t) for i in range(3)]
            )

    return points[-1][1]


def color_name_from_srm_ui(srm):
    value = float(srm or 0)
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
    return "Mais claro que palha" if value < 2 else "Mais escuro que preto opaco"


def foam_color_hex(label):
    mapping = {
        "espuma branca": "#F8F8F2",
        "espuma branco-quebrada": "#F1EBD7",
        "espuma bege clara": "#E8D7B2",
        "bege claro": "#E2CFA5",
        "espuma bege pálida": "#D9C39B",
        "bege pálido": "#D8C39C",
        "bege": "#CDB58A",
        "bege / castanho claro": "#BFA77A",
    }
    return mapping.get(str(label).strip().lower(), "#F1EBD7")


def render_beer_glass(srm, foam_size, foam_color):
    """Desenha um copo em SVG; os valores são recalculados a cada interação."""
    liquid = beer_color_from_srm(srm)
    foam = foam_color_hex(foam_color)

    # Tamanho visual do colarinho:
    # 0 = sem colarinho; 10 = colarinho muito alto.
    # A cerveja continua ocupando o copo até a base; somente a altura
    # da espuma muda.
    glass_top = 35
    glass_bottom = 365
    head_h = (float(foam_size) / 10.0) * 105
    liquid_top = glass_top + head_h

    # Copo trapezoidal simplificado.
    glass_left = 75
    glass_right = 245

    # Retângulo do líquido dentro do corpo do copo.

    # Escurecimento/reflexo para dar sensação de volume.
    html = f"""
    <div style="width:100%;display:flex;justify-content:center;margin:4px 0 18px;">
      <div style="text-align:center;">
        <svg width="320" height="430" viewBox="0 0 320 430"
             xmlns="http://www.w3.org/2000/svg"
             style="max-width:100%;height:auto;">
          <defs>
            <clipPath id="glassClip">
              <path d="M75 35 L245 35 L225 365 L95 365 Z"/>
            </clipPath>
            <linearGradient id="beerGradient" x1="0" y1="0" x2="1" y2="0">
              <stop offset="0%" stop-color="{liquid}" stop-opacity="0.78"/>
              <stop offset="50%" stop-color="{liquid}" stop-opacity="1"/>
              <stop offset="100%" stop-color="{liquid}" stop-opacity="0.82"/>
            </linearGradient>
            <linearGradient id="foamGradient" x1="0" y1="0" x2="0" y2="1">
              <stop offset="0%" stop-color="{foam}" stop-opacity="0.98"/>
              <stop offset="100%" stop-color="{foam}" stop-opacity="0.82"/>
            </linearGradient>
            <filter id="shadow" x="-30%" y="-30%" width="160%" height="160%">
              <feDropShadow dx="0" dy="8" stdDeviation="8" flood-opacity="0.28"/>
            </filter>
          </defs>

          <!-- sombra -->
          <ellipse cx="160" cy="383" rx="92" ry="12" fill="#000" opacity="0.18"/>

          <!-- cerveja + espuma recortadas no formato do copo -->
          <g clip-path="url(#glassClip)">
            <!-- A cerveja ocupa todo o corpo abaixo do colarinho -->
            <rect x="65" y="{liquid_top}" width="190"
                  height="{glass_bottom - liquid_top}"
                  fill="url(#beerGradient)"/>

            <!-- Sem colarinho: a cerveja chega até o topo do copo -->
            <rect x="65" y="{glass_top}" width="190" height="{head_h}"
                  fill="url(#foamGradient)"
                  opacity="{1 if head_h > 0 else 0}"/>

            <!-- linha de interface cerveja/espuma -->
            <line x1="65" y1="{liquid_top}" x2="255" y2="{liquid_top}"
                  stroke="#FFFFFF" stroke-width="2" opacity="0.20"/>

            <!-- bolhas discretas somente quando existe espuma -->
            <circle cx="105" cy="{glass_top + head_h*0.42}" r="3"
                    fill="#fff" opacity="{0.30 if head_h > 0 else 0}"/>
            <circle cx="132" cy="{glass_top + head_h*0.66}" r="2"
                    fill="#fff" opacity="{0.25 if head_h > 0 else 0}"/>
            <circle cx="178" cy="{glass_top + head_h*0.35}" r="3"
                    fill="#fff" opacity="{0.25 if head_h > 0 else 0}"/>
            <circle cx="207" cy="{glass_top + head_h*0.62}" r="2"
                    fill="#fff" opacity="{0.22 if head_h > 0 else 0}"/>

            <!-- reflexo do vidro -->
            <path d="M100 55 L82 330" stroke="#fff" stroke-width="10"
                  stroke-linecap="round" opacity="0.13"/>
          </g>

          <!-- contorno do copo -->
          <path d="M75 35 L245 35 L225 365 L95 365 Z"
                fill="none" stroke="#D9DEE7" stroke-width="3"
                opacity="0.82" filter="url(#shadow)"/>
          <line x1="72" y1="35" x2="248" y2="35"
                stroke="#E9EDF3" stroke-width="4" opacity="0.85"/>
          <line x1="95" y1="365" x2="225" y2="365"
                stroke="#E9EDF3" stroke-width="3" opacity="0.75"/>

          <!-- informações -->
          <text x="160" y="405" text-anchor="middle"
                font-family="Arial, sans-serif" font-size="16"
                fill="#E8EAF0">{srm:g} SRM · {color_name_from_srm_ui(srm)}</text>
        </svg>
      </div>
    </div>
    """
    components.html(html, height=445, scrolling=False)

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

    # Copo visual
    st.markdown("### 🍺 Aparência do copo")

    srm = st.number_input(
        "SRM",
        min_value=0.0,
        max_value=50.0,
        value=float(st.session_state.appearance_srm or 0),
        step=0.5,
        key="appearance_srm_input",
    )
    st.session_state.appearance_srm = srm if srm > 0 else None

    # Cor da espuma é categórica; vem diretamente do vocabulário da planilha.
    foam_color_df = appearance_ui[
        (appearance_ui["Grupo_UI"] == "🫧 Espuma — cor") &
        (appearance_ui["Controle_UI"] == "espuma_cor")
    ]
    foam_options = (
        foam_color_df["Rótulo_PT"].drop_duplicates().astype(str).tolist()
        if not foam_color_df.empty
        else ["espuma branca", "espuma branco-quebrada", "bege claro", "bege", "bege pálido"]
    )

    foam_selected = st.selectbox(
        "Cor da espuma",
        ["Espuma branca"] + foam_options,
        key="appearance_foam_color_select",
    )
    foam_selected = "" if foam_selected == "Espuma branca" else foam_selected

    head_size = int(st.session_state.appearance_main["Formação da espuma"])
    render_beer_glass(srm, head_size, foam_selected or "espuma branca")

    st.caption(
        f"**{srm:g} SRM — {color_name_from_srm_ui(srm)}** · "
        f"Colarinho: **{head_size}/10 — {label_intensity(head_size, True)}**"
    )

    st.divider()

    # Head
    st.markdown("### 🫧 Espuma")
    c1, c2 = st.columns(2)
    with c1:
        v = st.slider(
            "Tamanho do colarinho",
            0, 10, int(st.session_state.appearance_main["Formação da espuma"]), 1,
            key="appearance_head_size"
        )
        st.session_state.appearance_main["Formação da espuma"] = v
        st.caption(
            f"**{v}/10 — {label_intensity(v, True)}** · "
            "controla somente o tamanho do colarinho no copo"
        )
    with c2:
        v = st.slider(
            "Retenção da espuma",
            0, 10, int(st.session_state.appearance_main["Retenção da espuma"]), 1,
            key="appearance_head_retention"
        )
        st.session_state.appearance_main["Retenção da espuma"] = v
        st.caption(
            f"**{v}/10 — {label_intensity(v, True)}** · "
            "registrada separadamente; não altera o tamanho do colarinho"
        )

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
