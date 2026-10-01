import streamlit as st

# ============================================================
# BEERSENSE — AVALIAÇÃO SENSORIAL BJCP
# Tela: AROMA
# ============================================================

st.set_page_config(
    page_title="BeerSense — Aroma",
    page_icon="🍺",
    layout="centered",
    initial_sidebar_state="collapsed"
)

# ============================================================
# ESTILO VISUAL
# ============================================================

st.markdown("""
<style>

    /* Área principal */
    .block-container {
        max-width: 760px;
        padding-top: 2rem;
        padding-bottom: 4rem;
    }

    /* Título */
    .beer-title {
        font-size: 2.4rem;
        font-weight: 800;
        margin-bottom: 0;
    }

    .beer-subtitle {
        color: #888;
        font-size: 1rem;
        margin-top: -5px;
        margin-bottom: 25px;
    }

    /* Títulos de seção */
    .section-title {
        font-size: 1.7rem;
        font-weight: 750;
        margin-top: 15px;
        margin-bottom: 5px;
    }

    .section-description {
        color: #888;
        font-size: 0.9rem;
        margin-bottom: 15px;
    }

    /* Cards */
    .group-card {
        padding: 15px 18px;
        border-radius: 12px;
        border: 1px solid rgba(128,128,128,0.25);
        margin-bottom: 12px;
    }

    /* Botão principal */
    div.stButton > button {
        width: 100%;
        border-radius: 10px;
        height: 3rem;
        font-weight: 700;
        font-size: 1rem;
    }

    /* Slider */
    div[data-baseweb="slider"] {
        padding-bottom: 5px;
    }

    /* Remove excesso de espaço */
    .stMarkdown {
        margin-bottom: 0;
    }

</style>
""", unsafe_allow_html=True)


# ============================================================
# FUNÇÕES
# ============================================================

def intensidade_slider(label, key, valor=0):
    """
    Slider padrão de intensidade BJCP.
    Escala operacional de 0 a 10.
    """

    valor = st.slider(
        label,
        min_value=0,
        max_value=10,
        value=valor,
        step=1,
        key=key
    )

    return valor


def mostrar_nuances(titulo, nuances, prefixo):
    """
    Cria uma seção expansível com nuances.
    Cada nuance possui checkbox + intensidade 0-10.
    """

    with st.expander(f"＋ Mostrar nuances de {titulo}"):

        resultados = {}

        for i, nuance in enumerate(nuances):

            ativo = st.checkbox(
                nuance,
                key=f"{prefixo}_ativo_{i}"
            )

            if ativo:

                intensidade = st.slider(
                    f"Intensidade — {nuance}",
                    min_value=0,
                    max_value=10,
                    value=5,
                    step=1,
                    key=f"{prefixo}_intensidade_{i}"
                )

                resultados[nuance] = intensidade

        return resultados


# ============================================================
# CABEÇALHO
# ============================================================

st.markdown(
    '<div class="beer-title">🍺 BeerSense</div>',
    unsafe_allow_html=True
)

st.markdown(
    '<div class="beer-subtitle">Avaliação Sensorial baseada no BJCP</div>',
    unsafe_allow_html=True
)

st.divider()

# ============================================================
# ETAPA
# ============================================================

st.progress(0.25)

st.markdown(
    '<div class="section-title">AROMA</div>',
    unsafe_allow_html=True
)

st.markdown(
    '<div class="section-description">'
    'Avalie primeiro a intensidade geral de cada grupo. '
    'Depois, se desejar, identifique as nuances específicas.'
    '</div>',
    unsafe_allow_html=True
)


# ============================================================
# LÚPULO
# ============================================================

st.markdown("### 🌿 Lúpulo")

lupulo = intensidade_slider(
    "Intensidade geral do lúpulo",
    "aroma_lupulo",
    0
)

nuances_lupulo = mostrar_nuances(
    "Lúpulo",
    [
        "Cítrico",
        "Floral",
        "Herbal",
        "Especiado",
        "Resinoso",
        "Pinho",
        "Tropical",
        "Frutas de caroço",
        "Frutas vermelhas",
        "Frutas tropicais",
        "Melão",
        "Lúpulo nobre",
        "Outros"
    ],
    "lupulo"
)


# ============================================================
# MALTE
# ============================================================

st.markdown("### 🌾 Malte")

malte = intensidade_slider(
    "Intensidade geral do malte",
    "aroma_malte",
    0
)

nuances_malte = mostrar_nuances(
    "Malte",
    [
        "Pão",
        "Biscoito",
        "Bolacha",
        "Cereal",
        "Maltado",
        "Caramelo",
        "Toffee",
        "Mel",
        "Chocolate",
        "Café",
        "Torrado",
        "Queimado",
        "Nozes",
        "Frutas secas",
        "Outros"
    ],
    "malte"
)


# ============================================================
# FERMENTAÇÃO
# ============================================================

st.markdown("### 🍌 Fermentação")

fermentacao = intensidade_slider(
    "Intensidade geral da fermentação",
    "aroma_fermentacao",
    0
)

nuances_fermentacao = mostrar_nuances(
    "Fermentação",
    [
        "Frutado",
        "Ésteres",
        "Banana",
        "Maçã",
        "Pera",
        "Frutas vermelhas",
        "Frutas tropicais",
        "Cravo",
        "Fenólico",
        "Álcool",
        "Enxofre",
        "Solvente",
        "Outros"
    ],
    "fermentacao"
)


# ============================================================
# OUTROS CARACTERES
# ============================================================

st.markdown("### 🧪 Outros caracteres")

outros = mostrar_nuances(
    "Outros caracteres",
    [
        "Álcool",
        "Madeira",
        "Defumado",
        "Enxofre",
        "Acidez",
        "Oxidação",
        "Diacetil",
        "DMS",
        "Solvente",
        "Outros"
    ],
    "outros"
)


# ============================================================
# RESUMO
# ============================================================

st.divider()

st.markdown("### 📋 Resumo do aroma")

col1, col2, col3 = st.columns(3)

with col1:
    st.metric("Lúpulo", f"{lupulo}/10")

with col2:
    st.metric("Malte", f"{malte}/10")

with col3:
    st.metric("Fermentação", f"{fermentacao}/10")


# ============================================================
# BOTÃO PRÓXIMO
# ============================================================

st.divider()

if st.button("Próximo →", type="primary"):

    st.session_state["aroma_concluido"] = True

    st.session_state["aroma_lupulo_valor"] = lupulo
    st.session_state["aroma_malte_valor"] = malte
    st.session_state["aroma_fermentacao_valor"] = fermentacao

    st.session_state["aroma_nuances_lupulo"] = nuances_lupulo
    st.session_state["aroma_nuances_malte"] = nuances_malte
    st.session_state["aroma_nuances_fermentacao"] = nuances_fermentacao
    st.session_state["aroma_nuances_outros"] = outros

    st.success(
        "Aroma registrado! A próxima etapa será Aparência."
    )


# ============================================================
# DEBUG — TEMPORÁRIO
# ============================================================

with st.expander("🔧 Dados registrados — teste"):

    st.write({
        "lupulo": lupulo,
        "malte": malte,
        "fermentacao": fermentacao,
        "nuances_lupulo": nuances_lupulo,
        "nuances_malte": nuances_malte,
        "nuances_fermentacao": nuances_fermentacao,
        "outros": outros
    })
