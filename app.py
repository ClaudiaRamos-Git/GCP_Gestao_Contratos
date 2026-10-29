"""GCP_Gestao_Contratos — painel Streamlit (Projeto Final SENAI/SC · LAB365).

Lê apenas arquivos publicáveis gerados por `src/transform.py` e `src/analysis.py`:
  - data/processed/red_flags_convenio.parquet
  - data/processed/contratos_red_flags.parquet
  - data/processed/agg_contrato_objeto.parquet
  - outputs/*.csv (separador ';', decimal ',')

Execução (na raiz do projeto):  streamlit run app.py
Visual com tema escuro, painel lateral, lista e etiquetas coloridas.
"""
import os

import numpy as np
import pandas as pd
import plotly.express as px
import streamlit as st

PROC = "data/processed/"
OUT = "outputs/"
DATA_FONTE = "17/07/2026"
ANO_MIN, ANO_MAX = 2008, 2026

# ---------------------------------------------------------------------------
# Paleta
# ---------------------------------------------------------------------------
BG, PANEL, CARD, BORDA = "#1E1F21", "#252628", "#2A2B2D", "#3A3B3D"
TEXTO, MUDO = "#F1F1F1", "#A2A0A2"
CORAL, AZUL, LARANJA = "#F06A6A", "#4573D2", "#F1A875"
PASTEL_AZUL, PASTEL_VERDE, PASTEL_ROXO, PASTEL_AMARELO, PASTEL_CORAL = (
    "#9CC9F2", "#8FDDB8", "#D7B2F0", "#F8E08E", "#F7A3A3")

FLAGS = {
    "RF_VALOR_ZERO": "Contrato com valor zero",
    "RF_FORA_VIGENCIA": "Assinatura fora da vigência",
    "RF_CONTRATADO_ACIMA_GLOBAL": "Contratado acima do global",
    "RF_PAGO_ACIMA_DESEMBOLSO": "Pago acima do desembolsado",
    "RF_PRESTACAO_VENCIDA": "Prestação de contas vencida",
    "RF_MUITOS_ADITIVOS": "Muitos aditivos/prorrogações",
}
FLAGS_CONTRATO = {
    "RF01": ("RF_VALOR_ZERO", "Valor global zerado"),
    "RF02": ("RF_ID_REPETIDO", "ID de contrato repetido"),
    "RF03": ("RF_VIGENCIA_INVERTIDA", "Fim de vigência anterior ao início"),
    "RF04": ("RF_FORA_VIGENCIA", "Assinatura fora da vigência do convênio"),
    "RF05": ("RF_SEM_LICITACAO", "Dispensa ou inexigibilidade"),
}

PAGINAS = ["🏠 Visão geral", "🚩 Red flags", "📁 Convênios", "📄 Contratos", "ℹ️ Metodologia"]

st.set_page_config(page_title="GCP · Gestão de Contratos", page_icon="📊",
                   layout="wide", initial_sidebar_state="expanded")

# Declara o idioma da página como português e pede ao navegador para não traduzir.
# Sem isso, o Chrome vê lang="en" no HTML padrão do Streamlit, oferece tradução automática
# e embaralha os textos (ex.: "Convênios" vira "Convetos") e o React quebra com
# "NotFoundError: removeChild".
_JS_IDIOMA = """<script>
const d = window.parent.document;
d.documentElement.setAttribute('lang', 'pt-BR');
d.documentElement.setAttribute('translate', 'no');
if (!d.querySelector('meta[name="google"]')) {
  const m = d.createElement('meta'); m.name = 'google'; m.content = 'notranslate'; d.head.appendChild(m);
}
</script>"""
try:
    st.iframe(_JS_IDIOMA, height=1)  # Streamlit recente
except Exception:
    try:
        import streamlit.components.v1 as components
        components.html(_JS_IDIOMA, height=0)  # Streamlit mais antigo
    except Exception:
        pass

CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap');
html, body, [class*="css"], .stApp { font-family: 'Inter', sans-serif; }
.stApp { background: __BG__; color: __TEXTO__; }
[data-testid="stHeader"] { background: transparent; }
.block-container { padding-top: 1.6rem; max-width: 1320px; }
[data-testid="stSidebar"] { background: __PANEL__; border-right: 1px solid __BORDA__; }
[data-testid="stSidebar"] .block-container { padding-top: 1rem; }
h1, h2, h3 { color: __TEXTO__; font-weight: 600; letter-spacing: -0.01em; }
hr { border-color: __BORDA__; }
[data-testid="stSidebar"] div[role="radiogroup"] { gap: 2px; }
[data-testid="stSidebar"] div[role="radiogroup"] > label { padding: 8px 12px; border-radius: 8px; width: 100%; cursor: pointer; }
[data-testid="stSidebar"] div[role="radiogroup"] > label:hover { background: #333436; }
[data-testid="stSidebar"] div[role="radiogroup"] > label > div:first-child { display: none; }
[data-testid="stSidebar"] div[role="radiogroup"] > label:has(input:checked) { background: __BORDA__; }
[data-testid="stSidebar"] div[role="radiogroup"] p { font-size: 0.95rem; }
.marca { display: flex; align-items: center; gap: 10px; margin-bottom: 14px; }
.marca .logo { width: 34px; height: 34px; border-radius: 8px; background: __LARANJA__; display: flex;
  align-items: center; justify-content: center; font-weight: 700; color: #1E1F21; font-size: 0.8rem; }
.marca .nome { font-weight: 600; font-size: 1rem; line-height: 1.1; }
.marca .sub { color: __MUDO__; font-size: 0.72rem; }
.secao-lateral { color: __MUDO__; font-size: 0.72rem; text-transform: uppercase; letter-spacing: .06em; margin: 14px 0 4px 4px; }
.nota-lateral { background: __CARD__; border: 1px solid __BORDA__; border-radius: 10px; padding: 10px 12px;
  font-size: 0.78rem; color: __MUDO__; margin-top: 10px; }
.cab { display: flex; align-items: center; gap: 12px; margin-bottom: 4px; }
.cab .icone { width: 36px; height: 36px; border-radius: 8px; background: __LARANJA__; display: flex;
  align-items: center; justify-content: center; font-size: 1.1rem; }
.cab .titulo { font-size: 1.7rem; font-weight: 600; }
.subtitulo { color: __MUDO__; font-size: 0.9rem; margin-bottom: 18px; }
.kpi { background: __CARD__; border: 1px solid __BORDA__; border-radius: 12px; padding: 14px 16px; height: 100%; }
.kpi .rot { color: __MUDO__; font-size: 0.78rem; }
.kpi .val { font-size: 1.55rem; font-weight: 600; margin-top: 2px; }
.kpi .obs { color: __MUDO__; font-size: 0.72rem; margin-top: 2px; }
.painel { background: __CARD__; border: 1px solid __BORDA__; border-radius: 12px; padding: 16px; }
.painel h4 { margin: 0 0 8px 0; font-size: 1rem; font-weight: 600; }
.painel .linha { display: flex; justify-content: space-between; padding: 6px 0; border-bottom: 1px solid __BORDA__; font-size: 0.85rem; }
.painel .linha span:first-child { color: __MUDO__; }
.pill { display: inline-block; padding: 1px 9px; border-radius: 5px; font-size: 0.78rem; font-weight: 500;
  color: #1E1F21; margin: 0 4px 4px 0; white-space: nowrap; }
table.lista { width: 100%; border-collapse: collapse; font-size: 0.86rem; }
table.lista th { text-align: left; color: __MUDO__; font-weight: 500; padding: 8px 10px; border-bottom: 1px solid __BORDA__; border-top: 1px solid __BORDA__; }
table.lista td { padding: 9px 10px; border-bottom: 1px solid __BORDA__; vertical-align: top; }
table.lista tr:hover td { background: #262729; }
.alerta { background: #2D2A22; border: 1px solid #5B4F2A; border-radius: 10px; padding: 10px 14px; font-size: 0.85rem; color: #E8D9A0; }
.filtros { color: __MUDO__; font-size: 0.8rem; margin: 2px 0 10px 0; }
.filtros b { color: __TEXTO__; font-weight: 500; }
button[data-baseweb="tab"] { font-weight: 500; }
</style>
"""
for chave, valor in {"__BG__": BG, "__PANEL__": PANEL, "__CARD__": CARD, "__BORDA__": BORDA,
                     "__TEXTO__": TEXTO, "__MUDO__": MUDO, "__LARANJA__": LARANJA}.items():
    CSS = CSS.replace(chave, valor)
st.markdown(CSS, unsafe_allow_html=True)


# ---------------------------------------------------------------------------
# Auxiliares
# ---------------------------------------------------------------------------
def pt(texto):
    return texto.replace(",", "X").replace(".", ",").replace("X", ".")


def num(n):
    return pt(f"{n:,.0f}")


def brl(v):
    return pt(f"R$ {v:,.2f}")


def abrevia(v):
    if v >= 1e9:
        return pt(f"R$ {v / 1e9:,.1f} bi")
    if v >= 1e6:
        return pt(f"R$ {v / 1e6:,.1f} mi")
    return brl(v)


def pill(texto, cor):
    return f'<span class="pill" style="background:{cor}">{texto}</span>'


def kpi(rotulo, valor, obs=""):
    return (f'<div class="kpi"><div class="rot">{rotulo}</div><div class="val">{valor}</div>'
            f'<div class="obs">{obs}</div></div>')


def cabecalho(icone, titulo, subtitulo):
    st.markdown(f'<div class="cab"><div class="icone">{icone}</div><div class="titulo">{titulo}</div></div>'
                f'<div class="subtitulo">{subtitulo}</div>', unsafe_allow_html=True)


def tabela_html(cabecalho_cols, linhas):
    th = "".join(f"<th>{c}</th>" for c in cabecalho_cols)
    corpo = "".join("<tr>" + "".join(f"<td>{c}</td>" for c in linha) + "</tr>" for linha in linhas)
    st.markdown(f'<table class="lista"><thead><tr>{th}</tr></thead><tbody>{corpo}</tbody></table>',
                unsafe_allow_html=True)


def fonte(extra=""):
    st.caption(f"Fonte: SICONV/Transferegov, arquivos publicados em {DATA_FONTE}. Elaboração própria. {extra}".strip())


def filtros_ativos(partes, resumo):
    """Mostra os filtros em uso e o recorte exibido."""
    ativos = " · ".join(f"<b>{p}</b>" for p in partes) if partes else "nenhum (todos os dados)"
    st.markdown(f'<div class="filtros">Filtros ativos: {ativos} &nbsp;|&nbsp; {resumo}</div>', unsafe_allow_html=True)


def grafico(fig, altura=340, x=None, y=None):
    fig.update_layout(height=altura, paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
                      font=dict(family="Inter, sans-serif", color=TEXTO),
                      margin=dict(l=0, r=0, t=30, b=0),
                      legend=dict(orientation="h", y=1.12, x=0, title=None))
    fig.update_xaxes(gridcolor=BORDA, zeroline=False, title_text=x)
    fig.update_yaxes(gridcolor=BORDA, zeroline=False, title_text=y)
    try:
        st.plotly_chart(fig, width="stretch")
    except TypeError:
        st.plotly_chart(fig, use_container_width=True)


def mostrar_df(df, altura=430):
    try:
        st.dataframe(df, hide_index=True, width="stretch", height=altura)
    except TypeError:
        st.dataframe(df, hide_index=True, use_container_width=True, height=altura)


def csv_bytes(df):
    return df.to_csv(index=False, sep=";", decimal=",").encode("utf-8-sig")


def download_sob_demanda(chave, assinatura, df, nome_arquivo):
    """Gera o CSV só quando a pessoa pede (evita processar centenas de milhares de linhas a cada clique)."""
    if st.button(f"Preparar CSV ({num(len(df))} linhas)", key=f"prep_{chave}"):
        st.session_state[f"csv_{chave}"] = (assinatura, csv_bytes(df))
    pronto = st.session_state.get(f"csv_{chave}")
    if pronto and pronto[0] == assinatura:
        st.download_button("⬇️ Baixar CSV", data=pronto[1], file_name=nome_arquivo, mime="text/csv",
                           key=f"dl_{chave}")
    elif pronto:
        st.caption("Os filtros mudaram: prepare o CSV novamente.")


@st.cache_data(show_spinner=False)
def ler_csv(nome):
    caminho = OUT + nome
    if not os.path.exists(caminho):
        return None
    return pd.read_csv(caminho, sep=";", decimal=",", encoding="utf-8-sig")


@st.cache_data(show_spinner=False)
def ler_parquet(nome):
    caminho = PROC + nome
    if not os.path.exists(caminho):
        return None
    return pd.read_parquet(caminho)


@st.cache_data(show_spinner=False)
def ler_flags():
    df = ler_parquet("red_flags_convenio.parquet")
    if df is not None:
        df["NR_CONVENIO"] = df["NR_CONVENIO"].astype(str)
    return df


def exigir(*dfs):
    if any(d is None for d in dfs):
        st.error("Arquivos de saída não encontrados. Rode `python -m src.transform` e "
                 "`python src/analysis.py` na raiz do projeto e recarregue a página.")
        st.stop()


def marcar_parcial(df, col_ano="ANO"):
    df = df.copy()
    df["SITUACAO"] = np.where(df[col_ano] == ANO_MAX, "Ano parcial (até 17/07)", "Ano completo")
    return df


CORES_ANO = {"Ano completo": AZUL, "Ano parcial (até 17/07)": LARANJA}

# ---------------------------------------------------------------------------
# Painel lateral esquerdo: navegação e filtros
# ---------------------------------------------------------------------------
flags_df = ler_flags()
agg_df = ler_parquet("agg_contrato_objeto.parquet")
F = {}

with st.sidebar:
    st.markdown('<div class="marca"><div class="logo">GCP</div><div><div class="nome">Gestão de Contratos</div>'
                '<div class="sub">Convênios públicos · SICONV</div></div></div>', unsafe_allow_html=True)
    st.markdown('<div class="secao-lateral">Navegação</div>', unsafe_allow_html=True)
    pagina = st.radio("Navegação", PAGINAS, label_visibility="collapsed")

    if pagina == PAGINAS[0]:
        st.markdown('<div class="secao-lateral">Filtros</div>', unsafe_allow_html=True)
        F["periodo"] = st.slider("Período (ano de assinatura/pagamento)", ANO_MIN, ANO_MAX,
                                 (ANO_MIN, ANO_MAX), key="per_vg")
    elif pagina == PAGINAS[2] and flags_df is not None:
        st.markdown('<div class="secao-lateral">Filtros</div>', unsafe_allow_html=True)
        if "ANO_ASSINATURA" in flags_df.columns and flags_df["ANO_ASSINATURA"].notna().any():
            lo = max(ANO_MIN, int(flags_df["ANO_ASSINATURA"].min()))
            hi = min(ANO_MAX, int(flags_df["ANO_ASSINATURA"].max()))
            F["periodo"] = st.slider("Período (ano de assinatura do convênio)", lo, hi, (lo, hi), key="per_cv")
        sit = sorted(flags_df["SIT_CONVENIO"].dropna().unique())
        F["situacao"] = st.multiselect("Situação do convênio", sit, placeholder="Todas", key="sit_cv")
        F["min_alertas"] = st.slider("Mínimo de alertas", 0, int(flags_df["QTD_ALERTAS"].max()), 0, key="min_cv")
        F["flags"] = st.multiselect("Exigir alertas", list(FLAGS), format_func=FLAGS.get,
                                    placeholder="Qualquer", key="flags_cv")
    elif pagina == PAGINAS[3] and agg_df is not None:
        st.markdown('<div class="secao-lateral">Filtros</div>', unsafe_allow_html=True)
        F["periodo"] = st.slider("Período (ano de assinatura do contrato)", ANO_MIN, ANO_MAX,
                                 (ANO_MIN, ANO_MAX), key="per_ct")
        aq = sorted(agg_df["TIPO_AQUISICAO_CONTRATO"].fillna("Não informado").unique())
        F["aquisicao"] = st.multiselect("Tipo de aquisição", aq, placeholder="Todos", key="aq_ct")
        md = sorted(agg_df["MODALIDADE_LICITACAO"].fillna("Não informado").unique())
        F["modalidade"] = st.multiselect("Modalidade de licitação", md, placeholder="Todas", key="md_ct")
        tf = sorted(agg_df["TIPO_FORNECEDOR"].fillna("Não informado").unique())
        F["fornecedor"] = st.multiselect("Tipo de fornecedor", tf, placeholder="Todos", key="tf_ct")

    st.markdown(f'<div class="nota-lateral"><b>Fonte:</b> SICONV / Transferegov, arquivos publicados em '
                f'{DATA_FONTE}.<br><br>Alertas são pontos a conferir, <b>não prova de irregularidade</b>.</div>',
                unsafe_allow_html=True)


# ---------------------------------------------------------------------------
# Páginas
# ---------------------------------------------------------------------------
def pagina_visao_geral():
    cabecalho("🏠", "Visão geral", "Contratos, convênios e pagamentos do SICONV (datas plausíveis: 2008 a 17/07/2026)")
    contratos = ler_csv("contratos_por_ano.csv")
    pagamentos = ler_csv("pagamentos_por_ano.csv")
    resumo = ler_csv("red_flags_resumo.csv")
    exigir(contratos, pagamentos, resumo, flags_df)

    st.markdown('<div class="painel"><b>Pergunta do projeto:</b> é possível automatizar o cruzamento de contratos, '
                'licitações, convênios e pagamentos e gerar alertas que ajudem a priorizar conferências? '
                '<b>Para quem:</b> quem recebe recurso público, licita e presta contas (e quem audita). '
                f'<b>Fonte:</b> dados abertos do SICONV/Transferegov, arquivos de {DATA_FONTE}. '
                '<b>Como navegar:</b> use o painel à esquerda; cada página tem seus filtros.</div>',
                unsafe_allow_html=True)
    st.write("")

    lo, hi = F["periodo"]
    contratos = contratos[contratos["ANO"].between(lo, hi)]
    pagamentos = pagamentos[pagamentos["ANO"].between(lo, hi)]
    partes = [f"período {lo}–{hi}"] if (lo, hi) != (ANO_MIN, ANO_MAX) else []
    filtros_ativos(partes, f"{num(contratos['CONTRATOS'].sum())} contratos e "
                           f"{num(pagamentos['PAGAMENTOS'].sum())} pagamentos no período")
    if contratos.empty:
        st.info("Nenhum dado no período selecionado.")
        return

    n_formalizados = int(resumo.loc[resumo["codigo"] == "RF06", "base"].iloc[0])
    com_alerta = int((flags_df["QTD_ALERTAS"] > 0).sum())
    c1, c2, c3, c4 = st.columns(4)
    c1.markdown(kpi("Contratos assinados", num(contratos["CONTRATOS"].sum()), "no período (datas válidas)"),
                unsafe_allow_html=True)
    c2.markdown(kpi("Valor contratado", abrevia(contratos["VALOR_TOTAL"].sum()), "soma do valor global"),
                unsafe_allow_html=True)
    c3.markdown(kpi("Valor pago", abrevia(pagamentos["VALOR_PAGO"].sum()), "pagamentos no período"),
                unsafe_allow_html=True)
    c4.markdown(kpi("Convênios com alerta", pt(f"{100 * com_alerta / n_formalizados:.1f}%"),
                    f"{num(com_alerta)} de {num(n_formalizados)} formalizados (todo o período)"),
                unsafe_allow_html=True)
    st.write("")

    contratos = marcar_parcial(contratos)
    e, d = st.columns(2)
    with e:
        st.markdown("**Contratos assinados por ano**")
        grafico(px.bar(contratos, x="ANO", y="CONTRATOS", color="SITUACAO", color_discrete_map=CORES_ANO),
                x="Ano de assinatura", y="Quantidade de contratos")
        fonte()
    with d:
        st.markdown("**Valor contratado por ano**")
        contratos["VALOR_BI"] = contratos["VALOR_TOTAL"] / 1e9
        grafico(px.bar(contratos, x="ANO", y="VALOR_BI", color="SITUACAO", color_discrete_map=CORES_ANO),
                x="Ano de assinatura", y="Valor global (R$ bilhões)")
        fonte()

    st.markdown("**Valor pago por ano**")
    pagamentos = pagamentos.copy()
    pagamentos["VALOR_BI"] = pagamentos["VALOR_PAGO"] / 1e9
    pagamentos["SITUACAO"] = np.where(pagamentos["ANO"] == ANO_MAX, "Ano parcial (até 17/07)", "Ano completo")
    grafico(px.bar(pagamentos, x="ANO", y="VALOR_BI", color="SITUACAO", color_discrete_map=CORES_ANO), 300,
            x="Ano do pagamento", y="Valor pago (R$ bilhões)")
    fonte()
    st.markdown('<div class="alerta">2026 é um ano parcial (dados até 17/07/2026): não compare com anos completos. '
                'Contratos e pagamentos com datas impossíveis (ex.: ano 0002 ou 2031) ficaram fora destes gráficos.</div>',
                unsafe_allow_html=True)


def pagina_red_flags():
    cabecalho("🚩", "Red flags", "Regras de alerta aplicadas aos contratos e convênios formalizados")
    resumo = ler_csv("red_flags_resumo.csv")
    exigir(resumo, flags_df)

    linhas = []
    for _, r in resumo.iterrows():
        cor = PASTEL_AZUL if r["codigo"] <= "RF05" else PASTEL_ROXO
        nivel = "contrato" if r["codigo"] <= "RF05" else "convênio"
        linhas.append([pill(r["codigo"], cor), r["descricao"], r["limiar"], pill(nivel, PASTEL_AMARELO),
                       num(r["base"]), num(r["ocorrencias"]), pt(f"{r['pct']:.2f}%")])
    tabela_html(["Código", "Alerta", "Regra", "Nível", "Base", "Ocorrências", "%"], linhas)
    fonte("Cada alerta indica um ponto a conferir.")
    st.write("")

    e, d = st.columns(2)
    with e:
        st.markdown("**% de ocorrências por regra**")
        grafico(px.bar(resumo.sort_values("pct"), x="pct", y="codigo", orientation="h",
                       color_discrete_sequence=[CORAL]), x="% da base de cada regra", y="Regra")
        fonte()
    with d:
        st.markdown("**Convênios formalizados por número de alertas**")
        dist = flags_df["QTD_ALERTAS"].value_counts().sort_index().reset_index()
        dist.columns = ["ALERTAS", "CONVENIOS"]
        dist["ALERTAS"] = dist["ALERTAS"].astype(str)
        grafico(px.bar(dist, x="ALERTAS", y="CONVENIOS", color_discrete_sequence=[AZUL]),
                x="Número de alertas no convênio", y="Quantidade de convênios")
        fonte()
    st.markdown('<div class="alerta">Alerta é um ponto a conferir, não prova de irregularidade. '
                'RF05 (dispensa/inexigibilidade) é uma hipótese legal prevista em lei; serve só para priorizar análise.</div>',
                unsafe_allow_html=True)

    st.write("")
    st.markdown("### Baixar contratos por alerta (RF01 a RF05)")
    sinalizados = ler_parquet("contratos_red_flags.parquet")
    if sinalizados is None:
        st.info("A lista de contratos sinalizados ainda não foi gerada (rode `python src/analysis.py`).")
        return
    escolha = st.selectbox("Alerta", list(FLAGS_CONTRATO),
                           format_func=lambda k: f"{k} · {FLAGS_CONTRATO[k][1]}")
    coluna = FLAGS_CONTRATO[escolha][0]
    lista = sinalizados[sinalizados[coluna]].drop(columns=[c for c in sinalizados.columns if c.startswith("RF_")])
    st.caption(f"{num(len(lista))} contratos com o alerta {escolha}. O arquivo não contém nomes de fornecedores.")
    if lista.empty:
        st.info("Nenhum contrato com esse alerta.")
        return
    mostrar_df(lista.head(50), 260)
    st.caption("Prévia das 50 primeiras linhas.")
    download_sob_demanda(f"rf_{escolha}", escolha, lista, f"contratos_{escolha}.csv")


def pagina_convenios():
    cabecalho("📁", "Convênios", "Lista priorizada por número de alertas, com painel de detalhe à direita")
    exigir(flags_df)

    df = flags_df.copy()
    partes = []
    if "periodo" in F and "ANO_ASSINATURA" in df.columns:
        lo, hi = F["periodo"]
        df = df[df["ANO_ASSINATURA"].between(lo, hi)]
        partes.append(f"assinatura {lo}–{hi}")
    if F.get("situacao"):
        df = df[df["SIT_CONVENIO"].isin(F["situacao"])]
        partes.append("situação: " + ", ".join(F["situacao"]))
    if F.get("min_alertas", 0) > 0:
        df = df[df["QTD_ALERTAS"] >= F["min_alertas"]]
        partes.append(f"mínimo de {F['min_alertas']} alertas")
    for f in F.get("flags", []):
        df = df[df[f]]
    if F.get("flags"):
        partes.append("alertas: " + ", ".join(FLAGS[f] for f in F["flags"]))
    df = df.sort_values(["QTD_ALERTAS", "SOMA_PAGO"], ascending=[False, False])
    filtros_ativos(partes, f"{num(len(df))} de {num(len(flags_df))} convênios formalizados")

    c1, c2, c3 = st.columns(3)
    c1.markdown(kpi("Convênios no filtro", num(len(df)),
                    f"{pt(f'{100 * len(df) / len(flags_df):.1f}%')} dos formalizados"), unsafe_allow_html=True)
    c2.markdown(kpi("Valor global", abrevia(df["VL_GLOBAL_CONV"].sum())), unsafe_allow_html=True)
    c3.markdown(kpi("Valor pago", abrevia(df["SOMA_PAGO"].sum())), unsafe_allow_html=True)
    st.write("")

    lista, detalhe = st.columns([2.6, 1.2])
    busca = lista.text_input("Buscar por nº do convênio", placeholder="ex.: 700000")
    vis = df[df["NR_CONVENIO"].str.contains(busca.strip(), regex=False)] if busca.strip() else df
    vis_top = vis.head(500)

    tabela = pd.DataFrame({
        "Nº convênio": vis_top["NR_CONVENIO"],
        "Situação": vis_top["SIT_CONVENIO"],
        "Valor global": vis_top["VL_GLOBAL_CONV"].map(lambda v: brl(v) if pd.notna(v) else "-"),
        "Pago": vis_top["SOMA_PAGO"].map(lambda v: brl(v) if pd.notna(v) else "-"),
        "Alertas": vis_top["QTD_ALERTAS"],
    })
    with lista:
        st.caption(f"Mostrando {num(len(vis_top))} de {num(len(vis))} (máx. 500, ordenado por alertas)")
        if vis.empty:
            st.info("Nenhum convênio com esses filtros.")
        else:
            mostrar_df(tabela)
            exporta = vis.drop(columns=["QTD_ALERTAS"]).rename(columns=FLAGS)
            for col in FLAGS.values():
                exporta[col] = exporta[col].astype(object).map({True: "Sim", False: "Não"})
            exporta.insert(len(exporta.columns), "Qtd. alertas", vis["QTD_ALERTAS"].values)
            download_sob_demanda("convenios", str((partes, busca)), exporta, "convenios_filtrados.csv")

    with detalhe:
        st.markdown("**Detalhe do convênio**")
        if vis_top.empty:
            return
        escolhido = st.selectbox("Convênio", vis_top["NR_CONVENIO"].tolist(), label_visibility="collapsed")
        r = vis_top[vis_top["NR_CONVENIO"] == escolhido].iloc[0]
        ativos = [FLAGS[f] for f in FLAGS if bool(r[f])]
        pills = "".join(pill(a, PASTEL_CORAL) for a in ativos) if ativos else pill("Sem alertas", PASTEL_VERDE)
        fmt = lambda v: brl(v) if pd.notna(v) else "-"
        st.markdown(
            f'<div class="painel"><h4>Nº {escolhido}</h4>{pill(str(r["SIT_CONVENIO"]), PASTEL_AZUL)}'
            f'<div style="margin:10px 0 4px 0;color:{MUDO};font-size:0.78rem">Alertas ({int(r["QTD_ALERTAS"])})</div>{pills}'
            f'<div class="linha"><span>Valor global</span><span>{fmt(r["VL_GLOBAL_CONV"])}</span></div>'
            f'<div class="linha"><span>Soma dos contratos</span><span>{fmt(r["SOMA_CONTRATOS"])}</span></div>'
            f'<div class="linha"><span>Soma paga</span><span>{fmt(r["SOMA_PAGO"])}</span></div></div>',
            unsafe_allow_html=True)


def comparar(a, coluna, rotulo):
    g = a.assign(**{coluna: a[coluna].fillna("Não informado")}).groupby(coluna).agg(
        CONTRATOS=("QTD_CONTRATOS", "sum"), VALOR=("VALOR_TOTAL", "sum")).reset_index()
    g = g.sort_values("CONTRATOS", ascending=False)
    g["% dos contratos"] = 100 * g["CONTRATOS"] / g["CONTRATOS"].sum()
    g["% do valor"] = 100 * g["VALOR"] / g["VALOR"].sum()
    longo = g.melt(id_vars=coluna, value_vars=["% dos contratos", "% do valor"], var_name="Medida", value_name="%")
    fig = px.bar(longo, x=coluna, y="%", color="Medida", barmode="group",
                 color_discrete_map={"% dos contratos": AZUL, "% do valor": LARANJA})
    fig.update_traces(texttemplate="%{y:.1f}", textposition="outside")
    fig.update_xaxes(categoryorder="array", categoryarray=g[coluna].tolist())
    grafico(fig, x=rotulo, y="% do total (demais filtros aplicados)")
    fonte()


def pagina_contratos():
    cabecalho("📄", "Contratos", "Quem contrata, como contrata e onde o valor se concentra")
    cruz = ler_csv("modalidade_x_processo.csv")
    conc = ler_csv("concentracao_fornecedores_pj.csv")
    exigir(agg_df, cruz, conc)

    lo, hi = F["periodo"]
    DIMENSOES = (("aquisicao", "TIPO_AQUISICAO_CONTRATO", "aquisição"),
                 ("modalidade", "MODALIDADE_LICITACAO", "modalidade"),
                 ("fornecedor", "TIPO_FORNECEDOR", "fornecedor"))

    def recorte(ignorar=None):
        """Aplica período e filtros; `ignorar` deixa de fora o filtro da própria dimensão do gráfico."""
        r = agg_df[agg_df["ANO_CONTRATO"].between(lo, hi)]
        for chave, coluna, _ in DIMENSOES:
            if F.get(chave) and chave != ignorar:
                r = r[r[coluna].fillna("Não informado").isin(F[chave])]
        return r

    a = recorte()
    partes = [f"período {lo}–{hi}"] if (lo, hi) != (ANO_MIN, ANO_MAX) else []
    for chave, _, nome in DIMENSOES:
        if F.get(chave):
            partes.append(f"{nome}: " + ", ".join(F[chave]))
    filtros_ativos(partes, f"{num(a['QTD_CONTRATOS'].sum())} contratos no recorte "
                           f"(exclui datas inválidas e objetos pouco frequentes agrupados em 'OUTROS')")
    if a.empty or a["QTD_CONTRATOS"].sum() == 0:
        st.info("Nenhum contrato com esses filtros.")
        return

    c1, c2, c3 = st.columns(3)
    total, valor = int(a["QTD_CONTRATOS"].sum()), float(a["VALOR_TOTAL"].sum())
    c1.markdown(kpi("Contratos no recorte", num(total)), unsafe_allow_html=True)
    c2.markdown(kpi("Valor contratado", abrevia(valor)), unsafe_allow_html=True)
    c3.markdown(kpi("Valor médio por contrato", brl(valor / total)), unsafe_allow_html=True)
    st.write("")

    por_ano = a.groupby("ANO_CONTRATO").agg(CONTRATOS=("QTD_CONTRATOS", "sum")).reset_index()
    por_ano["ANO"] = por_ano["ANO_CONTRATO"].astype(int)
    por_ano = marcar_parcial(por_ano)
    st.markdown("**Contratos assinados por ano (no recorte)**")
    grafico(px.bar(por_ano, x="ANO", y="CONTRATOS", color="SITUACAO", color_discrete_map=CORES_ANO), 280,
            x="Ano de assinatura", y="Quantidade de contratos")
    fonte("2026 é ano parcial.")

    abas = st.tabs(["Tipo de aquisição", "Modalidade", "Pessoa física x jurídica", "Objetos",
                    "Modalidade x processo", "Concentração PJ"])
    with abas[0]:
        comparar(recorte("aquisicao"), "TIPO_AQUISICAO_CONTRATO", "Tipo de aquisição")
        st.caption("Compare a barra azul (quantidade) com a laranja (valor): onde o valor pesa mais que a quantidade. "
                   "Este gráfico ignora o filtro de tipo de aquisição, para mostrar a distribuição completa.")
    with abas[1]:
        comparar(recorte("modalidade"), "MODALIDADE_LICITACAO", "Modalidade de licitação")
        st.caption("'Não informado' mistura falta de preenchimento e processos que não são licitação "
                   "(veja a aba Modalidade x processo). Este gráfico ignora o filtro de modalidade, "
                   "para mostrar a distribuição completa.")
    with abas[2]:
        comparar(recorte("fornecedor"), "TIPO_FORNECEDOR", "Tipo de fornecedor")
        st.caption("Fornecedores pessoa física são anonimizados na base tratada. "
                   "Este gráfico ignora o filtro de tipo de fornecedor, para mostrar a distribuição completa.")
    with abas[3]:
        obj = a[~a["OBJETO_AGRUPADO"].fillna("").str.startswith("OUTROS")
                & (a["OBJETO_AGRUPADO"].fillna("") != "NÃO INFORMADO")]
        top = obj.groupby("OBJETO_AGRUPADO").agg(C=("QTD_CONTRATOS", "sum"), V=("VALOR_TOTAL", "sum")) \
                 .sort_values("C", ascending=False).head(15).reset_index()
        st.markdown("**Objetos de contrato mais frequentes no recorte**")
        tabela_html(["Objeto (agrupado)", "Contratos", "Valor total"],
                    [[r["OBJETO_AGRUPADO"], num(r["C"]), brl(r["V"])] for _, r in top.iterrows()])
        fonte("Objetos com menos de 10 ocorrências ficam agrupados em 'OUTROS' para proteger a privacidade.")
    with abas[4]:
        st.markdown("**Contratos sem modalidade, por tipo de processo de compra** (todo o período)")
        cruz = cruz.sort_values("SEM_MODALIDADE", ascending=False)
        tabela_html(["Tipo de processo", "Contratos", "Sem modalidade", "% do tipo sem modalidade",
                     "% de todos os sem modalidade"],
                    [[r["TIPO_PROCESSO"], num(r["CONTRATOS"]), num(r["SEM_MODALIDADE"]),
                      pt(f"{r['%_DO_TIPO_SEM_MODALIDADE']:.1f}%"), pt(f"{r['%_DOS_SEM_MODALIDADE']:.1f}%")]
                     for _, r in cruz.iterrows()])
        fonte("A modalidade só faz sentido em licitação; nos demais processos a ausência é esperada.")
    with abas[5]:
        r = conc.iloc[0]
        k1, k2, k3, k4 = st.columns(4)
        k1.markdown(kpi("5 maiores fornecedores PJ", pt(f"{r['TOP5_PCT']:.2f}%"), "do valor PJ"), unsafe_allow_html=True)
        k2.markdown(kpi("10 maiores", pt(f"{r['TOP10_PCT']:.2f}%"), "do valor PJ"), unsafe_allow_html=True)
        k3.markdown(kpi("100 maiores", pt(f"{r['TOP100_PCT']:.2f}%"), "do valor PJ"), unsafe_allow_html=True)
        k4.markdown(kpi("HHI", pt(f"{r['HHI']:.1f}"), "abaixo de 1.500 = baixa concentração"), unsafe_allow_html=True)
        st.caption(f"{num(r['FORNECEDORES_PJ'])} fornecedores PJ e {num(r['CONTRATOS_PJ'])} contratos (todo o período). "
                   "O painel mostra apenas medidas de concentração, sem ranking nominal de fornecedores.")
        fonte()


def pagina_metodologia():
    cabecalho("ℹ️", "Metodologia", "Como os números foram construídos e o que o painel não afirma")
    st.markdown(f"""
**Fonte.** Arquivos públicos do SICONV/Transferegov (contratos, licitações, convênios e pagamentos), publicados em {DATA_FONTE}.

**Modelo.** Esquema estrela em parquet. Os dados brutos e os pagamentos individuais não ficam no repositório.

**Janela de datas.** Só entram nas análises por ano datas entre 2008 e 17/07/2026. Datas impossíveis na fonte
(398 contratos, como o ano 0002 ou 2029, e 34 pagamentos, como 1985 ou 2031) foram tratadas como inválidas.
**2026 é ano parcial.**

**ID de contrato repetido.** 2.866 linhas compartilham 1.245 IDs; nenhuma é cópia exata. As linhas foram mantidas
e o caso virou alerta (RF02). As 1.621 linhas excedentes somam R$ 2,92 bi (1,43% do valor total); sem elas o valor
total seria R$ 201,30 bi.

**Modalidade "Não informado".** Mistura falta de preenchimento e processos que não são licitação (dispensa,
inexigibilidade, cotação), nos quais não há modalidade a informar. A aba Modalidade x processo mostra o cruzamento.

**Privacidade.** Fornecedores pessoa física são anonimizados. O painel não exibe ranking nominal de fornecedores
e os arquivos para download não contêm nomes. Houve exclusão preventiva, por independência profissional, de
convênios de uma lista privada mantida fora do repositório.

**Downloads.** As listas de contratos por alerta (RF01 a RF05) e de convênios filtrados são exportadas em CSV
(separador `;`, decimal `,`), prontas para abrir no Excel.

**Red flags.** São regras simples que apontam pontos a conferir. Não provam irregularidade e não substituem a análise
de quem audita ou presta contas.
""")


{PAGINAS[0]: pagina_visao_geral, PAGINAS[1]: pagina_red_flags, PAGINAS[2]: pagina_convenios,
 PAGINAS[3]: pagina_contratos, PAGINAS[4]: pagina_metodologia}[pagina]()
