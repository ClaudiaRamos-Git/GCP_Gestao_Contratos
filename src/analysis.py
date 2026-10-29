"""Análise exploratória (EDA), estatística descritiva e red flags do projeto GCP_Gestao_Contratos.

Lê as tabelas de data/processed/ geradas por src/transform.py (rode o transform antes).
fato_contrato e fato_pagamento existem só localmente (não vão para o Git); o fato_pagamento completo é opcional.
Gera:
  - relatório no terminal (números para o README, seções 7, 8 e 13);
  - tabelas em outputs/ (CSV com ';' e decimal ',');
  - data/processed/red_flags_convenio.parquet e outputs/red_flags_resumo.csv (usados pelo app).

Execução (na raiz do projeto):  python src/analysis.py
"""
import os

import numpy as np
import pandas as pd

PROC = "data/processed/"
OUT = "outputs/"
# Data de publicação dos arquivos na fonte: referência para prazos vencidos
DATA_REFERENCIA = pd.Timestamp("2026-07-17")
OUTROS = "OUTROS (objetos pouco frequentes)"
# Janela de datas plausíveis (o SICONV começa em 2008; a fonte foi publicada em DATA_REFERENCIA)
ANO_MIN = 2008
ANO_MAX = DATA_REFERENCIA.year
DATA_MIN = pd.Timestamp(f"{ANO_MIN}-01-01")


# ---------------------------------------------------------------------------
# Auxiliares
# ---------------------------------------------------------------------------
def titulo(texto):
    print("\n" + "=" * 78 + f"\n{texto}\n" + "=" * 78)


def pct(parte, total):
    return round(100 * parte / total, 2) if total else 0.0


def brl(valor):
    return f"R$ {valor:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")


def salvar_csv(df, nome):
    os.makedirs(OUT, exist_ok=True)
    df.to_csv(OUT + nome, index=False, sep=";", decimal=",", encoding="utf-8-sig")


def carregar():
    contrato = pd.read_parquet(PROC + "fato_contrato.parquet")
    convenio = pd.read_parquet(PROC + "dim_convenio.parquet")
    licitacao = pd.read_parquet(PROC + "dim_licitacao.parquet")
    agg_mensal = pd.read_parquet(PROC + "agg_pagamento_convenio_mes.parquet")
    contrato["ANO"] = contrato["DATA_ASSINATURA_CONTRATO"].dt.year
    # Atributos da licitação no contrato (modalidade e tipo de processo)
    atributos = licitacao[["ID_LICITACAO", "MODALIDADE_LICITACAO", "TP_PROCESSO_COMPRA"]]
    contrato = contrato.merge(atributos.drop_duplicates("ID_LICITACAO"), on="ID_LICITACAO", how="left")
    return contrato, convenio, licitacao, agg_mensal


