import streamlit as st
import pandas as pd
from pathlib import Path


# ============================================================
# BEERSENSE
# Avaliação Sensorial BJCP
# Versão: Aroma
# ============================================================

st.set_page_config(
    page_title="BeerSense",
    page_icon="🍺",
    layout="centered",
    initial_sidebar_state="collapsed"
)


# ============================================================
# CONFIGURAÇÃO
# ============================================================

ARQUIVO_BJCP = Path("data/bjcp_database.xlsx")


# ============================================================
# TRADUÇÕES PARA A INTERFACE
#
# Os nomes internos continuam iguais aos da nossa base.
# Aqui apenas definimos como eles aparecem para o usuário.
# ============================================================

TRADUCOES = {
    "Intensidade de lúpulo": "Intensidade de lúpulo",
    "Intensidade de malte": "Intensidade de malte",
    "Intensidade de fermentação": "Intensidade de fermentação",

    "malt": "Maltado",
    "bread/biscuit/toast": "Pão / Biscoito / Torrado",
    "fruit": "Frutado",
    "esters": "Ésteres",
    "alcohol": "Álcool",
    "smoke": "Defumado",
    "caramel/toffee": "Caramelo / Toffee",
    "grain/corn": "Cereal / Milho",
    "hop aroma": "Aroma de lúpulo",
    "phenolic/spice": "Fenólico / Especiado",
    "roast/chocolate/coffee": "Torrado / Chocolate / Café",
    "sour/acid": "Ácido / Sour",
    "sulfur/DMS": "Enxofre / DMS",
    "wood/oak": "Madeira / Carvalho",
}


# ============================================================
# ESTILO VISUAL
# ============================================================

st.markdown(
    """
    <style>

    .block-container {
        max-width: 760px;
        padding-top: 2rem;
        padding-bottom: 4rem;
    }

    .beer-title {
        font-size: 2.5rem;
        font-weight: 800;
        margin-bottom: 0;
    }

    .beer-subtitle {
        color: #888;
        font-size: 1rem;
        margin-top: -5px;
        margin-bottom: 20px;
    }

    .section-title {
        font-size: 1.8rem;
        font-weight: 800;
        margin-top: 10px;
    }

    .section-description {
        color: #888;
        margin-bottom: 20px;
    }

    .group-title {
        font-size: 1.25rem;
        font-weight: 750;
        margin-top: 15px;
        margin-bottom: 5px;
    }

    div.stButton > button {
        width: 100%;
        border-radius: 10px;
        min-height: 3rem;
        font-weight: 700;
    }

    </style>
    """,
    unsafe_allow_html=True
)


# ============================================================
# CARREGAR BANCO
# ============================================================

@st.cache_data
def carregar_banco():

    estilos = pd.read_excel(
        ARQUIVO_BJCP,
        sheet_name="Estilos"
    )

    parametros = pd.read_excel(
        ARQUIVO_BJCP,
        sheet_name="Categorias_Parametros"
    )

    referencias = pd.read_excel(
        ARQUIVO_BJCP,
        sheet_name="Valores_Referencia_BJCP"
    )

    return estilos, parametros, referencias


# ============================================================
# VERIFICAÇÃO DO ARQUIVO
# ============================================================

if not ARQUIVO_BJCP.exists():

    st.error(
        "❌ Não encontrei a base BJCP."
    )

    st.code(
        str(ARQUIVO_BJCP)
    )

    st.stop()


# ============================================================
# CARREGAR DADOS
# ============================================================

try:

    estilos, parametros, referencias = carregar_banco()

except Exception as erro:

    st.error(
        "❌ Erro ao carregar a base BJCP."
    )

    st.exception(erro)

    st.stop()


# ============================================================
# SEPARAR PARÂMETROS DE AROMA
# ============================================================

parametros_aroma = parametros[
    parametros["Dimensão"].astype(str).str.lower() == "aroma"
].copy()


parametros_principais = parametros_aroma[
    parametros_aroma["Tipo"].astype(str).str.lower() == "intensidade"
].copy()


parametros_nuances = parametros_aroma[
    parametros_aroma["Tipo"].astype(str).str.lower() == "nuance"
].copy()


# ============================================================
# CABEÇALHO
# ============================================================

st.markdown(
    '<div class="beer-title">🍺 BeerSense</div>',
    unsafe_allow_html=True
)

st.markdown(
    '<div class="beer-subtitle">'
    'Avaliação Sensorial baseada no BJCP'
    '</div>',
    unsafe_allow_html=True
)


# ============================================================
# STATUS DA BASE
# ============================================================

with st.expander("✓ Base BJCP conectada", expanded=False):

    col1, col2, col3 = st.columns(3)

    with col1:
        st.metric(
            "Estilos",
            len(estilos)
        )

    with col2:
        st.metric(
            "Parâmetros",
            len(parametros)
        )

    with col3:
        st.metric(
            "Referências",
            len(referencias)
        )


st.divider()


# ============================================================
# TÍTULO DA ETAPA
# ============================================================

st.progress(0.25)

st.markdown(
    '<div class="section-title">AROMA</div>',
    unsafe_allow_html=True
)

