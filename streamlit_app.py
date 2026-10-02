import streamlit as st
from pathlib import Path
import pandas as pd
import importlib.util
import re

st.set_page_config(
    page_title="BJCP Style Matcher",
    page_icon="🍺",
    layout="wide",
)

BASE = Path(__file__).resolve().parent
DATA_DIR = BASE / "data"

DB_CANDIDATES = [
    DATA_DIR / "bjcp_database.xlsx",
    BASE / "bjcp_database.xlsx",
]

MOTOR_CANDIDATES = [
    BASE / "motor_matching_v5_eliminatorio.py",
    DATA_DIR / "motor_matching_v5_eliminatorio.py",
    BASE / "motor_matching_v4_contagem.py",
    DATA_DIR / "motor_matching_v4_contagem.py",
    BASE / "motor_matching_v3_generico.py",
    DATA_DIR / "motor_matching_v3_generico.py",
]


# =========================================================
# ARQUIVOS
# =========================================================
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


def rank_by_perfil_sensorail(observations, perfil_df):
    """Ranking de proximidade usando o Perfil_Sensorial.

    Regras importantes:
    - RANGE não é comparado pelo texto "alto/baixo"; é comparado pelo PARÂMETRO
      e pela intensidade 0-10 do perfil.
    - CHECKBOX é comparado pelo descritor percebido.
    - A seção é normalizada sem diferenciar maiúsculas/minúsculas.
    - Termos genéricos não podem, sozinhos, fazer todos os estilos empatarem.
    """
    if perfil_df is None or perfil_df.empty:
        return []

    def norm(value):
        s = str(value or "").strip().lower()
        s = s.replace("ç", "c").replace("ã", "a").replace("á", "a")
        s = s.replace("é", "e").replace("ê", "e").replace("í", "i")
        s = s.replace("ó", "o").replace("ô", "o").replace("ú", "u")
        s = re.sub(r"[^a-z0-9]+", " ", s)
        return re.sub(r"\s+", " ", s).strip()

    def section_norm(section):
        s = norm(section)
        aliases = {
            "aroma": "aroma",
            "sabor": "flavor",
            "sensacao na boca": "mouthfeel",
            "sensacao na boca": "mouthfeel",
            "aparencia": "appearance",
            "final": "mouthfeel",
        }
        return aliases.get(s, s)

    # Parâmetros da interface -> conceitos que aparecem no Perfil_Sensorial.
    parameter_aliases = {
        "malte": ["malte", "cereal", "grainy", "pao", "caramelo", "tostado"],
        "lupulo": ["lupulo", "hop", "hoppy"],
        "esteres": ["esteres", "ester", "frutado"],
        "fenóis": ["fenol", "especiaria"],
        "fenóis": ["fenol", "especiaria"],
        "dulcor": ["dulcor", "doce", "sweet"],
        "amargor": ["amargor", "amargo", "bitterness", "bitter"],
        "alcool": ["alcool", "alcohol", "aquecimento"],
        "acidez": ["acidez", "acido", "sour", "sourness"],
        "aspereza": ["aspereza", "adstringencia", "harsh"],
        "corpo": ["corpo", "body"],
        "carbonatacao": ["carbonatacao", "carbonation"],
        "calor": ["calor", "aquecimento", "warmth"],
        "cremosidade": ["cremosidade", "creamy", "creamy body"],
        "adstringencia": ["adstringencia", "astringency", "harsh"],
        "limpidez": ["limpidez", "clara", "clear", "brilhante"],
        "tamanho colarinho": ["colarinho", "espuma", "head"],
        "retencao colarinho": ["retencao", "persistence", "persistente"],
        "equilibrio": ["equilibrio", "balance"],
    }

    # Termos da interface -> termos comuns no banco.
    term_aliases = {
        "grao": ["grao", "cereal", "granulado"],
        "citrico": ["citrico", "citrus"],
        "terroso": ["terroso", "earthy"],
        "floral": ["floral"],
        "gramineo": ["gramineo", "grassy"],
        "ervas": ["ervas", "herbal"],
        "pinho": ["pinho", "pine", "resinoso", "resin"],
        "condimento": ["condimento", "spice", "spicy"],
        "frutado": ["frutado", "fruity"],
        "berry": ["berry", "frutas vermelhas"],
        "frutas secas": ["frutas secas", "dried fruit"],
        "drupa": ["drupa", "stone fruit", "frutas de caroco"],
        "fruta tropical": ["fruta tropical", "tropical fruit"],
        "fruta escura": ["fruta escura", "dark fruit"],
        "caramelo": ["caramelo", "caramel"],
        "pao": ["pao", "bread", "bready"],
        "tostado": ["tostado", "toast", "toasty"],
        "torrado": ["torrado", "roasted"],
        "queimado": ["queimado", "burnt"],
        "especiaria": ["especiaria", "spice", "spicy"],
        "fumaça": ["fumaca", "smoke", "smoky"],
        "madeira": ["madeira", "oak", "wood"],
        "seco": ["seco", "dry"],
        "doce": ["doce", "sweet", "sweetness"],
        "amargo": ["amargo", "bitter"],
        "médio": ["medio", "medium"],
        "picante": ["picante", "spicy"],
    }

    intensity_to_10 = {
        "VERY_LOW": 1.0,
        "LOW": 2.5,
        "MEDIUM_LOW": 3.75,
        "MEDIUM": 5.0,
        "MEDIUM_HIGH": 6.25,
        "HIGH": 7.5,
        "VERY_HIGH": 9.5,
    }

    def best_checkbox_match(ob, g):
        term = norm(ob["term"])
        aliases = term_aliases.get(term, [term])
        candidates = g[g["_term"].apply(
            lambda x: any(a in x for a in aliases)
        )]
        if candidates.empty:
            return None, 0.0

        best = None
        best_score = -1.0
        for _, row in candidates.iterrows():
            status = row["_status"]
            base = {
                "typical": 1.0,
                "optional": 0.80,
                "permitted/variable": 0.65,
                "prohibited/fault": -1.0,
            }.get(status, 0.55)
            # Descritor explícito é mais importante que coincidência genérica.
            if any(a == row["_term"] for a in aliases):
                base += 0.15
            if base > best_score:
                best_score = base
                best = row
        return best, best_score

    def best_range_match(ob, g):
        parameter = norm(ob["parameter"])
        obs_i = ob["intensity"]
        aliases = parameter_aliases.get(parameter, [parameter])

        # Primeiro tenta pela subcategoria, depois pelo termo.
        def relevant(row):
            sub = norm(row["_subcat"])
            term = norm(row["_term"])
            return any(a in sub or a in term for a in aliases)

        candidates = g[g.apply(relevant, axis=1)]
        if candidates.empty:
            return None, 0.0

        candidates = candidates[candidates["_int"].notna()]
        if candidates.empty:
            return None, 0.0

        # Escolhe o registro mais próximo da intensidade observada.
        candidates = candidates.copy()
        candidates["_distance"] = (candidates["_int"] - obs_i).abs()
        row = candidates.sort_values("_distance").iloc[0]
        distance = float(row["_distance"])

        closeness = max(0.0, 1.0 - distance / 10.0)
        base = {
            "typical": 1.0,
            "optional": 0.80,
            "permitted/variable": 0.65,
            "prohibited/fault": -1.0,
        }.get(row["_status"], 0.55)

        return row, base * closeness

    obs = []
    for o in observations:
        tipo = str(o.get("Tipo") or "").upper()
        section = section_norm(o.get("Seção"))
        parameter = str(o.get("Parâmetro") or "").strip()
        value = str(o.get("Valor") or "").strip()
        intensity_code = str(o.get("Intensidade") or "").strip().upper()

        if tipo == "CHECKBOX":
            if norm(value) != "presente":
                continue
            obs.append({
                "kind": "checkbox",
                "section": section,
                "parameter": parameter,
                "term": parameter,
                "intensity": 5.0,
            })

        elif tipo == "RANGE":
            if intensity_code == "AUSENTE":
                continue

            # Cores são comparadas como categorias ordenadas, não como intensidade.
            if parameter in ("Cor da cerveja", "Cor do colarinho"):
                obs.append({
                    "kind": "color",
                    "section": section,
                    "parameter": parameter,
                    "term": value,
                    "intensity": 5.0,
                })
            elif intensity_code in intensity_to_10:
                obs.append({
                    "kind": "range",
                    "section": section,
                    "parameter": parameter,
                    "term": value,
                    "intensity": intensity_to_10[intensity_code],
                })

        # Equilíbrio e outros eixos serão tratados separadamente quando
        # a camada estruturada estiver completa.

    if not obs:
        return []

    df = perfil_df.copy()
    required = ["Código", "Estilo", "Parâmetro", "Termo PT", "Status"]
    if any(c not in df.columns for c in required):
        return []

    df["_param"] = df["Parâmetro"].astype(str)
    df["_param_norm"] = df["_param"].map(norm)
    df["_term"] = df["Termo PT"].astype(str).map(norm)
    df["_subcat"] = df["Subcategoria"].astype(str).map(norm) if "Subcategoria" in df.columns else ""
    df["_status"] = df["Status"].astype(str).str.lower()
    df["_int"] = pd.to_numeric(df["Intensidade 0-10"], errors="coerce") if "Intensidade 0-10" in df.columns else pd.NA

    results = []

    for (codigo, estilo), g in df.groupby(["Código", "Estilo"], dropna=False):
        total_weight = 0.0
        score = 0.0
        matched = 0
        details = []

        for ob in obs:
            # Restringe pela dimensão correta.
            candidates = g[g["_param_norm"] == ob["section"]]

            if ob["kind"] == "checkbox":
                row, local = best_checkbox_match(ob, candidates)
                weight = 1.25

            elif ob["kind"] == "range":
                row, local = best_range_match(ob, candidates)
                weight = 1.5

            elif ob["kind"] == "color":
                # Cor: usa termo + proximidade ordinal quando possível.
                palette = (
                    ["palha", "amarelo", "ouro", "ambar", "cobre", "marrom", "preto"]
                    if ob["parameter"] == "Cor da cerveja"
                    else ["branco", "marfim", "creme", "bege", "moreno", "marrom"]
                )
                observed = norm(ob["term"])
                candidates2 = candidates[
                    candidates["_term"].apply(lambda x: observed in x or x in observed)
                ]
                if candidates2.empty:
                    row, local = None, 0.0
                else:
                    row = candidates2.iloc[0]
                    local = {
                        "typical": 1.0,
                        "optional": 0.80,
                        "permitted/variable": 0.65,
                        "prohibited/fault": -1.0,
                    }.get(row["_status"], 0.55)
                weight = 1.25
            else:
                row, local, weight = None, 0.0, 1.0

            if row is not None:
                score += weight * local
                total_weight += weight
                if local > 0:
                    matched += 1
                    details.append(row["Termo PT"])
            else:
                # Falta de uma característica no perfil não é uma penalidade
                # automática: BJCP não diz que "não mencionado" = proibido.
                total_weight += weight * 0.25

        normalized_score = score / max(total_weight, 1e-9)

        results.append({
            "Código": str(codigo),
            "Estilo": str(estilo),
            "score": normalized_score,
            "matched": matched,
            "evaluated": len(obs),
            "display": f"{matched} / {len(obs)} observações compatíveis",
            "details": details,
        })

    # Desempate por score real, depois cobertura e número de correspondências.
    results.sort(
        key=lambda x: (x["score"], x["matched"]),
        reverse=True
    )
    return results[:3]