# ---------------------------------------------------------------------------
# 1. Visão geral e período
# ---------------------------------------------------------------------------
def visao_geral(contrato, convenio, licitacao, agg_mensal):
    titulo("1. VISÃO GERAL E PERÍODO")
    print(f"Contratos: {len(contrato):,} | Convênios: {len(convenio):,} "
          f"(formalizados: {int(convenio['FORMALIZADO'].sum()):,}) | Licitações: {len(licitacao):,}")
    print(f"Pagamentos (soma das agregadas): {int(agg_mensal['QTD_PAGAMENTOS'].sum()):,} | "
          f"Valor pago: {brl(agg_mensal['VALOR_PAGO'].sum())}")
    ass = contrato["DATA_ASSINATURA_CONTRATO"]
    valida = ass.between(DATA_MIN, DATA_REFERENCIA)
    fora = int(ass.notna().sum() - valida.sum())
    print(f"Assinatura de contratos (datas plausíveis, {ANO_MIN} a {DATA_REFERENCIA:%d/%m/%Y}): "
          f"{ass[valida].min():%d/%m/%Y} a {ass[valida].max():%d/%m/%Y}")
    print(f"  -> {fora:,} contratos com assinatura fora dessa janela (ex.: {ass.min():%d/%m/%Y} e "
          f"{ass.max():%d/%m/%Y}), tratados como data inválida na análise por ano")
    conv_ass = convenio["DIA_ASSIN_CONV"]
    print(f"Assinatura de convênios: {conv_ass.min():%d/%m/%Y} a {conv_ass.max():%d/%m/%Y}")
    meses = agg_mensal["ANO_MES"].dropna().astype(str)
    plausiveis = meses[(meses >= f"{ANO_MIN}-01") & (meses <= f"{DATA_REFERENCIA:%Y-%m}")].sort_values()
    n_fora = int(agg_mensal.loc[~agg_mensal["ANO_MES"].astype(str).isin(plausiveis.unique()), "QTD_PAGAMENTOS"].sum())
    print(f"Pagamentos (mês, janela plausível): {plausiveis.iloc[0]} a {plausiveis.iloc[-1]} "
          f"| pagamentos fora da janela: {n_fora:,} (de {meses.min()} a {meses.max()})")


# ---------------------------------------------------------------------------
# 2. Qualidade dos dados
# ---------------------------------------------------------------------------
def qualidade(contrato, convenio, licitacao):
    titulo("2. QUALIDADE DOS DADOS (ausentes e duplicidades)")
    linhas = []
    for nome, df, colunas in [
        ("contrato", contrato, ["DATA_PUBLICACAO_CONTRATO", "DATA_ASSINATURA_CONTRATO",
                                "DATA_FIM_VIGENCIA_CONTRATO", "TIPO_AQUISICAO_CONTRATO"]),
        ("convênio", convenio, ["DIA_ASSIN_CONV", "VL_EMPENHADO_CONV", "VL_DESEMBOLSADO_CONV",
                                "VALOR_GLOBAL_ORIGINAL_CONV", "SIT_CONVENIO"]),
        ("licitação", licitacao, ["DATA_PUBLICACAO_LICITACAO", "DATA_HOMOLOGACAO_LICITACAO",
                                  "MODALIDADE_LICITACAO", "VALOR_LICITACAO"]),
    ]:
        for col in colunas:
            if col not in df.columns:
                continue
            if col in ("TIPO_AQUISICAO_CONTRATO", "SIT_CONVENIO", "MODALIDADE_LICITACAO"):
                ausentes = int((df[col] == "Não informado").sum())
            else:
                ausentes = int(df[col].isna().sum())
            linhas.append({"tabela": nome, "coluna": col, "ausentes": ausentes,
                           "pct": pct(ausentes, len(df))})
    tabela = pd.DataFrame(linhas)
    print(tabela.to_string(index=False))
    salvar_csv(tabela, "qualidade_ausentes.csv")
    rep = contrato["ID_CONTRATO_REPETIDO"].astype(bool)
    print(f"\nID_CONTRATO repetido: {int(rep.sum()):,} linhas "
          f"({contrato.loc[rep, 'ID_CONTRATO'].nunique():,} IDs distintos)")
    # Diagnóstico: as linhas repetidas são cópias exatas ou contratos diferentes com o mesmo ID?
    r = contrato[rep]
    excedentes = r.duplicated("ID_CONTRATO", keep="first")
    exatas = r.duplicated(keep="first")
    valor_total = contrato["VALOR_GLOBAL_CONTRATO"].sum()
    valor_exced = r.loc[excedentes, "VALOR_GLOBAL_CONTRATO"].sum()
    print(f"  Linhas excedentes (além da 1ª de cada ID): {int(excedentes.sum()):,} | "
          f"cópias exatas (todas as colunas iguais): {int(exatas.sum()):,}")
    print(f"  Valor das linhas excedentes: {brl(valor_exced)} = {pct(valor_exced, valor_total)}% "
          f"do valor total ({brl(valor_total)})")
    print(f"  Valor total mantendo 1 linha por ID repetido: {brl(valor_total - valor_exced)}")


