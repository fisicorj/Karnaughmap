Mapa de Karnaugh Interativo com Streamlit

Aplicação interativa desenvolvida em Python + Streamlit para demonstrar, de forma visual e animada, a simplificação de funções booleanas utilizando o Mapa de Karnaugh.

Este projeto foi criado com foco educacional, permitindo que estudantes compreendam não apenas o como, mas principalmente o porquê matemático por trás dos agrupamentos.

Objetivo

Demonstrar de forma visual:

Como os mintermos são organizados no mapa
Como os agrupamentos eliminam variáveis
A relação entre:

Representação visual (mapa)
Álgebra Booleana
Simplificação de circuitos digitais


Funcionalidades

Exibição do mapa de Karnaugh (3 variáveis)
Animação passo a passo dos agrupamentos
Destaque visual dos grupos
Demonstração da simplificação algébrica
Explicação conceitual integrada
Controle de velocidade da animação
Exemplos prontos para exploração

Tecnologias utilizadas

Python 3.10+
Streamlit
Pandas

Exemplo trabalhado

A aplicação demonstra o caso:

[
F(A,B,C) = \Sigma m(2,3,6,7)
]

Que resulta em:

[
F = B
]

Interpretação

Durante a animação, é possível observar que:

A e C variam dentro do grupo → são eliminadas
B permanece constante → é mantida