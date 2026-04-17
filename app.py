import time
import streamlit as st
import pandas as pd

st.set_page_config(page_title="Mapa de Karnaugh Animado", layout="wide")

st.title("Mapa de Karnaugh — animação da simplificação")
st.markdown(
    """
Este app mostra como o agrupamento no mapa de Karnaugh elimina variáveis.
No exemplo abaixo, usamos a função:

**F(A,B,C) = Σm(2,3,6,7)**

que simplifica para:

**F = B**
"""
)

st.divider()

# Ordem Gray nas colunas
gray_cols = ["00", "01", "11", "10"]

# Exemplo de 3 variáveis:
# linhas = A (0,1)
# colunas = BC em Gray code
#
# mintermos: 2,3,6,7
# A B C
# 0 1 0 -> m2
# 0 1 1 -> m3
# 1 1 0 -> m6
# 1 1 1 -> m7
#
# colunas:
# 00 -> BC=00
# 01 -> BC=01
# 11 -> BC=11
# 10 -> BC=10

base_values = [
    [0, 0, 1, 1],  # A=0
    [0, 0, 1, 1],  # A=1
]

df = pd.DataFrame(base_values, index=["A=0", "A=1"], columns=gray_cols)

st.subheader("1) Tabela inicial do mapa")
st.dataframe(df, use_container_width=True)

st.markdown(
    """
Os dois pares de `1` à direita formam um grupo de 4 células.

Como esse grupo cobre:
- `A = 0` e `A = 1`  → **A varia**, então **A é eliminada**
- `C = 0` e `C = 1`  → **C varia**, então **C é eliminada**
- `B = 1` em todas as células → **B permanece**
"""
)

st.divider()

st.subheader("2) Animação do agrupamento")

speed = st.slider("Velocidade da animação (segundos por passo)", 0.2, 2.0, 0.8, 0.1)

placeholder = st.empty()
text_placeholder = st.empty()

def render_table(highlight_cells=None):
    if highlight_cells is None:
        highlight_cells = []

    styled = df.style

    def style_cells(data):
        styles = pd.DataFrame("", index=data.index, columns=data.columns)
        for r, c in highlight_cells:
            styles.iloc[r, c] = "background-color: #ffe082; font-weight: bold;"
        return styles

    styled = styled.apply(style_cells, axis=None)
    placeholder.dataframe(styled, use_container_width=True)

# Passo 1
text_placeholder.info("Passo 1: observe os 1's que serão agrupados.")
render_table()
time.sleep(speed)

# Passo 2
text_placeholder.info("Passo 2: destacando a primeira coluna relevante do grupo.")
render_table(highlight_cells=[(0, 2), (1, 2)])
time.sleep(speed)

# Passo 3
text_placeholder.info("Passo 3: expandindo o grupo para 4 células adjacentes.")
render_table(highlight_cells=[(0, 2), (0, 3), (1, 2), (1, 3)])
time.sleep(speed)

# Passo 4
text_placeholder.success(
    "Passo 4: grupo de 4 formado. As variáveis que mudam dentro do grupo são eliminadas."
)
render_table(highlight_cells=[(0, 2), (0, 3), (1, 2), (1, 3)])

st.divider()

st.subheader("3) Interpretação algébrica")

st.latex(r"""
F(A,B,C)=\overline{A}B\overline{C} + \overline{A}BC + AB\overline{C} + ABC
""")

st.markdown("Agrupando e fatorando:")

st.latex(r"""
F = B(\overline{A}\overline{C} + \overline{A}C + A\overline{C} + AC)
""")

st.markdown("Agrupando por blocos:")

st.latex(r"""
F = B[\overline{A}(\overline{C}+C) + A(\overline{C}+C)]
""")

st.latex(r"""
F = B[\overline{A}(1) + A(1)]
""")

st.latex(r"""
F = B(\overline{A}+A)
""")

st.latex(r"""
F = B(1)=B
""")

st.success("Resultado final: F = B")

st.divider()

st.subheader("4) Explicação visual das variáveis")

col1, col2, col3 = st.columns(3)

with col1:
    st.markdown("### Variável A")
    st.write("No grupo, aparecem células com A=0 e A=1.")
    st.write("Logo, A varia e é eliminada.")

with col2:
    st.markdown("### Variável B")
    st.write("No grupo, B=1 em todas as células.")
    st.write("Logo, B permanece na expressão.")

with col3:
    st.markdown("### Variável C")
    st.write("No grupo, aparecem células com C=0 e C=1.")
    st.write("Logo, C varia e é eliminada.")

st.divider()

st.subheader("5) Quer testar outro caso?")

example = st.selectbox(
    "Escolha outro exemplo",
    [
        "F = Σm(2,3,6,7)  -> B",
        "F = Σm(0,1,2,3)  -> A'",
        "F = Σm(1,3,5,7)  -> C",
    ],
)

if example == "F = Σm(2,3,6,7)  -> B":
    st.latex(r"F = B")
elif example == "F = Σm(0,1,2,3)  -> A'":
    st.latex(r"F = \overline{A}")
else:
    st.latex(r"F = C")

st.caption("Você pode expandir este app para aceitar qualquer mapa e animar agrupamentos automaticamente.")