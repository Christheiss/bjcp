import streamlit as st
import pandas as pd
from pathlib import Path

# ============================================================
# BEERSENSE
# Teste de conexão com a base BJCP
# ============================================================

st.set_page_config(
    page_title="BeerSense",
    page_icon="🍺",
    layout="centered"
)

# ============================================================
# CONFIGURAÇÃO
# ============================================================

ARQUIVO_BJCP = Path("data/bjcp_database.xlsx")


# ============================================================
# CABEÇALHO
# ============================================================

st.title("🍺 BeerSense")
st.subheader("Avaliação Sensorial BJCP")

st.write(
    "Teste de conexão entre o aplicativo e a base de dados BJCP."
)

st.divider()


# ============================================================
# VERIFICAR ARQUIVO
# ============================================================

if not ARQUIVO_BJCP.exists():

    st.error(
        "❌ O arquivo da base BJCP não foi encontrado."
    )

    st.write("Caminho procurado:")

    st.code(str(ARQUIVO_BJCP))

    st.stop()


# ============================================================
# CARREGAR EXCEL
# ============================================================

try:

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

except Exception as erro:

    st.error("❌ Erro ao carregar a base BJCP.")

    st.exception(erro)

    st.stop()


# ============================================================
# BASE CARREGADA
# ============================================================

st.success("✅ Base BJCP carregada com sucesso!")

st.divider()

st.header("📊 Base de dados")


# ============================================================
# MÉTRICAS
# ============================================================

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


# ============================================================
# STATUS DAS ABAS
# ============================================================

st.subheader("Abas carregadas")

st.write("✅ Estilos")
st.write("✅ Categorias_Parametros")
st.write("✅ Valores_Referencia_BJCP")


# ============================================================
# PREVIEW DOS ESTILOS
# ============================================================

st.divider()

st.subheader("🍺 Estilos BJCP")

st.dataframe(
    estilos.head(10),
    use_container_width=True,
    hide_index=True
)


# ============================================================
# PREVIEW DOS PARÂMETROS
# ============================================================

st.divider()

st.subheader("🧪 Parâmetros")

st.dataframe(
    parametros.head(10),
    use_container_width=True,
    hide_index=True
)


# ============================================================
# PREVIEW DAS REFERÊNCIAS
# ============================================================

st.divider()

st.subheader("📚 Referências BJCP")

st.dataframe(
    referencias.head(10),
    use_container_width=True,
    hide_index=True
)


# ============================================================
# INFORMAÇÕES TÉCNICAS
# ============================================================

st.divider()

with st.expander("🔧 Informações técnicas"):

    st.write("Arquivo utilizado:")

    st.code(str(ARQUIVO_BJCP))

    st.write("Dimensões das tabelas:")

    st.write(
        f"Estilos: {estilos.shape[0]} linhas × "
        f"{estilos.shape[1]} colunas"
    )

    st.write(
        f"Parâmetros: {parametros.shape[0]} linhas × "
        f"{parametros.shape[1]} colunas"
    )

    st.write(
        f"Referências: {referencias.shape[0]} linhas × "
        f"{referencias.shape[1]} colunas"
    )