# =========================================================
# CONFIGURAÇÃO SENSORIAL
# =========================================================
INTENSITIES = {
    0: "Ausente",
    1: "Muito baixo",
    2: "Baixo",
    3: "Médio-baixo",
    4: "Médio",
    5: "Médio-alto",
    6: "Alto",
    7: "Muito alto",
}

INTENSITY_TO_CODE = {
    "Ausente": "AUSENTE",
    "Muito baixo": "VERY_LOW",
    "Baixo": "LOW",
    "Médio-baixo": "MEDIUM_LOW",
    "Médio": "MEDIUM",
    "Médio-alto": "MEDIUM_HIGH",
    "Alto": "HIGH",
    "Muito alto": "VERY_HIGH",
}


def add_intensity(section, parameter, label, default=0):
    """Controle de intensidade: slider."""
    value = st.slider(
        label,
        min_value=0,
        max_value=7,
        value=default,
        format="%d",
        key=f"slider_{section}_{parameter}",
    )

    st.caption(f"**{INTENSITIES[value]}**")

    observations.append({
        "Seção": section,
        "Parâmetro": parameter,
        "Tipo": "RANGE",
        "Valor": INTENSITIES[value],
        "Intensidade": INTENSITY_TO_CODE[INTENSITIES[value]],
    })