st.markdown(
    '<div class="section-description">'
    'Avalie a intensidade geral primeiro. '
    'Depois, selecione as nuances que você identifica na cerveja.'
    '</div>',
    unsafe_allow_html=True
)


# ============================================================
# ARMAZENAR RESULTADOS
# ============================================================

aroma_resultado = {}


# ============================================================
# PARÂMETROS PRINCIPAIS
# ============================================================

st.markdown(
    '<div class="group-title">🌿 Lúpulo</div>',
    unsafe_allow_html=True
)

p = parametros_principais[
    parametros_principais["Parametro_ID"] == "P001"
]

if not p.empty:

    nome = p.iloc[0]["Parâmetro"]

    valor_lupulo = st.slider(
        "Intensidade geral",
        min_value=0,
        max_value=10,
        value=0,
        step=1,
        key="aroma_lupulo"
    )

    aroma_resultado["P001"] = {
        "parametro": nome,
        "valor": valor_lupulo
    }


st.markdown(
    '<div class="group-title">🌾 Malte</div>',
    unsafe_allow_html=True
)

p = parametros_principais[
    parametros_principais["Parametro_ID"] == "P002"
]

if not p.empty:

    nome = p.iloc[0]["Parâmetro"]

    valor_malte = st.slider(
        "Intensidade geral",
        min_value=0,
        max_value=10,
        value=0,
        step=1,
        key="aroma_malte"
    )

    aroma_resultado["P002"] = {
        "parametro": nome,
        "valor": valor_malte
    }


st.markdown(
    '<div class="group-title">🍌 Fermentação</div>',
    unsafe_allow_html=True
)

p = parametros_principais[
    parametros_principais["Parametro_ID"] == "P003"
]

if not p.empty:

    nome = p.iloc[0]["Parâmetro"]

    valor_fermentacao = st.slider(
        "Intensidade geral",
        min_value=0,
        max_value=10,
        value=0,
        step=1,
        key="aroma_fermentacao"
    )

    aroma_resultado["P003"] = {
        "parametro": nome,
        "valor": valor_fermentacao
    }


# ============================================================
# NUANCES
# ============================================================

st.divider()

st.subheader("🔎 Nuances")


# Agrupar as nuances pelos grupos existentes no banco
grupos = parametros_nuances["Grupo"].dropna().unique()


for grupo in grupos:

    dados_grupo = parametros_nuances[
        parametros_nuances["Grupo"] == grupo
    ]

    nome_grupo = str(grupo)

    if nome_grupo == "Lúpulo":
        icone = "🌿"
    elif nome_grupo == "Malte":
        icone = "🌾"
    elif nome_grupo == "Fermentação":
        icone = "🍌"
    elif nome_grupo == "Outros":
        icone = "🧪"
    else:
        icone = "🔎"

    with st.expander(
        f"{icone} {nome_grupo}"
    ):

        for _, parametro in dados_grupo.iterrows():

            parametro_id = str(
                parametro["Parametro_ID"]
            )

            nome_original = str(
                parametro["Parâmetro"]
            )

            nome_exibicao = TRADUCOES.get(
                nome_original,
                nome_original
            )

            ativo = st.checkbox(
                nome_exibicao,
                key=f"ativo_{parametro_id}"
            )

            if ativo:

                intensidade = st.slider(
                    f"Intensidade — {nome_exibicao}",
                    min_value=0,
                    max_value=10,
                    value=5,
                    step=1,
                    key=f"intensidade_{parametro_id}"
                )

                aroma_resultado[parametro_id] = {
                    "parametro": nome_original,
                    "nome_exibicao": nome_exibicao,
                    "valor": intensidade,
                    "grupo": nome_grupo
                }


# ============================================================
# RESUMO
# ============================================================

st.divider()

st.subheader("📋 Resumo do Aroma")


col1, col2, col3 = st.columns(3)

with col1:
    st.metric(
        "Lúpulo",
        f"{aroma_resultado.get('P001', {}).get('valor', 0)}/10"
    )

with col2:
    st.metric(
        "Malte",
        f"{aroma_resultado.get('P002', {}).get('valor', 0)}/10"
    )

with col3:
    st.metric(
        "Fermentação",
        f"{aroma_resultado.get('P003', {}).get('valor', 0)}/10"
    )


nuances_selecionadas = [
    item
    for item in aroma_resultado.keys()
    if item not in ["P001", "P002", "P003"]
]


st.write(
    f"**Nuances identificadas:** "
    f"{len(nuances_selecionadas)}"
)


# ============================================================
# SALVAR AVALIAÇÃO NA SESSÃO
# ============================================================

st.divider()

if st.button(
    "Salvar Aroma e continuar →",
    type="primary"
):

    st.session_state["aroma"] = aroma_resultado

    st.session_state["aroma_concluido"] = True

    st.success(
        "✅ Aroma registrado com sucesso!"
    )

    st.write(
        "Parâmetros registrados:",
        len(aroma_resultado)
    )


# ============================================================
# VISUALIZAR DADOS — TEMPORÁRIO
# ============================================================

with st.expander("🔧 Ver dados registrados"):

    st.json(aroma_resultado)
