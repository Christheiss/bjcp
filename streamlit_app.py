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
flavor_ui = db.get("Vocabulario_Sabor_UI", pd.DataFrame())
mouthfeel_ui = db.get("Vocabulario_Sensacao_Boca_UI", pd.DataFrame())
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

    # Nível da cerveja é FIXO.
    # 0 = sem colarinho; 10 = colarinho muito alto.
    # O colarinho cresce PARA CIMA a partir do nível fixo da cerveja,
    # deixando a parte superior do copo vazia.
    glass_top = 35
    glass_bottom = 365
    # A cerveja ocupa aproximadamente 2/3 da altura útil do copo.
    # Esse nível fica fixo; o colarinho cresce acima dele.
    liquid_top = glass_bottom - ((glass_bottom - glass_top) * 2 / 3)
    max_head_h = liquid_top - glass_top
    head_h = (float(foam_size) / 10.0) * max_head_h
    foam_top = liquid_top - head_h

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
            <!-- CERVEJA: nível superior FIXO -->
            <rect x="65" y="{liquid_top}" width="190"
                  height="{glass_bottom - liquid_top}"
                  fill="url(#beerGradient)"/>

            <!-- COLARINHO: cresce para CIMA, sem mover a cerveja -->
            <rect x="65" y="{foam_top}" width="190" height="{head_h}"
                  fill="url(#foamGradient)"
                  opacity="{1 if head_h > 0 else 0}"/>

            <!-- interface fixa entre cerveja e espuma -->
            <line x1="65" y1="{liquid_top}" x2="255" y2="{liquid_top}"
                  stroke="#FFFFFF" stroke-width="2" opacity="0.20"/>

            <!-- bolhas dentro do colarinho -->
            <circle cx="105" cy="{foam_top + head_h*0.42}" r="3"
                    fill="#fff" opacity="{0.30 if head_h > 0 else 0}"/>
            <circle cx="132" cy="{foam_top + head_h*0.66}" r="2"
                    fill="#fff" opacity="{0.25 if head_h > 0 else 0}"/>
            <circle cx="178" cy="{foam_top + head_h*0.35}" r="3"
                    fill="#fff" opacity="{0.25 if head_h > 0 else 0}"/>
            <circle cx="207" cy="{foam_top + head_h*0.62}" r="2"
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

if "flavor_main" not in st.session_state:
    st.session_state.flavor_main = {
        "Lúpulo": 0, "Malte": 0, "Fermentação": 0,
        "Amargor": 0, "Doçura": 0, "Acidez": 0, "Álcool": 0
    }
if "flavor_selected" not in st.session_state:
    st.session_state.flavor_selected = {}
if "flavor_values" not in st.session_state:
    st.session_state.flavor_values = {}
if "flavor_balance" not in st.session_state:
    st.session_state.flavor_balance = {"Malte ↔ Lúpulo": 5, "Doce ↔ Seco": 5}

if "mouth_main" not in st.session_state:
    st.session_state.mouth_main = {
        "Corpo": 5,
        "Carbonatação": 5,
        "Adstringência": 0,
        "Aquecimento alcoólico": 0,
        "Textura / viscosidade": 0,
    }
if "mouth_selected" not in st.session_state:
    st.session_state.mouth_selected = {}
if "mouth_values" not in st.session_state:
    st.session_state.mouth_values = {}
if "mouth_finish" not in st.session_state:
    st.session_state.mouth_finish = 5

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

steps = ["Aroma", "Aparência", "Sabor", "Sensação de boca", "Dados técnicos", "Resultado"]
step = st.radio(
    "Etapa da avaliação",
    steps,
    index=steps.index(st.session_state.step) if st.session_state.step in steps else 0,
    horizontal=True,
    key="step_selector",
)
st.session_state.step = step

step_num = {"Aroma": 1, "Aparência": 2, "Sabor": 3, "Sensação de boca": 4, "Dados técnicos": 5}[step]
st.progress(step_num / 6, text=f"Etapa {step_num} de 6 — {step}")

