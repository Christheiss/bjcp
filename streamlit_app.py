import streamlit as st

st.set_page_config(
    page_title="BeerSense",
    page_icon="🍺",
    layout="centered"
)

st.title("🍺 BeerSense")
st.subheader("Avaliação Sensorial BJCP")

st.write("Protótipo inicial")

st.divider()

st.header("AROMA")

st.subheader("Lúpulo")
lupulo = st.slider("Intensidade", 0, 10, 0)

st.subheader("Malte")
malte = st.slider("Intensidade", 0, 10, 0)

st.subheader("Fermentação")
fermentacao = st.slider("Intensidade", 0, 10, 0)

st.divider()

st.write("Lúpulo:", lupulo)
st.write("Malte:", malte)
st.write("Fermentação:", fermentacao)