def add_fermentation_status(ester_intensity, phenol_intensity):
    """Deriva o perfil de fermentação a partir de ésteres e fenóis."""
    ester_code = INTENSITY_TO_CODE[INTENSITIES[ester_intensity]]
    phenol_code = INTENSITY_TO_CODE[INTENSITIES[phenol_intensity]]

    if ester_intensity == 0 and phenol_intensity == 0:
        status = "Fermentação limpa"
        explanation = "Ésteres e fenóis estão ausentes."
    else:
        status = "Fermentação com caráter perceptível"
        present = []
        if ester_intensity > 0:
            present.append(f"ésteres: {INTENSITIES[ester_intensity].lower()}")
        if phenol_intensity > 0:
            present.append(f"fenóis: {INTENSITIES[phenol_intensity].lower()}")
        explanation = " / ".join(present)

    st.info(f"**Perfil de fermentação: {status}** — {explanation}")

    observations.append({
        "Seção": "Aroma",
        "Parâmetro": "Perfil de fermentação",
        "Tipo": "DERIVED",
        "Valor": status,
        "Intensidade": "",
    })


def add_checkbox(section, parameter, label, group=""):
    """Controle de presença: checkbox.

    A chave inclui o grupo porque um mesmo descritor pode aparecer
    em mais de uma família (ex.: Cítrico em Lúpulo e Ésteres).
    """
    safe_group = str(group).strip().replace(" ", "_")
    safe_parameter = str(parameter).strip().replace(" ", "_")
    key = f"check_{section}_{safe_group}_{safe_parameter}"

    value = st.checkbox(
        label,
        key=key,
    )

    observations.append({
        "Seção": section,
        "Parâmetro": parameter,
        "Tipo": "CHECKBOX",
        "Valor": "presente" if value else "ausente",
        "Intensidade": "",
    })


def add_checkbox_group(section, title, items):
    st.markdown(f"**{title}**")
    cols = st.columns(4)

    for i, item in enumerate(items):
        with cols[i % 4]:
            add_checkbox(section, item, item, group=title)


def add_color_checkboxes(section, parameter_prefix, title, colors):
    st.markdown(f"**{title}**")
    cols = st.columns(7)

    for i, color in enumerate(colors):
        with cols[i]:
            add_checkbox(section, f"{parameter_prefix}_{color}", color)


# =========================================================
# CARREGAMENTO
# =========================================================
st.title("🍺 BJCP Style Matcher")
st.caption(
    "Protótipo de avaliação sensorial baseado na estrutura da súmula BJCP."
)

db = find_database()

if db is None:
    st.error("Banco Excel não encontrado.")
    st.code("data/bjcp_database.xlsx")
    st.stop()

motor = load_motor()

if motor is None:
    st.info(
        "Motor externo não encontrado. A interface está funcionando, "
        "mas o cálculo completo será conectado ao motor posteriormente."
    )

try:
    excel = pd.ExcelFile(db)

except Exception as e:
    st.error(f"Erro ao ler o banco: {e}")
    st.stop()


# =========================================================
# RESET DA AVALIAÇÃO
# =========================================================
def reset_evaluation():
    """Zera explicitamente todos os widgets sensoriais e mantém o estilo."""
    # IMPORTANTE:
    # Em Streamlit, apenas apagar a chave de um widget não é suficiente:
    # na próxima execução o widget pode recuperar seu valor anterior.
    # Por isso, definimos explicitamente o estado inicial de cada família.
    for key in list(st.session_state.keys()):
        key_str = str(key)

        if key_str == "style_selector" or key_str.startswith("btn_"):
            continue

        if key_str.startswith("slider_"):
            st.session_state[key] = 0

        elif key_str.startswith("check_"):
            st.session_state[key] = False

        elif key_str.startswith("color_"):
            st.session_state[key] = 0

        elif key_str == "sabor_equilibrio":
            st.session_state[key] = "Equilibrado"

        # Outros estados auxiliares da interface não devem carregar
        # a avaliação anterior.
        elif key_str.startswith("resultado_") or key_str.startswith("possibilidade_"):
            del st.session_state[key]


# =========================================================
# SIDEBAR
# =========================================================
with st.sidebar:
    st.header("🍺 BJCP Style Matcher")

    # Carrega todos os estilos disponíveis na aba Estilos do banco.
    styles_df = load_sheet(db, "Estilos") if "Estilos" in excel.sheet_names else pd.DataFrame()

    if not styles_df.empty and "Código" in styles_df.columns and "Estilo" in styles_df.columns:
        style_options = [
            f"{str(row['Código']).strip()} — {str(row['Estilo']).strip()}"
            for _, row in styles_df.iterrows()
            if pd.notna(row["Código"]) and pd.notna(row["Estilo"])
        ]
    else:
        style_options = ["1A — American Light Lager"]

    selected_style = st.selectbox(
        "Estilo em avaliação",
        style_options,
        index=0,
        key="style_selector",
    )

    selected_style_code = selected_style.split(" — ", 1)[0].strip()

    st.button(
        "🧹 Zerar todos os parâmetros",
        use_container_width=True,
        on_click=reset_evaluation,
        key="btn_zerar_avaliacao",
        help="Zera todos os parâmetros sensoriais e mantém o estilo selecionado.",
    )

    st.divider()

    st.write("**Banco de dados**")
    st.caption(db.name)
    st.caption(f"{len(style_options)} estilos disponíveis")

    st.write("**Interface**")
    st.caption("Checklist sensorial BJCP")

    st.divider()
    st.caption(
        "Os controles de intensidade usam a escala linguística "
        "do modelo do aplicativo."
    )