# -----------------------------
# MATCHING BJCP
# -----------------------------
def _canonical_pid_from_ui(dim, row):
    """Mapeia descritores detalhados da UI para os parâmetros canônicos do banco."""
    if dim == "Aroma":
        c = str(row.get("Parametro_Canônico", ""))
        mp = {
            "Aroma — Lúpulo": "P001", "Aroma — Malte": "P002",
            "Aroma — Fermentação": "P003", "Aroma — Brett/Funky": "P003",
        }
        if c in mp: return mp[c]
        term = str(row.get("Termo_EN", "")).lower()
        keys = [("smoke","P022"),("caramel","P023"),("toffee","P023"),("grain","P024"),("corn","P024"),
                ("hop","P025"),("phenolic","P026"),("spice","P026"),("roast","P027"),("chocolate","P027"),("coffee","P027"),
                ("sour","P028"),("acid","P028"),("sulfur","P029"),("dms","P029"),("wood","P030"),("oak","P030")]
        for k,p in keys:
            if k in term: return p
        return None
    if dim == "Sabor":
        term=str(row.get("Termo_EN","")).lower()
        keys=[("alcohol","P031"),("bitterness","P032"),("bitter","P032"),("bread","P033"),("biscuit","P033"),("toast","P033"),
              ("caramel","P034"),("toffee","P034"),("dry","P035"),("dryness","P035"),("ester","P036"),("fruit","P037"),
              ("hop","P038"),("malt","P039"),("phenolic","P040"),("spice","P040"),("roast","P041"),("chocolate","P041"),("coffee","P041"),
              ("smoke","P042"),("sour","P043"),("acid","P043"),("sweet","P044"),("wood","P045"),("oak","P045")]
        for k,p in keys:
            if k in term: return p
        return None
    if dim == "Mouthfeel":
        term=str(row.get("Termo_EN","")).lower()
        keys=[("warmth","P046"),("alcohol","P046"),("astring","P047"),("tannin","P047"),("body","P048"),
              ("carbon","P049"),("creamy","P050"),("cream","P050"),("smooth","P050"),("silky","P050"),("crisp","P051"),
              ("viscos","P052"),("ropy","P052"),("syrup","P052"),("thick","P052")]
        for k,p in keys:
            if k in term: return p
        return None
    if dim == "Aparência":
        return str(row.get("Parametro_ID", "")) if str(row.get("Parametro_ID", "")).startswith("P") else None
    return None

def build_user_vector():
    v = {
        "P001": st.session_state.aroma_main.get("Lúpulo",0), "P002": st.session_state.aroma_main.get("Malte",0),
        "P003": st.session_state.aroma_main.get("Fermentação",0),
        "P004": st.session_state.appearance_main.get("Limpidez",0), "P005": st.session_state.appearance_main.get("Limpidez",0),
        "P006": st.session_state.appearance_main.get("Formação da espuma",0),
        "P007": st.session_state.flavor_main.get("Lúpulo",0), "P008": st.session_state.flavor_main.get("Malte",0),
        "P009": st.session_state.flavor_main.get("Fermentação",0), "P010": st.session_state.flavor_main.get("Amargor",0),
        "P011": st.session_state.flavor_main.get("Doçura",0), "P012": st.session_state.flavor_balance.get("Doce ↔ Seco",5),
        "P013": st.session_state.mouth_main.get("Corpo",0), "P014": st.session_state.mouth_main.get("Carbonatação",0),
        "P015": st.session_state.mouth_main.get("Aquecimento alcoólico",0), "P016": st.session_state.mouth_main.get("Adstringência",0),
    }
    # Nuances detalhadas -> parâmetros canônicos
    for label_map, values, sheet, dim in [
        (st.session_state.aroma_selected, st.session_state.aroma_values, aroma_ui, "Aroma"),
        (st.session_state.flavor_selected, st.session_state.flavor_values, flavor_ui, "Sabor"),
        (st.session_state.mouth_selected, st.session_state.mouth_values, mouthfeel_ui, "Mouthfeel"),
        (st.session_state.appearance_selected, st.session_state.appearance_values, appearance_ui, "Aparência"),
    ]:
        if sheet.empty: continue
        id_col = {"Aroma":"Parametro_ID","Sabor":"Sabor_ID","Mouthfeel":"Sensacao_Boca_ID","Aparência":"Aparencia_ID"}[dim]
        for group, labels in label_map.items():
            df=sheet[sheet["Grupo_UI"]==group]
            for label in labels:
                row=df[df["Rótulo_PT"].astype(str)==str(label)]
                if row.empty: continue
                rr=row.iloc[0]; pid=_canonical_pid_from_ui(dim,rr)
                if not pid: continue
                val=int(values.get(str(rr[id_col]),0))
                v[pid]=max(v.get(pid,0),val)
    return v