# ---------------------------------------------------------------------------
# 3. Distribuição dos valores
# ---------------------------------------------------------------------------
def distribuicao_valores(contrato):
    titulo("3. DISTRIBUIÇÃO DO VALOR GLOBAL DOS CONTRATOS")
    v = contrato["VALOR_GLOBAL_CONTRATO"].dropna()
    print(f"Média: {brl(v.mean())} | Mediana: {brl(v.median())} | "
          f"Desvio-padrão: {brl(v.std())} | Assimetria: {v.skew():,.1f}")
    quantis = v.quantile([0.01, 0.05, 0.25, 0.5, 0.75, 0.9, 0.95, 0.99, 1.0])
    tabela = pd.DataFrame({"percentil": [f"{int(q * 100)}%" for q in quantis.index],
                           "valor_R$": quantis.values})
    print(tabela.assign(**{"valor_R$": tabela["valor_R$"].map(brl)}).to_string(index=False))
    salvar_csv(tabela, "distribuicao_valor_contrato.csv")

    positivos = v[v > 0]
    log = np.log10(positivos)
    q1, q3 = log.quantile([0.25, 0.75])
    limite = 10 ** (q3 + 1.5 * (q3 - q1))
    n_out = int((positivos > limite).sum())
    print(f"\nOutliers (IQR sobre log10 dos valores > 0): limite {brl(limite)} | "
          f"{n_out:,} contratos acima ({pct(n_out, len(positivos))}%)")

    ordenado = v.sort_values(ascending=False)
    total = v.sum()
    for fracao in (0.01, 0.10):
        n = max(int(len(v) * fracao), 1)
        print(f"Os {int(fracao * 100)}% maiores contratos ({n:,}) concentram "
              f"{pct(ordenado.head(n).sum(), total)}% do valor total ({brl(total)})")
    print(f"Contratos com valor zero: {int((v == 0).sum()):,} ({pct(int((v == 0).sum()), len(v))}%)")