# Carrega SOMENTE as regras do estilo atualmente selecionado.
if "Regras_Estilo_v6" in excel.sheet_names:
    all_rules = load_sheet(db, "Regras_Estilo_v6")
    if "Código" in all_rules.columns:
        rules = all_rules[
            all_rules["Código"].astype(str).str.strip().eq(selected_style_code)
        ].copy()
    else:
        rules = pd.DataFrame()
else:
    rules = pd.DataFrame()

# =========================================================
# AVALIAÇÃO
# =========================================================
st.header("1. Avaliação sensorial")

observations = []

tab_aroma, tab_aparencia, tab_sabor, tab_boca, tab_falhas, tab_resultados, tab_possibilidades = st.tabs([
    "🌸 Aroma",
    "👁️ Aparência",
    "👅 Sabor",
    "💧 Sensação na boca",
    "⚠️ Falhas / Off-flavors",
    "📊 Resultados",
    "🔎 Possibilidades",
])


# =========================================================
# AROMA
# =========================================================
with tab_aroma:

    st.subheader("Aroma")

    st.markdown("### Intensidade")

    col1, col2 = st.columns(2)

    with col1:
        add_intensity("Aroma", "Malte", "Malte")
        add_intensity("Aroma", "Lúpulo", "Lúpulo")

        ester_intensity = st.slider(
            "Ésteres",
            min_value=0,
            max_value=7,
            value=0,
            step=1,
            key="slider_Aroma_Ésteres",
        )
        st.caption(f"**{INTENSITIES[ester_intensity]}**")
        observations.append({
            "Seção": "Aroma",
            "Parâmetro": "Ésteres",
            "Tipo": "RANGE",
            "Valor": INTENSITIES[ester_intensity],
            "Intensidade": INTENSITY_TO_CODE[INTENSITIES[ester_intensity]],
        })

        phenol_intensity = st.slider(
            "Fenóis",
            min_value=0,
            max_value=7,
            value=0,
            step=1,
            key="slider_Aroma_Fenóis",
        )
        st.caption(f"**{INTENSITIES[phenol_intensity]}**")
        observations.append({
            "Seção": "Aroma",
            "Parâmetro": "Fenóis",
            "Tipo": "RANGE",
            "Valor": INTENSITIES[phenol_intensity],
            "Intensidade": INTENSITY_TO_CODE[INTENSITIES[phenol_intensity]],
        })

        add_fermentation_status(ester_intensity, phenol_intensity)

    with col2:
        add_intensity("Aroma", "Álcool", "Álcool")
        add_intensity("Aroma", "Dulçor", "Dulçor")
        add_intensity("Aroma", "Acidez", "Acidez")

    st.divider()

    st.markdown("### Características percebidas")

    add_checkbox_group(
        "Aroma",
        "Malte",
        [
            "Grão",
            "Caramelo",
            "Pão",
            "Rico",
            "Fruta Escura",
            "Tostado",
            "Torrado",
            "Queimado",
        ],
    )

    add_checkbox_group(
        "Aroma",
        "Lúpulo",
        [
            "Cítrico",
            "Terroso",
            "Floral",
            "Gramíneo",
            "Ervas",
            "Pinho",
            "Condimento",
            "Madeira",
        ],
    )

    add_checkbox_group(
        "Aroma",
        "Ésteres",
        [
            "Frutado",
            "Maçã/Pera",
            "Banana",
            "Berry",
            "Cítrico",
            "Frutas Secas",
            "Uva",
            "Drupa",
        ],
    )

    add_checkbox_group(
        "Aroma",
        "Outros",
        [
            "Brettanomyces",
            "Fruta",
            "Lático",
            "Fumaça",
            "Especiaria",
            "Vinho",
            "Madeira",
        ],
    )


# =========================================================
# APARÊNCIA
# =========================================================
with tab_aparencia:

    st.subheader("Aparência")

    st.markdown("### Intensidade")

    col1, col2 = st.columns(2)

    with col1:
        add_intensity("Aparência", "Limpidez", "Limpidez")
        add_intensity("Aparência", "Tamanho Colarinho", "Tamanho do colarinho")

    with col2:
        add_intensity("Aparência", "Retenção Colarinho", "Retenção do colarinho")

    st.divider()

    st.markdown("### Cor")

    beer_colors = [
        ("Palha", "#F7E9A8"),
        ("Amarelo", "#F2D34F"),
        ("Ouro", "#D9A52E"),
        ("Âmbar", "#B86A1B"),
        ("Cobre", "#9A4B22"),
        ("Marrom", "#603B28"),
        ("Preto", "#17130F"),
    ]

    head_colors = [
        ("Branco", "#FFFFFF"),
        ("Marfim", "#FFF3D1"),
        ("Creme", "#F2D5A4"),
        ("Bege", "#D8B98A"),
        ("Moreno", "#8B684B"),
        ("Marrom", "#5A3826"),
    ]

    def add_color_slider(section, parameter, label, palette):
        names = [item[0] for item in palette]

        index = st.slider(
            label,
            min_value=0,
            max_value=len(names) - 1,
            value=0,
            step=1,
            key=f"color_{section}_{parameter}",
        )

        name, hex_color = palette[index]

        st.markdown(
            f'''
            <div style="
                display:flex;
                align-items:center;
                gap:14px;
                margin-top:-4px;
                margin-bottom:14px;
            ">
                <div style="
                    width:58px;
                    height:32px;
                    border-radius:6px;
                    background:{hex_color};
                    border:1px solid rgba(255,255,255,.35);
                    box-shadow:0 1px 4px rgba(0,0,0,.25);
                "></div>
                <div style="font-size:1.05rem;font-weight:600;">{name}</div>
            </div>
            ''',
            unsafe_allow_html=True,
        )

        observations.append({
            "Seção": section,
            "Parâmetro": parameter,
            "Tipo": "RANGE",
            "Valor": name,
            "Intensidade": name,
        })

    add_color_slider(
        "Aparência",
        "Cor da cerveja",
        "Cor da cerveja",
        beer_colors,
    )

    add_color_slider(
        "Aparência",
        "Cor do colarinho",
        "Cor do colarinho",
        head_colors,
    )

    st.markdown("**Outros aspectos**")
    add_checkbox_group(
        "Aparência",
        "Outros",
        [
            "Flat",
            "Renda",
            "Lágrimas",
            "Opaco",
        ],
    )


