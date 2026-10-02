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
DATA_DIR = BASE / "data"

DB_CANDIDATES = [
    DATA_DIR / "bjcp_database.xlsx",
    BASE / "bjcp_database.xlsx",
]

MOTOR_CANDIDATES = [
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
    rule_sheet = next(
        (
            s for s in ["Regras_1A_v2", "Regras_1A"]
            if s in excel.sheet_names
        ),
        None,
    )

    if rule_sheet:
        rules = load_sheet(db, rule_sheet)
    else:
        rules = pd.DataFrame()

except Exception as e:
    st.error(f"Erro ao ler o banco: {e}")
    st.stop()


# =========================================================
# SIDEBAR
# =========================================================
with st.sidebar:
    st.header("🍺 BJCP Style Matcher")

    st.selectbox(
        "Estilo em avaliação",
        ["1A — American Light Lager"],
    )

    st.divider()

    st.write("**Banco de dados**")
    st.caption(db.name)

    st.write("**Interface**")
    st.caption("Checklist sensorial BJCP")

    st.divider()
    st.caption(
        "Os controles de intensidade usam a escala linguística "
        "do modelo do aplicativo."
    )


# =========================================================
# AVALIAÇÃO
# =========================================================
st.header("1. Avaliação sensorial")

observations = []

tab_aroma, tab_aparencia, tab_sabor, tab_boca = st.tabs([
    "🌸 Aroma",
    "👁️ Aparência",
    "👅 Sabor",
    "💧 Sensação na boca",
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
        add_intensity("Aroma", "Ésteres", "Ésteres")
        add_intensity("Aroma", "Fenóis", "Fenóis")

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
        add_intensity("Aparência", "Textura Colarinho", "Textura do colarinho")

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

    add_checkbox_group(
        "Sabor",
        "Equilíbrio",
        [
            "Malte",
            "Lúpulo",
            "Equilibrado",
        ],
    )


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

    st.markdown("### Falhas / características percebidas")

    add_checkbox_group(
        "Sensação na Boca",
        "Final",
        [
            "Choca",
            "Gusher",
            "Quente",
            "Áspero",
            "Escorregadio",
            "Enjoativo",
            "Doce",
            "Médio",
            "Seco",
            "Picante",
        ],
    )


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

    if motor is None or not hasattr(motor, "calculate"):
        st.warning(
            "A interface está pronta, mas o motor de matching completo "
            "ainda precisa ser conectado a esta nova estrutura de entrada."
        )

        with st.expander("Ver dados coletados"):
            st.dataframe(
                pd.DataFrame(observations),
                use_container_width=True,
                hide_index=True,
            )

    else:
        try:
            score, details = motor.calculate(
                observations,
                rules.to_dict("records"),
            )

            c1, c2, c3 = st.columns(3)

            c1.metric(
                "Compatibilidade",
                f"{score:.2f}%",
            )

            c2.metric(
                "Estilo",
                "1A",
            )

            c3.metric(
                "Características avaliadas",
                len(observations),
            )

            if score >= 80:
                st.success("Alta compatibilidade operacional.")
            elif score >= 60:
                st.warning("Compatibilidade intermediária.")
            else:
                st.error("Baixa compatibilidade operacional.")

            st.subheader("Detalhamento")

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
