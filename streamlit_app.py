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

tab_aroma, tab_aparencia, tab_sabor, tab_boca, tab_falhas, tab_resultados = st.tabs([
    "🌸 Aroma",
    "👁️ Aparência",
    "👅 Sabor",
    "💧 Sensação na boca",
    "⚠️ Falhas / Off-flavors",
    "📊 Resultados",
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
            summary.append(f"⚠️ {warning_count} desvio(s)")
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
                st.warning(text + f"⚠️ {message}")
            elif status == "ERRO":
                st.error(text + f"✗ {message}")
            elif status == "PROIBIDO":
                st.error(text + f"⛔ {message}")
            elif status == "IGNORAR":
                continue
            else:
                st.info(text + message)


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
                c2.metric("Estilo", "1A")
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