# =========================================================
# SABOR
# =========================================================
with tab_sabor:

    st.subheader("Sabor")

    st.markdown("### Intensidade")

    col1, col2 = st.columns(2)

    with col1:
        add_intensity("Sabor", "Malte", "Malte")
        add_intensity("Sabor", "Lúpulo", "Lúpulo")
        add_intensity("Sabor", "Ésteres", "Ésteres")
        add_intensity("Sabor", "Fenóis", "Fenóis")
        add_intensity("Sabor", "Dulçor", "Dulçor")

    with col2:
        add_intensity("Sabor", "Amargor", "Amargor")
        add_intensity("Sabor", "Álcool", "Álcool")
        add_intensity("Sabor", "Acidez", "Acidez")
        add_intensity("Sabor", "Aspereza", "Aspereza")

    st.divider()

    st.markdown("### Características percebidas")

    add_checkbox_group(
        "Sabor",
        "Malte",
        [
            "Grão",
            "Caramelo",
            "Pão",
            "Rico",
            "Fruta Escura",
            "Tostado",
            "Torrado",
            "Queimado",
        ],
    )

    add_checkbox_group(
        "Sabor",
        "Lúpulo",
        [
            "Cítrico",
            "Terroso",
            "Floral",
            "Gramíneo",
            "Ervas",
            "Pinho",
            "Condimento",
            "Madeira",
        ],
    )

    add_checkbox_group(
        "Sabor",
        "Ésteres",
        [
            "Frutado",
            "Maçã/Pera",
            "Banana",
            "Berry",
            "Cítrico",
            "Frutas Secas",
            "Uva",
            "Drupa",
        ],
    )

    add_checkbox_group(
        "Sabor",
        "Outros",
        [
            "Brett.",
            "Fruta",
            "Lático",
            "Fumaça",
            "Especiaria",
            "Vinho",
            "Madeira",
        ],
    )

    st.markdown("### Equilíbrio")

    balance = st.select_slider(
        "Equilíbrio",
        options=["Malte", "Equilibrado", "Lúpulo"],
        value="Equilibrado",
        key="sabor_equilibrio",
    )

    st.caption(f"**{balance}**")

    observations.append({
        "Seção": "Sabor",
        "Parâmetro": "Equilíbrio",
        "Tipo": "RANGE",
        "Valor": balance,
        "Intensidade": balance,
    })


# =========================================================
# SENSAÇÃO NA BOCA
# =========================================================
with tab_boca:

    st.subheader("Sensação na boca")

    st.markdown("### Intensidade")

    col1, col2 = st.columns(2)

    with col1:
        add_intensity("Sensação na Boca", "Corpo", "Corpo")
        add_intensity("Sensação na Boca", "Carbonatação", "Carbonatação")
        add_intensity("Sensação na Boca", "Calor", "Calor")

    with col2:
        add_intensity("Sensação na Boca", "Cremosidade", "Cremosidade")
        add_intensity("Sensação na Boca", "Adstringência", "Adstringência")

    st.divider()

    st.markdown("### Falhas")

    add_checkbox_group(
        "Sensação na Boca",
        "Falhas",
        [
            "Choca",
            "Gusher",
            "Quente",
            "Áspero",
            "Escorregadio",
        ],
    )

    st.divider()

    st.markdown("### Final")

    add_checkbox_group(
        "Sensação na Boca",
        "Final",
        [
            "Enjoativo",
            "Doce",
            "Médio",
            "Seco",
            "Picante",
        ],
    )


# =========================================================
# FALHAS / OFF-FLAVORS
# =========================================================
with tab_falhas:

    st.subheader("Falhas / Off-flavors")

    st.caption(
        "Marque somente as falhas que foram percebidas na amostra."
    )

    st.markdown("### Aroma / Fermentação")

    add_checkbox_group(
        "Falhas",
        "Aroma / Fermentação",
        [
            "Acetaldeído",
            "Atingido por Luz",
            "Azedo/Ácido",
            "Alcoólico/Quente",
            "Adstringente",
            "Diacetil",
            "DMS",
            "Esterificado",
            "Gramíneo",
        ],
    )

    st.divider()

    st.markdown("### Sabor")

    add_checkbox_group(
        "Falhas",
        "Sabor",
        [
            "Medicinal",
            "Metálico",
            "Mofo",
            "Oxidado",
            "Plástico",
            "Solvente/Fusel",
            "Vinagre",
        ],
    )

    st.divider()

    st.markdown("### Boca / Outros")

    add_checkbox_group(
        "Falhas",
        "Boca / Outros",
        [
            "Fumaça",
            "Condimento",
            "Enxofre",
            "Vegetal",
            "Levedura",
        ],
    )


# =========================================================
# FEEDBACK DO MATCHING
# =========================================================
COLOR_BEER_ORDER = [
    "Palha", "Amarelo", "Ouro", "Âmbar", "Cobre", "Marrom", "Preto"
]