# ---------------------------------------------------------------------------
# 4. Tendência no tempo
# ---------------------------------------------------------------------------
def tendencia(contrato, agg_mensal):
    titulo("4. TENDÊNCIA NO TEMPO")
    c = contrato[contrato["ANO"].between(ANO_MIN, ANO_MAX)]
    por_ano = c.groupby("ANO").agg(
        CONTRATOS=("ID_LICITACAO", "size"),
        VALOR_TOTAL=("VALOR_GLOBAL_CONTRATO", "sum"),
        VALOR_MEDIANO=("VALOR_GLOBAL_CONTRATO", "median"),
    ).reset_index()
    por_ano["ANO"] = por_ano["ANO"].astype(int)
    por_ano[["VALOR_TOTAL", "VALOR_MEDIANO"]] = por_ano[["VALOR_TOTAL", "VALOR_MEDIANO"]].round(2)
    por_ano["VARIACAO_QTD_%"] = por_ano["CONTRATOS"].pct_change().mul(100).round(1)
    # Último ano é parcial (dados até DATA_REFERENCIA): variação não comparável
    parcial = por_ano["ANO"] == ANO_MAX
    por_ano["OBS"] = np.where(parcial, f"parcial (até {DATA_REFERENCIA:%d/%m})", "")
    por_ano.loc[parcial, "VARIACAO_QTD_%"] = np.nan
    fora = int(contrato["ANO"].notna().sum() - len(c))
    exibir = por_ano.assign(VALOR_TOTAL=por_ano["VALOR_TOTAL"].map(brl),
                            VALOR_MEDIANO=por_ano["VALOR_MEDIANO"].map(brl))
    print(exibir.to_string(index=False))
    print(f"Contratos com ano de assinatura fora de {ANO_MIN}-{ANO_MAX}: {fora:,} (excluídos desta tabela)")
    salvar_csv(por_ano, "contratos_por_ano.csv")

    agg = agg_mensal.copy()
    agg["ANO"] = pd.to_numeric(agg["ANO_MES"].str.slice(0, 4), errors="coerce")
    pag_ano = agg.groupby("ANO").agg(PAGAMENTOS=("QTD_PAGAMENTOS", "sum"),
                                     VALOR_PAGO=("VALOR_PAGO", "sum")).reset_index()
    pag_ano["ANO"] = pag_ano["ANO"].astype(int)
    dentro = pag_ano["ANO"].between(ANO_MIN, ANO_MAX)
    print("\nPagamentos por ano:")
    print(pag_ano[dentro].assign(VALOR_PAGO=pag_ano.loc[dentro, "VALOR_PAGO"].map(brl)).to_string(index=False))
    print(f"Fora de {ANO_MIN}-{ANO_MAX}: {int(pag_ano.loc[~dentro, 'PAGAMENTOS'].sum()):,} pagamentos, "
          f"{brl(pag_ano.loc[~dentro, 'VALOR_PAGO'].sum())} (anos: "
          f"{', '.join(map(str, pag_ano.loc[~dentro, 'ANO']))}); {ANO_MAX} é parcial")
    salvar_csv(pag_ano[dentro], "pagamentos_por_ano.csv")

    por_tipo = agg.groupby("TIPO_FORNECEDOR").agg(
        PAGAMENTOS=("QTD_PAGAMENTOS", "sum"), VALOR_PAGO=("VALOR_PAGO", "sum")).reset_index()
    por_tipo["%_PAGAMENTOS"] = (100 * por_tipo["PAGAMENTOS"] / por_tipo["PAGAMENTOS"].sum()).round(2)
    por_tipo["%_VALOR"] = (100 * por_tipo["VALOR_PAGO"] / por_tipo["VALOR_PAGO"].sum()).round(2)
    print("\nPagamentos: pessoa física x jurídica")
    print(por_tipo.to_string(index=False))

    caminho = PROC + "fato_pagamento.parquet"
    if os.path.exists(caminho):
        vp = pd.read_parquet(caminho, columns=["VL_PAGO"])["VL_PAGO"]
        q = vp.quantile([0.5, 0.9, 0.99])
        print(f"\nPagamento individual: mediana {brl(q[0.5])} | p90 {brl(q[0.9])} | p99 {brl(q[0.99])} "
              f"| máximo {brl(vp.max())}")