def _aggregate_refs():
    cols=["Código","Estilo","Parametro_ID","Mínimo_Operacional","Típico","Máximo_Operacional","Status"]
    r=references[cols].copy()
    priority={"esperado":3,"opcional":2,"não especificado":1}
    r["prio"]=r["Status"].map(priority).fillna(0)
    rows=[]
    for (code,style,pid),g in r.groupby(["Código","Estilo","Parametro_ID"],dropna=False):
        g=g.sort_values("prio",ascending=False); top=g.iloc[0]
        rows.append({"Código":code,"Estilo":style,"Parametro_ID":pid,"Min":g["Mínimo_Operacional"].max() if top["Status"]!="não especificado" else 0,
                     "Typical":g.loc[g["Status"]!="não especificado","Típico"].mean() if (g["Status"]!="não especificado").any() else 0,
                     "Max":g["Máximo_Operacional"].min() if top["Status"]!="não especificado" else 0,"Status":top["Status"]})
    return pd.DataFrame(rows)

def calculate_matching():
    user=build_user_vector(); refs=_aggregate_refs(); results=[]
    tech=st.session_state.get("technical",{})
    tech_map={"OG":"OG","FG":"FG","IBU":"IBU","SRM":"SRM","ABV":"ABV"}
    # Pesos: principais sensoriais > nuances; técnicos complementares.
    weights={f"P{i:03d}":1.0 for i in range(1,17)}
    weights.update({f"P{i:03d}":0.55 for i in range(17,59)})
    for _,sty in styles.iterrows():
        code=sty["Código"]; name=sty["Estilo"]; rr=refs[refs["Código"]==code]
        contributions=[]; missing=[]; unexpected=[]
        for pid,val in user.items():
            val=float(val); ref=rr[rr["Parametro_ID"]==pid]
            if ref.empty: continue
            x=ref.iloc[0]; status=x["Status"]
            w=weights.get(pid,0.5)
            if status in ("esperado","opcional"):
                lo,hi=float(x["Min"]),float(x["Max"]); typ=float(x["Typical"])
                if lo<=val<=hi:
                    fit=1.0
                else:
                    dist=(lo-val) if val<lo else (val-hi); fit=max(0.0,1.0-dist/4.0)
                # características esperadas ausentes/abaixo do típico geram lacuna, sem transformar automaticamente em defeito
                if status=="esperado" and val < max(0,typ-1.0):
                    missing.append((str(x["Parametro_ID"]),str(x["Parametro_ID"]),round(typ,1),round(val,1)))
                contributions.append((fit,w))
            else:
                # se o avaliador detectou uma nuance que não consta como esperada/opcional no perfil,
                # registramos como "não esperado"; não chamamos de defeito.
                if val>=2:
                    unexpected.append((pid,round(val,1)))
                    contributions.append((0.0,w*0.55))
        # Dados técnicos
        tech_scores=[]
        for field,col in tech_map.items():
            val=tech.get(field)
            if val is None: continue
            mn=sty.get(f"{col} min"); mx=sty.get(f"{col} max")
            if pd.isna(mn) or pd.isna(mx): continue
            val=float(val); mn=float(mn); mx=float(mx)
            fit=1.0 if mn<=val<=mx else max(0.0,1.0-min(abs(val-mn),abs(val-mx))/((mx-mn) if mx>mn else 1))
            tech_scores.append(fit)
        # pH não tem referência no banco de estilos, portanto não entra no score.
        if tech_scores: contributions.append((sum(tech_scores)/len(tech_scores),0.8))
        if contributions:
            score=100*sum(f*w for f,w in contributions)/sum(w for f,w in contributions)
        else: score=0
        results.append({"Código":code,"Estilo":name,"Score":score,"missing":missing,"unexpected":unexpected,"tech_scores":tech_scores})
    return sorted(results,key=lambda x:x["Score"],reverse=True)[:3]


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
elif step == "Aparência":
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
        st.caption(
            f"**{st.session_state.appearance_main['Formação da espuma']}/10 — "
            f"{label_intensity(st.session_state.appearance_main['Formação da espuma'], True)}** · "
            "controla somente o tamanho do colarinho no copo"
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
# -----------------------------
# SABOR
# -----------------------------
elif step == "Sabor":
    st.info(
        "A escala 0–10 é uma normalização operacional do aplicativo. "
        "Os rótulos aproximam a linguagem descritiva usada nas diretrizes BJCP; "
        "não representam uma escala numérica oficial."
    )
    st.header("SABOR")

    st.markdown("### Intensidades principais")
    main_cols = st.columns(4)
    flavor_main_items = [
        ("Lúpulo", "flavor_main_hop"),
        ("Malte", "flavor_main_malt"),
        ("Fermentação", "flavor_main_ferm"),
        ("Amargor", "flavor_main_bitterness"),
        ("Doçura", "flavor_main_sweetness"),
        ("Acidez", "flavor_main_acidity"),
        ("Álcool", "flavor_main_alcohol"),
    ]

    for i, (label, key) in enumerate(flavor_main_items):
        with main_cols[i % 4]:
            value = st.slider(
                label, 0, 10, int(st.session_state.flavor_main[label]), 1, key=key
            )
            st.session_state.flavor_main[label] = value
            st.caption(f"**{value}/10 — {label_intensity(value)}**")

    st.divider()

    st.markdown("### ⚖️ Equilíbrio")
    b1, b2 = st.columns(2)
    with b1:
        value = st.slider(
            "Malte  ◀────────▶  Lúpulo",
            0, 10,
            int(st.session_state.flavor_balance["Malte ↔ Lúpulo"]),
            1,
            key="flavor_balance_malt_hop",
        )
        st.session_state.flavor_balance["Malte ↔ Lúpulo"] = value
        side = "Malte" if value < 5 else ("Lúpulo" if value > 5 else "Equilibrado")
        st.caption(f"**{value}/10 — {side}**")
    with b2:
        value = st.slider(
            "Doce  ◀────────▶  Seco",
            0, 10,
            int(st.session_state.flavor_balance["Doce ↔ Seco"]),
            1,
            key="flavor_balance_sweet_dry",
        )
        st.session_state.flavor_balance["Doce ↔ Seco"] = value
        side = "Doce" if value < 5 else ("Seco" if value > 5 else "Equilibrado")
        st.caption(f"**{value}/10 — {side}**")

    st.divider()

    st.markdown("### Identificar sabores e características")
    st.caption(
        "Selecione somente o que você percebe. Cada característica selecionada "
        "pode receber sua própria intensidade."
    )

    if flavor_ui.empty:
        st.warning("A aba Vocabulario_Sabor_UI não foi encontrada no banco.")
    else:
        group_order = [
            "🌾 Malte",
            "🌿 Lúpulo",
            "🍑 Frutado",
            "🍺 Fermentação / levedura",
            "🍋 Acidez",
            "🔥 Álcool",
            "🌿 Taninos",
            "🦠 Brett / Funky",
            "⚖️ Equilíbrio / percepção",
            "⚠️ Defeitos / indesejáveis",
            "✨ Qualidade / impressão geral",
        ]
        existing_groups = set(flavor_ui["Grupo_UI"].dropna().astype(str))
        group_order += sorted(existing_groups - set(group_order))

        for group in group_order:
            df = flavor_ui[flavor_ui["Grupo_UI"] == group].copy()
            if df.empty:
                continue

            options = df["Rótulo_PT"].astype(str).tolist()
            id_map = dict(zip(df["Rótulo_PT"].astype(str), df["Sabor_ID"].astype(str)))
            previous = st.session_state.flavor_selected.get(group, [])

            with st.expander(f"{group} · {len(options)} descritores"):
                selected = st.multiselect(
                    "Características percebidas",
                    options=options,
                    default=[x for x in previous if x in options],
                    key=f"flavor_select_{re.sub(r'[^a-zA-Z0-9]+','_',group)}",
                    placeholder="Selecione uma ou mais..."
                )
                st.session_state.flavor_selected[group] = selected

                for label in selected:
                    sid = id_map[label]
                    value = st.session_state.flavor_values.get(sid, 0)
                    value = st.slider(
                        label, 0, 10, int(value), 1,
                        key=f"flavor_n_{sid}"
                    )
                    st.session_state.flavor_values[sid] = value
                    st.caption(f"{value}/10 — {label_intensity(value)}")

    st.divider()
    st.subheader("Resumo do Sabor")
    c1, c2, c3 = st.columns(3)
    c1.metric("Amargor", f"{st.session_state.flavor_main['Amargor']}/10")
    c2.metric("Doçura", f"{st.session_state.flavor_main['Doçura']}/10")
    c3.metric("Acidez", f"{st.session_state.flavor_main['Acidez']}/10")



# -----------------------------
# SENSAÇÃO DE BOCA
# -----------------------------
elif step == "Sensação de boca":
    st.info(
        "A sensação de boca descreve como a cerveja se comporta fisicamente "
        "na boca: corpo, carbonatação, textura, adstringência, aquecimento "
        "alcoólico e características do final."
    )
    st.header("SENSAÇÃO DE BOCA")

    st.markdown("### Intensidades principais")

    items = [
        ("Corpo", "mouth_body"),
        ("Carbonatação", "mouth_carbonation"),
        ("Adstringência", "mouth_astringency"),
        ("Aquecimento alcoólico", "mouth_warmth"),
        ("Textura / viscosidade", "mouth_texture"),
    ]

    cols = st.columns(3)
    for i, (label, key) in enumerate(items):
        with cols[i % 3]:
            value = st.slider(
                label,
                0, 10,
                int(st.session_state.mouth_main[label]),
                1,
                key=key,
            )
            st.session_state.mouth_main[label] = value
            st.caption(f"**{value}/10 — {label_intensity(value, True)}**")

    st.divider()

    st.markdown("### 🏁 Final")
    finish = st.slider(
        "Doce  ◀────────▶  Seco",
        0, 10,
        int(st.session_state.mouth_finish),
        1,
        key="mouth_finish_balance",
    )
    st.session_state.mouth_finish = finish
    finish_label = "Doce" if finish < 5 else ("Seco" if finish > 5 else "Equilibrado")
    st.caption(f"**{finish}/10 — {finish_label}**")

    st.divider()

    st.markdown("### Identificar características")
    st.caption(
        "Selecione somente as sensações percebidas. "
        "Cada característica selecionada pode receber sua própria intensidade."
    )

    if mouthfeel_ui.empty:
        st.warning("A aba Vocabulario_Sensacao_Boca_UI não foi encontrada no banco.")
    else:
        groups = [
            "⚖️ Corpo",
            "🫧 Carbonatação",
            "🖐️ Textura",
            "✋ Sensação tátil",
            "🔥 Álcool",
            "🏁 Final",
            "👄 Percepção geral",
            "⚠️ Defeitos / indesejáveis",
        ]
        existing = set(mouthfeel_ui["Grupo_UI"].dropna().astype(str))
        groups += sorted(existing - set(groups))

        for group in groups:
            df = mouthfeel_ui[mouthfeel_ui["Grupo_UI"] == group].copy()
            if df.empty:
                continue

            options = df["Rótulo_PT"].astype(str).tolist()
            id_map = dict(zip(
                df["Rótulo_PT"].astype(str),
                df["Sensacao_Boca_ID"].astype(str)
            ))
            previous = st.session_state.mouth_selected.get(group, [])

            with st.expander(f"{group} · {len(options)} descritores"):
                selected = st.multiselect(
                    "Sensações percebidas",
                    options=options,
                    default=[x for x in previous if x in options],
                    key=f"mouth_select_{re.sub(r'[^a-zA-Z0-9]+','_',group)}",
                    placeholder="Selecione uma ou mais..."
                )
                st.session_state.mouth_selected[group] = selected

                for label in selected:
                    mid = id_map[label]
                    value = st.session_state.mouth_values.get(mid, 0)
                    value = st.slider(
                        label,
                        0, 10,
                        int(value),
                        1,
                        key=f"mouth_n_{mid}",
                    )
                    st.session_state.mouth_values[mid] = value
                    st.caption(f"{value}/10 — {label_intensity(value, True)}")

    st.divider()
    st.subheader("Resumo da Sensação de Boca")
    c1, c2, c3 = st.columns(3)
    c1.metric("Corpo", f"{st.session_state.mouth_main['Corpo']}/10")
    c2.metric("Carbonatação", f"{st.session_state.mouth_main['Carbonatação']}/10")
    c3.metric("Adstringência", f"{st.session_state.mouth_main['Adstringência']}/10")

# -----------------------------
# DADOS TÉCNICOS
# -----------------------------
elif step == "Dados técnicos":
    st.header("DADOS TÉCNICOS")
    st.caption("Todos os campos são opcionais. Preencha apenas os dados disponíveis da cerveja.")

    if "technical" not in st.session_state:
        st.session_state.technical = {"OG": None, "FG": None, "ABV": None, "IBU": None, "SRM": None, "pH": None}

    c1, c2 = st.columns(2)
    with c1:
        og = st.number_input("OG — Original Gravity", min_value=1.000, max_value=1.300, value=1.000, step=0.001, format="%.3f", key="tech_og")
        fg = st.number_input("FG — Final Gravity", min_value=0.990, max_value=1.100, value=1.000, step=0.001, format="%.3f", key="tech_fg")
        ibu = st.number_input("IBU — Amargor", min_value=0.0, max_value=200.0, value=0.0, step=1.0, key="tech_ibu")
    with c2:
        abv = st.number_input("ABV — Teor alcoólico (%)", min_value=0.0, max_value=30.0, value=0.0, step=0.1, key="tech_abv")
        srm = st.number_input("SRM — Cor", min_value=0.0, max_value=50.0, value=0.0, step=0.5, key="tech_srm")
        ph = st.number_input("pH", min_value=0.0, max_value=14.0, value=0.0, step=0.1, key="tech_ph")

    st.session_state.technical = {
        "OG": og if og != 1.000 else None, "FG": fg if fg != 1.000 else None,
        "ABV": abv if abv != 0 else None, "IBU": ibu if ibu != 0 else None,
        "SRM": srm if srm != 0 else None, "pH": ph if ph != 0 else None,
    }

    if og > 1.000 and fg > 0 and fg < og:
        abv_est = (og - fg) * 131.25
        st.info(f"ABV estimado a partir de OG e FG: **{abv_est:.1f}%**")

    st.divider()
    st.markdown("### 🔎 Finalizar avaliação")
    st.caption("Depois de preencher os dados desejados, gere o resultado para comparar sua cerveja com os estilos BJCP.")
    if st.button("🍺 Gerar os 3 estilos mais próximos", type="primary", use_container_width=True, key="generate_matching"):
        st.session_state.step = "Resultado"
        st.rerun()

# -----------------------------
# RESULTADO
# -----------------------------
elif step == "Resultado":
    st.header("🍺 ESTILOS MAIS PRÓXIMOS")
    st.caption("A compatibilidade é uma estimativa operacional baseada nos dados preenchidos e nas referências estruturadas do banco. Não é uma classificação oficial BJCP.")
    top3 = calculate_matching()
    if not top3:
        st.warning("Não foi possível calcular o matching com os dados atuais.")
    else:
        for i,res in enumerate(top3,1):
            with st.container(border=True):
                st.subheader(f"{i}º — {res['Estilo']}")
                st.progress(min(1.0,res['Score']/100), text=f"Compatibilidade: {res['Score']:.0f}%")
                if res["missing"]:
                    st.markdown("**🟡 O que falta para se aproximar de 100%**")
                    for pid,_,typ,val in res["missing"][:6]:
                        pname=categories.loc[categories["Parametro_ID"]==pid,"Parâmetro"]
                        label=str(pname.iloc[0]) if not pname.empty else pid
                        st.write(f"• {label}: informado {val:g}/10 · típico do perfil ≈ {typ:g}/10")
                else:
                    st.write("🟢 Os parâmetros esperados avaliados estão próximos do perfil registrado.")
                if res["unexpected"]:
                    st.markdown("**🔴 Informado, mas não aparece como esperado/opcional neste perfil**")
                    for pid,val in res["unexpected"][:6]:
                        pname=categories.loc[categories["Parametro_ID"]==pid,"Parâmetro"]
                        label=str(pname.iloc[0]) if not pname.empty else pid
                        st.write(f"• {label}: {val:g}/10")
                else:
                    st.write("🟢 Nenhuma característica relevante fora do perfil estruturado foi detectada.")


st.caption(
    f"Banco: {len(styles)} estilos · {len(references)} referências · "
    f"{len(aroma_ui)} descritores de aroma · {len(appearance_ui)} descritores de aparência · "
    f"{len(flavor_ui)} descritores de sabor · {len(mouthfeel_ui)} descritores de boca"
)