COLOR_HEAD_ORDER = [
    "Branco", "Marfim", "Creme", "Bege", "Moreno", "Marrom"
]


def color_position(value, palette):
    try:
        return palette.index(value)
    except ValueError:
        return None


def feedback_for_rule(rule, observation):
    """Retorna estado, texto observado e texto esperado."""
    parameter = str(rule.get("Parâmetro") or "")
    rule_type = str(rule.get("Regra") or "").upper()
    measurement = str(rule.get("measurement_type") or "").upper()
    range_type = str(rule.get("range_type") or "").upper()

    if observation is None:
        return (
            "ERRO",
            "Ausente",
            "Não informado",
            f"{parameter}: o estilo exige uma característica que não foi informada."
        )

    observed_value = str(observation.get("Valor") or "")
    observed_intensity = str(observation.get("Intensidade") or "")

    # -------------------------
    # CORES
    # -------------------------
    if range_type == "COLOR_BEER":
        palette = COLOR_BEER_ORDER
        pos = color_position(observed_value, palette)

        min_op = rule.get("Min_Operacional")
        max_op = rule.get("Max_Operacional")

        try:
            min_pos = int(min_op) - 1
            max_pos = int(max_op) - 1
        except (TypeError, ValueError):
            min_pos = max_pos = None

        if pos is not None and min_pos is not None and max_pos is not None:
            expected_min = palette[max(0, min_pos)]
            expected_max = palette[min(len(palette) - 1, max_pos)]

            if min_pos <= pos <= max_pos:
                return (
                    "OK",
                    observed_value,
                    f"{expected_min} → {expected_max}",
                    f"{parameter}: dentro da faixa esperada."
                )
            if pos < min_pos:
                return (
                    "ABAIXO",
                    observed_value,
                    f"{expected_min} → {expected_max}",
                    f"{parameter}: sua cor está mais clara que a faixa esperada pelo estilo."
                )
            return (
                "ACIMA",
                observed_value,
                f"{expected_min} → {expected_max}",
                f"{parameter}: sua cor está mais escura que a faixa esperada pelo estilo."
            )

    if range_type == "COLOR_HEAD":
        palette = COLOR_HEAD_ORDER
        pos = color_position(observed_value, palette)

        if pos is not None:
            expected = "Branco"
            if observed_value == expected:
                return (
                    "OK",
                    observed_value,
                    expected,
                    f"{parameter}: correto."
                )
            return (
                "DESVIO",
                observed_value,
                expected,
                f"{parameter}: o estilo pede {expected}; você marcou {observed_value}."
            )

    # -------------------------
    # PROHIBITED
    # -------------------------
    if rule_type == "PROHIBITED":
        present = observed_value.lower() == "presente"

        if present:
            return (
                "PROIBIDO",
                "Presente",
                "Ausente",
                f"{parameter}: esta característica não é permitida para o estilo."
            )

        # PROHIBITED ausente não precisa aparecer no relatório.
        return (
            "IGNORAR",
            "Ausente",
            "Ausente",
            f"{parameter}: ausente, portanto sem desvio."
        )

    # -------------------------
    # CHECKBOX
    # -------------------------
    if measurement == "CHECKBOX":
        present = observed_value.lower() == "presente"

        if rule_type == "REQUIRED":
            if present:
                return (
                    "OK",
                    "Presente",
                    "Presente",
                    f"{parameter}: característica esperada e percebida."
                )
            return (
                "ERRO",
                "Ausente",
                "Presente",
                f"{parameter}: o estilo espera essa característica, mas ela foi marcada como ausente."
            )

        if rule_type == "OPTIONAL":
            if present:
                return (
                    "OK",
                    "Presente",
                    "Opcional",
                    f"{parameter}: presente, mas permitido pelo estilo."
                )
            return (
                "OK",
                "Ausente",
                "Opcional",
                f"{parameter}: ausente; isso é permitido porque a característica é opcional."
            )

    # -------------------------
    # INTENSIDADE
    # -------------------------
    levels_pt = {
        "AUSENTE": "Ausente",
        "VERY_LOW": "Muito baixo",
        "LOW": "Baixo",
        "MEDIUM_LOW": "Médio-baixo",
        "MEDIUM": "Médio",
        "MEDIUM_HIGH": "Médio-alto",
        "HIGH": "Alto",
        "VERY_HIGH": "Muito alto",
    }

    level_num = {
        "AUSENTE": 0,
        "VERY_LOW": 1,
        "LOW": 2,
        "MEDIUM_LOW": 3,
        "MEDIUM": 4,
        "MEDIUM_HIGH": 5,
        "HIGH": 6,
        "VERY_HIGH": 7,
    }

    obs_num = level_num.get(observed_intensity)
    min_level = str(rule.get("Min_Linguístico") or "").upper()
    max_level = str(rule.get("Max_Linguístico") or "").upper()
    min_num = level_num.get(min_level)
    max_num = level_num.get(max_level)

    if obs_num is not None and min_num is not None and max_num is not None:
        expected = levels_pt[min_level]
        if min_level != max_level:
            expected = f"{levels_pt[min_level]} → {levels_pt[max_level]}"

        if min_num <= obs_num <= max_num:
            return (
                "OK",
                levels_pt.get(observed_intensity, observed_intensity),
                expected,
                f"{parameter}: dentro da intensidade esperada."
            )

        if obs_num < min_num:
            return (
                "ABAIXO",
                levels_pt.get(observed_intensity, observed_intensity),
                expected,
                f"{parameter}: intensidade abaixo do que o estilo descreve."
            )

        return (
            "ACIMA",
            levels_pt.get(observed_intensity, observed_intensity),
            expected,
            f"{parameter}: intensidade acima do que o estilo descreve."
        )

    return (
        "INFO",
        observed_value or observed_intensity,
        str(rule.get("Termo_BJCP") or "Não especificado"),
        f"{parameter}: comparação detalhada ainda não configurada."
    )