# ---------------------------------------------------------------------------
# 5. Comparações entre grupos
# ---------------------------------------------------------------------------
def comparacoes(contrato):
    titulo("5. COMPARAÇÕES ENTRE GRUPOS (contratos)")
    resultados = {}
    for rotulo, coluna in [("tipo_aquisicao", "TIPO_AQUISICAO_CONTRATO"),
                           ("modalidade", "MODALIDADE_LICITACAO"),
                           ("tipo_fornecedor", "TIPO_FORNECEDOR")]:
        t = contrato.groupby(coluna, dropna=False).agg(
            CONTRATOS=("ID_LICITACAO", "size"),
            VALOR_TOTAL=("VALOR_GLOBAL_CONTRATO", "sum"),
            VALOR_MEDIANO=("VALOR_GLOBAL_CONTRATO", "median"),
            VALOR_MEDIO=("VALOR_GLOBAL_CONTRATO", "mean"),
        ).reset_index().sort_values("CONTRATOS", ascending=False)
        t["%_CONTRATOS"] = (100 * t["CONTRATOS"] / t["CONTRATOS"].sum()).round(2)
        t["%_VALOR"] = (100 * t["VALOR_TOTAL"] / t["VALOR_TOTAL"].sum()).round(2)
        print(f"\nPor {rotulo}:")
        print(t.to_string(index=False))
        salvar_csv(t, f"comparacao_{rotulo}.csv")
        resultados[rotulo] = t

    tp = contrato["TP_PROCESSO_COMPRA"].fillna("Não informado").value_counts()
    print("\nTipo de processo de compra (contratos):")
    print(tp.head(10).to_string())

    # Modalidade "Não informado" x tipo de processo: a ausência de modalidade vem de
    # processos que não são licitação (dispensa, inexigibilidade, cotação)?
    sem = contrato["MODALIDADE_LICITACAO"].fillna("Não informado") == "Não informado"
    proc = contrato["TP_PROCESSO_COMPRA"].fillna("Não informado")
    cruz = (pd.DataFrame({"TIPO_PROCESSO": proc, "SEM_MODALIDADE": sem})
            .groupby("TIPO_PROCESSO").agg(CONTRATOS=("SEM_MODALIDADE", "size"),
                                          SEM_MODALIDADE=("SEM_MODALIDADE", "sum")).reset_index())
    cruz["%_DO_TIPO_SEM_MODALIDADE"] = (100 * cruz["SEM_MODALIDADE"] / cruz["CONTRATOS"]).round(2)
    cruz["%_DOS_SEM_MODALIDADE"] = (100 * cruz["SEM_MODALIDADE"] / cruz["SEM_MODALIDADE"].sum()).round(2)
    cruz = cruz.sort_values("SEM_MODALIDADE", ascending=False)
    print("\nModalidade 'Não informado' por tipo de processo de compra:")
    print(cruz.to_string(index=False))
    licit = cruz["TIPO_PROCESSO"].eq("Licitação")
    print(f"Contratos sem modalidade cujo processo NÃO é licitação: "
          f"{pct(int(cruz.loc[~licit, 'SEM_MODALIDADE'].sum()), int(cruz['SEM_MODALIDADE'].sum()))}% "
          f"(inclui 'Não informado' no tipo de processo)")
    salvar_csv(cruz, "modalidade_x_processo.csv")


# ---------------------------------------------------------------------------
# 6. Relações entre variáveis do convênio
# ---------------------------------------------------------------------------
def relacoes(convenio):
    titulo("6. RELAÇÕES ENTRE VARIÁVEIS DO CONVÊNIO (correlação de Spearman)")
    f = convenio[convenio["FORMALIZADO"]].copy()
    f["DURACAO_VIGENCIA_DIAS"] = (f["DIA_FIM_VIGENC_CONV"] - f["DIA_INIC_VIGENC_CONV"]).dt.days
    cols = ["VL_GLOBAL_CONV", "DURACAO_VIGENCIA_DIAS", "QTD_TA", "QTD_PRORROGA"]
    corr = f[cols].corr(method="spearman").round(3)
    print(corr.to_string())
    print("Obs.: correlação indica associação, não causalidade.")
    corr.reset_index().rename(columns={"index": "variavel"}).pipe(salvar_csv, "correlacao_convenio.csv")