def render_feedback(results):
    st.subheader("🔎 Feedback da avaliação")

    categories = [
        ("Aroma", "🌸"),
        ("Aparência", "👁️"),
        ("Sabor", "👅"),
        ("Sensação na Boca", "💧"),
        ("Falhas", "⚠️"),
    ]

    grouped = {name: [] for name, _ in categories}

    for item in results:
        section, status, parameter, observed, expected, message = item
        section = str(section)

        if section == "Sensação na boca":
            section = "Sensação na Boca"
        elif section.lower() in ("falha", "falhas", "off-flavors"):
            section = "Falhas"

        if section not in grouped:
            section = "Aroma"

        grouped[section].append(
            (status, parameter, observed, expected, message)
        )

    for category, icon in categories:
        items = grouped[category]
        if not items:
            continue

        st.divider()
        st.markdown(f"### {icon} {category}")

        ok_count = sum(x[0] == "OK" for x in items)
        warning_count = sum(
            x[0] in ("ABAIXO", "ACIMA", "DESVIO") for x in items
        )
        error_count = sum(
            x[0] in ("ERRO", "PROIBIDO")
            for x in items
        )

        summary = []
        if ok_count:
            summary.append(f"✅ {ok_count} compatível(eis)")
        if warning_count:
            summary.append(f"❌ {warning_count} desvio(s)")
        if error_count:
            summary.append(f"❌ {error_count} problema(s)")

        if summary:
            st.caption(" · ".join(summary))

        for status, parameter, observed, expected, message in items:
            text = (
                f"**{parameter}**  \n"
                f"Você marcou: **{observed}**  \n"
                f"Estilo pede: **{expected}**  \n"
            )

            if status == "OK":
                st.success(text + f"✓ {message}")
            elif status in ("ABAIXO", "ACIMA", "DESVIO"):
                st.error(text + f"✗ {message}")
            elif status == "ERRO":
                st.error(text + f"✗ {message}")
            elif status == "PROIBIDO":
                st.error(text + f"⛔ {message}")
            elif status == "IGNORAR":
                continue
            else:
                st.info(text + message)


# =========================================================
# POSSIBILIDADES — 3 ESTILOS MAIS PRÓXIMOS
# =========================================================

with tab_possibilidades:
    st.subheader("🔎 Possibilidades")
    st.info(
        "Primeiro o sistema elimina estilos que falham em critérios eliminatórios. "
        "Só depois compara os parâmetros restantes para encontrar as 3 combinações mais próximas."
    )

    st.markdown(
        """
        **Critérios eliminatórios**
        - 🔴 REQUIRED não atendido → estilo eliminado
        - 🔴 UNEXPECTED detectado → estilo eliminado
        - 🔴 PROHIBITED detectado → estilo eliminado

        Depois disso, são analisados os parâmetros **OPTIONAL** e demais características
        compatíveis para ordenar as possibilidades.
        """
    )

    if st.button(
        "🔎 Encontrar 3 estilos mais próximos",
        type="primary",
        use_container_width=True,
        key="btn_possibilidades",
    ):
        try:
            # Procura regras estruturadas por estilo.
            possible_rule_sheets = [
                "Regras_Estilo_v6",
            ]
            rules_for_possibilities = None
            rule_sheet_used = None

            for sheet in possible_rule_sheets:
                if sheet in excel.sheet_names:
                    candidate = load_sheet(db, sheet)
                    # Só usa a planilha se ela realmente tiver uma coluna de estilo.
                    style_cols = [
                        c for c in ["Código", "Codigo", "Código_Estilo", "Estilo", "Style"]
                        if c in candidate.columns
                    ]
                    if style_cols:
                        rules_for_possibilities = candidate
                        rule_sheet_used = sheet
                        break

            structured_styles = 0
            if rules_for_possibilities is not None:
                style_col = next(
                    (c for c in ["Código", "Codigo", "Código_Estilo", "Estilo", "Style"]
                     if c in rules_for_possibilities.columns),
                    None,
                )
                if style_col:
                    structured_styles = rules_for_possibilities[style_col].dropna().astype(str).nunique()

            if (
                motor is not None
                and hasattr(motor, "rank_styles")
                and rules_for_possibilities is not None
                and structured_styles >= 3
            ):
                ranked = motor.rank_styles(observations, rules_for_possibilities)
                fonte = f"regras eliminatórias ({rule_sheet_used})"
            else:
                # O banco v31 já possui Perfil_Sensorial para praticamente todos os estilos,
                # então não deixamos a aba vazia enquanto a camada eliminatória é expandida.
                perfil = load_sheet(db, "Perfil_Sensorial") if "Perfil_Sensorial" in excel.sheet_names else pd.DataFrame()
                ranked = rank_by_perfil_sensorail(observations, perfil)
                fonte = "Perfil_Sensorial BJCP 2021 (proximidade)"

            if not ranked:
                st.info(
                    "Preencha pelo menos uma característica sensorial como presente "
                    "ou uma intensidade acima de Ausente para gerar as 3 possibilidades."
                )
            else:
                st.caption(
                    f"3 possibilidades mais próximas pela fonte: {fonte}. "
                    "Esta etapa de proximidade não substitui o filtro eliminatório completo."
                )
                for i, item in enumerate(ranked[:3], start=1):
                    st.markdown(f"### {i}. {item['Código']} — {item['Estilo']}")
                    st.success(f"**{item['display']}**")
                    if item.get("details"):
                        st.caption("Correspondências: " + ", ".join(dict.fromkeys(item["details"])))
                    if i < min(3, len(ranked)):
                        st.divider()

        except Exception as e:
            st.error(f"Erro ao calcular possibilidades: {e}")
            st.exception(e)