# ---------------------------------------------------------------------------
# 7. Concentração de fornecedores pessoa jurídica
# ---------------------------------------------------------------------------
def concentracao(contrato):
    titulo("7. CONCENTRAÇÃO DE FORNECEDORES PESSOA JURÍDICA")
    pj = contrato[contrato["TIPO_FORNECEDOR"] == "Pessoa jurídica"]
    g = pj.groupby("ID_FORNECEDOR_CONTRATO").agg(
        CONTRATOS=("ID_LICITACAO", "size"),
        VALOR_TOTAL=("VALOR_GLOBAL_CONTRATO", "sum"),
    ).reset_index(drop=True)
    total = g["VALOR_TOTAL"].sum()
    print(f"Fornecedores PJ distintos: {len(g):,} | contratos PJ: {len(pj):,} | valor: {brl(total)}")
    # Sem nomes: o painel e os arquivos publicados mostram só medidas de concentração,
    # nunca rankings identificados de fornecedores.
    print(f"Maior número de contratos de um fornecedor: {int(g['CONTRATOS'].max()):,} | "
          f"maior valor de um fornecedor: {brl(g['VALOR_TOTAL'].max())}")

    ordenado = g["VALOR_TOTAL"].sort_values(ascending=False)
    topos = {}
    for n in (5, 10, 100):
        topos[n] = pct(ordenado.head(n).sum(), total)
        print(f"Os {n} maiores fornecedores PJ concentram {topos[n]}% do valor PJ")
    participacao = g["VALOR_TOTAL"] / total
    hhi = float((participacao ** 2).sum() * 10000)
    print(f"Índice de Herfindahl-Hirschman (HHI) do valor PJ: {hhi:,.1f} "
          "(valores abaixo de 1.500 indicam baixa concentração)")
    salvar_csv(pd.DataFrame([{
        "FORNECEDORES_PJ": len(g), "CONTRATOS_PJ": len(pj), "VALOR_PJ": round(total, 2),
        "TOP5_PCT": topos[5], "TOP10_PCT": topos[10], "TOP100_PCT": topos[100], "HHI": round(hhi, 1),
        "MAX_CONTRATOS_UM_FORNECEDOR": int(g["CONTRATOS"].max()),
        "MAX_VALOR_UM_FORNECEDOR": round(float(g["VALOR_TOTAL"].max()), 2)}]),
        "concentracao_fornecedores_pj.csv")
    return hhi, pct(ordenado.head(10).sum(), total)


# ---------------------------------------------------------------------------
# 8. Red flags (regras, limiares e resultados)
# ---------------------------------------------------------------------------
def red_flags(contrato, convenio, agg_mensal, hhi, top10_pct):
    titulo("8. RED FLAGS (alertas de risco: pontos a conferir, não prova de irregularidade)")
    resumo = []

    def registrar(codigo, descricao, colunas, limiar, base, qtd):
        resumo.append({"codigo": codigo, "descricao": descricao, "colunas": colunas, "limiar": limiar,
                       "base": base, "ocorrencias": int(qtd), "pct": pct(int(qtd), base)})

    # --- Nível do contrato ---
    c = contrato.copy()
    c["RF_VALOR_ZERO"] = c["VALOR_GLOBAL_CONTRATO"] == 0
    c["RF_ID_REPETIDO"] = c["ID_CONTRATO_REPETIDO"].astype(bool)
    c["RF_VIGENCIA_INVERTIDA"] = c["DATA_FIM_VIGENCIA_CONTRATO"] < c["DATA_INICIO_VIGENCIA_CONTRATO"]
    vigencia_conv = convenio[["NR_CONVENIO", "DIA_INIC_VIGENC_CONV", "DIA_FIM_VIGENC_CONV"]]
    c = c.merge(vigencia_conv, on="NR_CONVENIO", how="left")
    ass = c["DATA_ASSINATURA_CONTRATO"]
    c["RF_FORA_VIGENCIA"] = (ass < c["DIA_INIC_VIGENC_CONV"]) | (ass > c["DIA_FIM_VIGENC_CONV"])
    texto = c["MODALIDADE_LICITACAO"].fillna("") + " " + c["TP_PROCESSO_COMPRA"].fillna("")
    c["RF_SEM_LICITACAO"] = texto.str.contains("Inexigib|Dispens", case=False, na=False)

    n = len(c)
    registrar("RF01", "Contrato com valor global zerado", "VALOR_GLOBAL_CONTRATO", "= 0", n, c["RF_VALOR_ZERO"].sum())
    registrar("RF02", "ID de contrato repetido", "ID_CONTRATO", "> 1 ocorrência", n, c["RF_ID_REPETIDO"].sum())
    registrar("RF03", "Fim de vigência anterior ao início (contrato)",
              "DATA_INICIO/FIM_VIGENCIA_CONTRATO", "fim < início", n, c["RF_VIGENCIA_INVERTIDA"].sum())
    registrar("RF04", "Assinatura do contrato fora da vigência do convênio",
              "DATA_ASSINATURA_CONTRATO, DIA_INIC/FIM_VIGENC_CONV", "assinatura < início ou > fim", n,
              c["RF_FORA_VIGENCIA"].sum())
    registrar("RF05", "Contratação por inexigibilidade ou dispensa",
              "MODALIDADE_LICITACAO, TP_PROCESSO_COMPRA", "contém 'Inexigib' ou 'Dispens'", n,
              c["RF_SEM_LICITACAO"].sum())

    # Lista de contratos sinalizados (sem nomes de fornecedores), para o painel e o download
    rf_contrato = ["RF_VALOR_ZERO", "RF_ID_REPETIDO", "RF_VIGENCIA_INVERTIDA",
                   "RF_FORA_VIGENCIA", "RF_SEM_LICITACAO"]
    marcado = c[rf_contrato].fillna(False).astype(bool).any(axis=1)
    cols_contrato = [x for x in ["ID_CONTRATO", "NR_CONVENIO", "ID_LICITACAO", "DATA_ASSINATURA_CONTRATO",
                                 "VALOR_GLOBAL_CONTRATO", "TIPO_AQUISICAO_CONTRATO", "MODALIDADE_LICITACAO",
                                 "TP_PROCESSO_COMPRA", "TIPO_FORNECEDOR"] if x in c.columns]
    sinalizados = c.loc[marcado, cols_contrato + rf_contrato].copy()
    sinalizados[rf_contrato] = sinalizados[rf_contrato].fillna(False).astype(bool)
    sinalizados.to_parquet(PROC + "contratos_red_flags.parquet", index=False, compression="zstd")
    print(f"Contratos com ao menos um alerta (RF01 a RF05): {len(sinalizados):,}")

    # --- Nível do convênio (apenas formalizados) ---
    form = convenio[convenio["FORMALIZADO"]].copy()
    por_conv = c.groupby("NR_CONVENIO").agg(
        N_CONTRATOS=("ID_LICITACAO", "size"),
        SOMA_CONTRATOS=("VALOR_GLOBAL_CONTRATO", "sum"),
        RF_VALOR_ZERO=("RF_VALOR_ZERO", "any"),
        RF_FORA_VIGENCIA=("RF_FORA_VIGENCIA", "any"),
    ).reset_index()
    pagos = agg_mensal.groupby("NR_CONVENIO").agg(SOMA_PAGO=("VALOR_PAGO", "sum")).reset_index()
    f = form.merge(por_conv, on="NR_CONVENIO", how="left").merge(pagos, on="NR_CONVENIO", how="left")
    for col in ("RF_VALOR_ZERO", "RF_FORA_VIGENCIA"):
        f[col] = f[col].fillna(False).astype(bool)

    f["RF_CONTRATADO_ACIMA_GLOBAL"] = (
        (f["VL_GLOBAL_CONV"] > 0) & (f["SOMA_CONTRATOS"] > f["VL_GLOBAL_CONV"] * 1.01 + 1))
    f["RF_PAGO_ACIMA_DESEMBOLSO"] = (
        f["SOMA_PAGO"].notna() & f["VL_DESEMBOLSADO_CONV"].notna()
        & (f["SOMA_PAGO"] > f["VL_DESEMBOLSADO_CONV"] * 1.01 + 1))
    vencido = f["DIA_LIMITE_PREST_CONTAS"].notna() & (f["DIA_LIMITE_PREST_CONTAS"] < DATA_REFERENCIA)
    encerrado = f["SIT_CONVENIO"].str.contains(r"Conclu|Aprovad|Cancel|Anulad", case=False, na=False)
    f["RF_PRESTACAO_VENCIDA"] = vencido & ~encerrado
    lim_ta = f["QTD_TA"].quantile(0.99)
    lim_pr = f["QTD_PRORROGA"].quantile(0.99)
    f["RF_MUITOS_ADITIVOS"] = (f["QTD_TA"] > lim_ta) | (f["QTD_PRORROGA"] > lim_pr)

    nf = len(f)
    registrar("RF06", "Contratado acima do valor global do convênio (tolerância 1%)",
              "soma VALOR_GLOBAL_CONTRATO, VL_GLOBAL_CONV", "soma > 1,01 x global", nf,
              f["RF_CONTRATADO_ACIMA_GLOBAL"].sum())
    registrar("RF07", "Pago acima do valor desembolsado (tolerância 1%)",
              "soma VL_PAGO, VL_DESEMBOLSADO_CONV", "pago > 1,01 x desembolsado", nf,
              f["RF_PAGO_ACIMA_DESEMBOLSO"].sum())
    registrar("RF08", "Prestação de contas com prazo vencido e convênio não encerrado",
              "DIA_LIMITE_PREST_CONTAS, SIT_CONVENIO", f"prazo < {DATA_REFERENCIA:%d/%m/%Y}", nf,
              f["RF_PRESTACAO_VENCIDA"].sum())
    registrar("RF09", "Muitos termos aditivos ou prorrogações (percentil 99)",
              "QTD_TA, QTD_PRORROGA", f"QTD_TA > {lim_ta:g} ou QTD_PRORROGA > {lim_pr:g}", nf,
              f["RF_MUITOS_ADITIVOS"].sum())

    resumo_df = pd.DataFrame(resumo)
    print(resumo_df[["codigo", "descricao", "base", "ocorrencias", "pct"]].to_string(index=False))
    print(f"\nConcentração PJ (informativo): top 10 fornecedores = {top10_pct}% do valor PJ | HHI = {hhi:,.1f}")
    print("\nSituação dos convênios com prestação vencida (verificar a regra de 'encerrado'):")
    print(f.loc[vencido, "SIT_CONVENIO"].value_counts().head(12).to_string())

    flags = ["RF_VALOR_ZERO", "RF_FORA_VIGENCIA", "RF_CONTRATADO_ACIMA_GLOBAL",
             "RF_PAGO_ACIMA_DESEMBOLSO", "RF_PRESTACAO_VENCIDA", "RF_MUITOS_ADITIVOS"]
    f["QTD_ALERTAS"] = f[flags].sum(axis=1).astype(int)
    print("\nConvênios formalizados por número de alertas:")
    print(f["QTD_ALERTAS"].value_counts().sort_index().to_string())

    f["ANO_ASSINATURA"] = f["DIA_ASSIN_CONV"].dt.year.astype("Int64")
    saida = f[["NR_CONVENIO", "SIT_CONVENIO", "ANO_ASSINATURA", "VL_GLOBAL_CONV", "SOMA_CONTRATOS", "SOMA_PAGO"]
              + flags + ["QTD_ALERTAS"]]
    saida.to_parquet(PROC + "red_flags_convenio.parquet", index=False, compression="zstd")
    salvar_csv(resumo_df, "red_flags_resumo.csv")
    print("\n✅ Gerados: data/processed/red_flags_convenio.parquet, data/processed/contratos_red_flags.parquet "
          "e outputs/red_flags_resumo.csv")


# ---------------------------------------------------------------------------
# Execução
# ---------------------------------------------------------------------------
def main():
    print("🔍 Carregando as tabelas do esquema estrela...")
    contrato, convenio, licitacao, agg_mensal = carregar()
    visao_geral(contrato, convenio, licitacao, agg_mensal)
    qualidade(contrato, convenio, licitacao)
    distribuicao_valores(contrato)
    tendencia(contrato, agg_mensal)
    comparacoes(contrato)
    relacoes(convenio)
    hhi, top10 = concentracao(contrato)
    red_flags(contrato, convenio, agg_mensal, hhi, top10)
    print("\n🏁 Análise concluída.")


if __name__ == "__main__":
    main()