# =========================================================
# RESULTADO — ABA
# =========================================================
with tab_resultados:

    st.subheader("Resultado da avaliação")

    st.info(
        "O resultado é uma contagem de características compatíveis. "
        "Exemplo: **19 / 30** significa 19 itens compatíveis de 30 avaliados."
    )

    st.caption(
        "Aqui aparecerão a compatibilidade, os desvios encontrados e o "
        "comparativo entre o que você percebeu e o que o estilo espera."
    )

    if rules.empty:
        st.warning(
            f"Este banco ainda não possui regras estruturadas para {selected_style_code}. "
            "O aplicativo não vai usar regras de outro estilo para preencher o feedback."
        )

    if st.button(
        "🍺 Calcular compatibilidade",
        type="primary",
        use_container_width=True,
    ):

        try:
            rule_records = rules.to_dict("records")

            # Executa o motor e normaliza o retorno para o formato:
            # result = {"matched": ..., "evaluated": ..., "display": "..."}
            if motor is not None and hasattr(motor, "calculate"):
                motor_output = motor.calculate(observations, rule_records)

                # Motor v4: retorna (result_dict, details)
                if (
                    isinstance(motor_output, tuple)
                    and len(motor_output) == 2
                    and isinstance(motor_output[0], dict)
                ):
                    result, details = motor_output

                # Permite também um motor que retorne apenas o dict.
                elif isinstance(motor_output, dict):
                    result = motor_output
                    details = motor_output.get("details", [])

                # Compatibilidade com versões antigas.
                elif isinstance(motor_output, tuple) and len(motor_output) == 2:
                    legacy_score, details = motor_output
                    result = {
                        "matched": 0,
                        "evaluated": 0,
                        "display": str(legacy_score),
                    }
                else:
                    raise TypeError(
                        f"Formato de retorno do motor não reconhecido: "
                        f"{type(motor_output).__name__}"
                    )
            else:
                st.warning(
                    "Motor externo não encontrado. Mostrando apenas o feedback "
                    "sensorial enquanto o motor não estiver conectado."
                )
                result = None
                details = []

            # -------------------------------------------------
            # Feedback humano: observado x esperado
            # -------------------------------------------------
            observation_map = {
                (
                    str(o.get("Seção") or ""),
                    str(o.get("Parâmetro") or ""),
                ): o
                for o in observations
            }

            feedback_results = []

            for rule in rule_records:
                rule_type = str(rule.get("Regra") or "").upper()

                # REQUIRED sempre é relevante.
                # OPTIONAL só é relevante quando foi percebido.
                # PROHIBITED só é relevante quando foi percebido.
                if rule_type not in ("REQUIRED", "OPTIONAL", "PROHIBITED"):
                    continue

                key = (
                    str(rule.get("Seção") or ""),
                    str(rule.get("Parâmetro") or ""),
                )

                observation = observation_map.get(key)

                # Evita mostrar parâmetros derivados como se fossem regras normais.
                if str(rule.get("measurement_type") or "").upper() == "DERIVED":
                    continue

                # OPTIONAL: só aparece se foi percebido.
                # CHECKBOX -> precisa estar Presente.
                # RANGE -> precisa ser diferente de Ausente.
                if rule_type == "OPTIONAL":
                    if observation is None:
                        continue

                    measurement_type = str(
                        rule.get("measurement_type") or ""
                    ).upper()

                    observed_value = str(
                        observation.get("Valor") or ""
                    ).strip().lower()

                    observed_intensity = str(
                        observation.get("Intensidade") or ""
                    ).strip().upper()

                    if measurement_type == "CHECKBOX":
                        if observed_value != "presente":
                            continue
                    else:
                        if (
                            observed_value == "ausente"
                            or observed_intensity == "AUSENTE"
                        ):
                            continue

                # PROHIBITED: só aparece se foi percebido.
                if rule_type == "PROHIBITED":
                    if observation is None:
                        continue

                    observed_value = str(observation.get("Valor") or "").lower()
                    if observed_value != "presente":
                        continue

                feedback_result = feedback_for_rule(rule, observation)

                feedback_results.append((
                    str(rule.get("Seção") or ""),
                    feedback_result[0],
                    str(rule.get("Parâmetro") or ""),
                    feedback_result[1],
                    feedback_result[2],
                    feedback_result[3],
                ))

            # -------------------------------------------------
            # Características inesperadas presentes
            # -------------------------------------------------
            rule_keys = {
                (
                    str(r.get("Seção") or ""),
                    str(r.get("Parâmetro") or ""),
                )
                for r in rule_records
            }

            for obs in observations:
                key = (
                    str(obs.get("Seção") or ""),
                    str(obs.get("Parâmetro") or ""),
                )

                if (
                    key not in rule_keys
                    and str(obs.get("Valor") or "").lower() == "presente"
                ):
                    parameter = str(obs.get("Parâmetro") or "")
                    feedback_results.append((
                        str(obs.get("Seção") or ""),
                        "DESVIO",
                        parameter,
                        "Presente",
                        "Não previsto no perfil estruturado",
                        f"{parameter}: foi percebido, mas não está estabelecido como característica esperada ou opcional deste estilo.",
                    ))

            # -------------------------------------------------
            # Resumo
            # -------------------------------------------------
            if result is not None:
                c1, c2, c3 = st.columns(3)
                c1.metric("Itens compatíveis", result["display"])
                c2.metric("Estilo", selected_style_code)
                c3.metric("Itens analisados", len(feedback_results))

            render_feedback(feedback_results)

            # Tabela técnica fica secundária.
            with st.expander("Ver detalhamento técnico do motor"):
                if details:
                    st.dataframe(
                        pd.DataFrame(
                            details,
                            columns=[
                                "Parâmetro",
                                "Regra",
                                "Compatível",
                            ],
                        ),
                        use_container_width=True,
                        hide_index=True,
                    )
                else:
                    st.info("O motor não retornou detalhes técnicos.")

            with st.expander("Ver dados coletados"):
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
    "Interface inspirada na estrutura da Súmula de Cerveja BJCP. "
    "A escala operacional do aplicativo não representa uma pontuação oficial do BJCP."
)
