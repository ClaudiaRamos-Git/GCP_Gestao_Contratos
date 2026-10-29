"""Pipeline de tratamento (ETL) do projeto GCP_Gestao_Contratos.
 
Etapas: leitura dos CSV brutos -> exclusão preventiva de convênios -> verificação
da exclusão -> tratamento e anonimização -> esquema estrela em parquet ->
validação das chaves entre as tabelas.
 
Execução (na raiz do projeto):  python src/transform.py
"""
import os
 
import numpy as np
import pandas as pd
 
try:  # execução direta: python src/transform.py
    from utils import LISTA_PRIVADA, excluir_convenios_conflito, so_digitos
except ImportError:  # execução como pacote
    from src.utils import LISTA_PRIVADA, excluir_convenios_conflito, so_digitos
 
RAW = "data/raw/"
PROC = "data/processed/"
OUT = "outputs/"
 
# Chaves e identificadores sempre lidos como texto (preserva zeros à esquerda
# e garante que as ligações entre tabelas comparem o mesmo tipo).
CHAVES = {
    "NR_CONVENIO": str, "ID_LICITACAO": str, "ID_CONTRATO": str, "NR_CONTRATO": str,
    "ID_PROPOSTA": str, "ID_FORNECEDOR_CONTRATO": str, "IDENTIF_FORNECEDOR": str,
    "NR_MOV_FIN": str, "IDENTIF_PROPONENTE": str,
}
 
 
# ---------------------------------------------------------------------------
# Funções auxiliares
# ---------------------------------------------------------------------------
def ler_csv(nome, **kwargs):
    return pd.read_csv(RAW + nome, sep=";", encoding="utf-8-sig",
                       dtype=CHAVES, low_memory=False, **kwargs)
 
 
def converter_valor(serie, nome=""):
    """Converte texto monetário em número sem esconder falhas.
 
    Com vírgula: o ponto é milhar e a vírgula é decimal ('1.234,56' -> 1234.56).
    Sem vírgula: o texto é mantido ('431' -> 431). O que não converte fica vazio
    (NaN) e é contado, em vez de virar zero.
    """
    texto = serie.astype("string").str.strip()
    tem_virgula = texto.str.contains(",", na=False)
    ponto_sem_virgula = texto.str.contains(r"\.", na=False) & ~tem_virgula
    limpo = texto.where(
        ~tem_virgula,
        texto.str.replace(".", "", regex=False).str.replace(",", ".", regex=False),
    )
    numero = pd.to_numeric(limpo, errors="coerce")
    falhas = numero.isna() & texto.notna()
    print(f"  [{nome}] vazios: {texto.isna().sum()} | falhas de conversão: {falhas.sum()} "
          f"| ponto sem vírgula (conferir): {ponto_sem_virgula.sum()}")
    return numero
 
 
def converter_data(serie, nome="", formato="%d/%m/%Y"):
    """Converte datas e informa quantas não puderam ser convertidas."""
    convertida = pd.to_datetime(serie, format=formato, errors="coerce")
    falhas = serie.notna() & convertida.isna()
    print(f"  [{nome}] datas não convertidas: {falhas.sum()}")
    return convertida
 
 
def preencher_nao_informado(df, colunas):
    for col in colunas:
        if col in df.columns:
            df[col] = df[col].fillna("Não informado").astype(str).str.strip()
            df[col] = df[col].replace({"": "Não informado", "nan": "Não informado", "None": "Não informado"})
    return df
 
 
def eh_pessoa_fisica(ids):
    """CPF mascarado (asteriscos) ou identificador com menos de 14 caracteres."""
    texto = ids.astype(str)
    return texto.str.contains(r"\*", na=False) | (texto.str.len() < 14)
 
 
# ---------------------------------------------------------------------------
# Verificação da exclusão preventiva
# ---------------------------------------------------------------------------
def verificar_exclusao(contrato, pagamento):
    """Confirma que nenhum CNPJ da lista privada restou como fornecedor/favorecido."""
    if not os.path.exists(LISTA_PRIVADA):
        print("  Lista privada ausente: nenhuma exclusão aplicada.")
        return
    lista = pd.read_csv(LISTA_PRIVADA, dtype=str, sep=None, engine="python", encoding="utf-8-sig")
    cnpjs = set(lista.iloc[:, 0].map(so_digitos))
    cnpjs.discard("")
    sobra_contrato = contrato["ID_FORNECEDOR_CONTRATO"].map(so_digitos).isin(cnpjs).sum()
    sobra_pagamento = pagamento["IDENTIF_FORNECEDOR"].map(so_digitos).isin(cnpjs).sum()
    assert sobra_contrato == 0 and sobra_pagamento == 0, (
        f"Exclusão falhou: {sobra_contrato} contratos e {sobra_pagamento} pagamentos restantes."
    )
    print("  ✅ Verificação da exclusão: nenhum registro da lista privada restou.")
 
 
# ---------------------------------------------------------------------------
# Tratamento por tabela (recebem DataFrames já filtrados)
# ---------------------------------------------------------------------------
def tratar_licitacoes(df):
    print("Tratando licitações...")
    df = df.copy()
    for col in ["DATA_PUBLICACAO_LICITACAO", "DATA_HOMOLOGACAO_LICITACAO"]:
        if col in df.columns:
            df[col] = converter_data(df[col], col)
    if "VALOR_LICITACAO" in df.columns:
        df["VALOR_LICITACAO"] = converter_valor(df["VALOR_LICITACAO"], "VALOR_LICITACAO")
    df = preencher_nao_informado(
        df, ["MODALIDADE_LICITACAO", "TP_PROCESSO_COMPRA", "TIPO_LICITACAO", "STATUS_LICITACAO"])
    previstas = ["ID_LICITACAO", "NR_CONVENIO", "MODALIDADE_LICITACAO", "TP_PROCESSO_COMPRA",
                 "TIPO_LICITACAO", "DATA_PUBLICACAO_LICITACAO", "DATA_HOMOLOGACAO_LICITACAO",
                 "STATUS_LICITACAO", "VALOR_LICITACAO"]
    return df[[c for c in previstas if c in df.columns]].copy()
 
 
def tratar_contratos(df, licitacao):
    print("Tratando contratos...")
    df = df.copy()
 
    # NR_CONVENIO do contrato, obtido via licitação (seção 5.3 do README)
    mapa = licitacao[["ID_LICITACAO", "NR_CONVENIO"]].drop_duplicates("ID_LICITACAO")
    df = df.merge(mapa, on="ID_LICITACAO", how="left")
 
    # Datas
    if "DATA_PUBLICACAO_CONTRATO" in df.columns:
        df["DATA_PUBLICACAO_CONTRATO"] = converter_data(
            df["DATA_PUBLICACAO_CONTRATO"], "DATA_PUBLICACAO_CONTRATO", "%Y-%m-%d")
    for col in ["DATA_ASSINATURA_CONTRATO", "DATA_INICIO_VIGENCIA_CONTRATO", "DATA_FIM_VIGENCIA_CONTRATO"]:
        if col in df.columns:
            datas = converter_data(df[col], col)
            invalidas = datas.dt.year.isin([1, 3010]) | (datas.dt.year > 2030)
            print(f"  [{col}] datas impossíveis (anos 1, 3010 ou > 2030) tornadas vazias: {invalidas.sum()}")
            datas.loc[invalidas] = pd.NaT
            df[col] = datas
 
    # Valores
    if "VALOR_GLOBAL_CONTRATO" in df.columns:
        df["VALOR_GLOBAL_CONTRATO"] = converter_valor(df["VALOR_GLOBAL_CONTRATO"], "VALOR_GLOBAL_CONTRATO")
 
    # Anonimização de pessoas físicas (seção 5.5)
    if "ID_FORNECEDOR_CONTRATO" in df.columns and "NOME_FORNECEDOR_CONTRATO" in df.columns:
        pf = eh_pessoa_fisica(df["ID_FORNECEDOR_CONTRATO"])
        df["TIPO_FORNECEDOR"] = np.where(pf, "Pessoa física", "Pessoa jurídica")
        df.loc[pf, "NOME_FORNECEDOR_CONTRATO"] = "Pessoa física"
        df.loc[pf, "ID_FORNECEDOR_CONTRATO"] = "ANONIMIZADO"
        print(f"  Fornecedores pessoa física anonimizados: {pf.sum():,}")
 
    # Categóricas
    df = preencher_nao_informado(df, ["TIPO_AQUISICAO_CONTRATO"])
 
    # ID_CONTRATO repetido: linhas mantidas e marcadas (nada é descartado em silêncio)
    if "ID_CONTRATO" in df.columns:
        df["ID_CONTRATO_REPETIDO"] = df["ID_CONTRATO"].notna() & df.duplicated("ID_CONTRATO", keep=False)
        print(f"  Linhas com ID_CONTRATO repetido (marcadas): {df['ID_CONTRATO_REPETIDO'].sum():,}")
 
    # Objeto normalizado: só alimenta o agregado de objetos (agg_contrato_objeto).
    # O texto livre original NÃO segue para o fato_contrato publicado.
    if "OBJETO_CONTRATO" in df.columns:
        df["OBJETO_NORM"] = (
            df["OBJETO_CONTRATO"].astype("string").str.upper()
            .str.replace(r"\s+", " ", regex=True).str.strip().str.slice(0, 150)
        )
        df["OBJETO_NORM"] = df["OBJETO_NORM"].fillna("NÃO INFORMADO").replace({"": "NÃO INFORMADO"})
    df = df.drop(columns=["OBJETO_CONTRATO"], errors="ignore")
    return df
 
 
def tratar_convenios(df):
    print("Tratando convênios...")
    df = df.copy()
 
    colunas_data = ["DIA_ASSIN_CONV", "DIA_PUBL_CONV", "DIA_INIC_VIGENC_CONV", "DIA_FIM_VIGENC_CONV",
                    "DIA_FIM_VIGENC_ORIGINAL_CONV", "DIA_LIMITE_PREST_CONTAS"]
    for col in colunas_data:
        if col in df.columns:
            df[col] = converter_data(df[col], col)
 
    colunas_valor = ["VL_GLOBAL_CONV", "VL_REPASSE_CONV", "VL_CONTRAPARTIDA_CONV",
                     "VL_EMPENHADO_CONV", "VL_DESEMBOLSADO_CONV", "VALOR_GLOBAL_ORIGINAL_CONV"]
    for col in colunas_valor:
        if col in df.columns:
            df[col] = converter_valor(df[col], col)
 
    for col in ["QTD_TA", "QTD_PRORROGA", "DIAS_PREST_CONTAS"]:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")
 
    # Início de vigência anterior a 2008 vira vazio (seção 5.6)
    if "DIA_INIC_VIGENC_CONV" in df.columns:
        antigas = df["DIA_INIC_VIGENC_CONV"] < "2008-01-01"
        print(f"  Início de vigência anterior a 2008 tornado vazio: {antigas.sum()}")
        df.loc[antigas, "DIA_INIC_VIGENC_CONV"] = pd.NaT
 
    # FORMALIZADO: convênio com data de assinatura (seção 5.6)
    df["FORMALIZADO"] = df["DIA_ASSIN_CONV"].notna()
    print(f"  Convênios formalizados: {df['FORMALIZADO'].sum():,} de {len(df):,}")
 
    df = preencher_nao_informado(df, ["SIT_CONVENIO"])
 
    previstas = ["NR_CONVENIO", "ID_PROPOSTA", "SIT_CONVENIO", "SUBSITUACAO_CONV", "INSTRUMENTO_ATIVO"] \
        + colunas_data + ["DIAS_PREST_CONTAS", "QTD_TA", "QTD_PRORROGA"] + colunas_valor + ["FORMALIZADO"]
    return df[[c for c in previstas if c in df.columns]].copy()
 
 
def tratar_pagamentos(df):
    print("Tratando pagamentos...")
    df = df.copy()
    if "DATA_PAG" in df.columns:
        df["DATA_PAG"] = converter_data(df["DATA_PAG"], "DATA_PAG")
    if "DATA_EMISSAO_DL" in df.columns:
        df["DATA_EMISSAO_DL"] = converter_data(df["DATA_EMISSAO_DL"], "DATA_EMISSAO_DL", "%Y-%m-%d")
    if "VL_PAGO" in df.columns:
        df["VL_PAGO"] = converter_valor(df["VL_PAGO"], "VL_PAGO")
 
    if "IDENTIF_FORNECEDOR" in df.columns and "NOME_FORNECEDOR" in df.columns:
        pf = eh_pessoa_fisica(df["IDENTIF_FORNECEDOR"])
        df["TIPO_FORNECEDOR"] = np.where(pf, "Pessoa física", "Pessoa jurídica")
        df.loc[pf, "NOME_FORNECEDOR"] = "Pessoa física"
        df.loc[pf, "IDENTIF_FORNECEDOR"] = "ANONIMIZADO"
        print(f"  Favorecidos pessoa física anonimizados: {pf.sum():,}")
 
    previstas = ["NR_MOV_FIN", "NR_CONVENIO", "IDENTIF_FORNECEDOR", "NOME_FORNECEDOR", "TIPO_FORNECEDOR",
                 "TP_MOV_FINANCEIRA", "DATA_PAG", "DESC_DL", "VL_PAGO", "DATA_EMISSAO_DL"]
    return df[[c for c in previstas if c in df.columns]].copy()
 
 
# ---------------------------------------------------------------------------
# Dimensões geradas
# ---------------------------------------------------------------------------
def construir_dim_fornecedor(contrato, pagamento):
    a = contrato[["ID_FORNECEDOR_CONTRATO", "NOME_FORNECEDOR_CONTRATO", "TIPO_FORNECEDOR"]]
    a = a.set_axis(["ID_FORNECEDOR", "NOME_FORNECEDOR", "TIPO_FORNECEDOR"], axis=1)
    b = pagamento[["IDENTIF_FORNECEDOR", "NOME_FORNECEDOR", "TIPO_FORNECEDOR"]]
    b = b.set_axis(["ID_FORNECEDOR", "NOME_FORNECEDOR", "TIPO_FORNECEDOR"], axis=1)
    forn = pd.concat([a, b], ignore_index=True).dropna(subset=["ID_FORNECEDOR"])
    return forn.drop_duplicates("ID_FORNECEDOR").reset_index(drop=True)
 
 
def construir_dim_tempo(contrato, pagamento):
    datas = pd.concat([contrato["DATA_ASSINATURA_CONTRATO"], pagamento["DATA_PAG"]]).dropna()
    datas = datas[(datas >= "2000-01-01") & (datas <= "2030-12-31")]
    cal = pd.DataFrame({"DATA": pd.date_range(datas.min().normalize(), datas.max().normalize(), freq="D")})
    cal["ANO"] = cal["DATA"].dt.year
    cal["MES"] = cal["DATA"].dt.month
    cal["TRIMESTRE"] = cal["DATA"].dt.quarter
    cal["ANO_MES"] = cal["DATA"].dt.strftime("%Y-%m")
    return cal
 
 
def construir_agregado_objeto(contrato, licitacao, minimo=10):
    """Objetos de contrato agregados, com as colunas dos filtros do painel.
 
    Objetos com menos de `minimo` ocorrências no total viram 'OUTROS', para que
    nenhum texto raro (por exemplo, com nome de pessoa) apareça isolado.
    """
    c = contrato.merge(
        licitacao[["ID_LICITACAO", "MODALIDADE_LICITACAO"]].drop_duplicates("ID_LICITACAO"),
        on="ID_LICITACAO", how="left")
    c["MODALIDADE_LICITACAO"] = c["MODALIDADE_LICITACAO"].fillna("Não informado")
    c["ANO_CONTRATO"] = c["DATA_ASSINATURA_CONTRATO"].dt.year
    frequencia = c["OBJETO_NORM"].map(c["OBJETO_NORM"].value_counts())
    c["OBJETO_AGRUPADO"] = c["OBJETO_NORM"].where(frequencia >= minimo, "OUTROS (objetos pouco frequentes)")
    agg = (
        c.groupby(["OBJETO_AGRUPADO", "TIPO_AQUISICAO_CONTRATO", "MODALIDADE_LICITACAO",
                   "TIPO_FORNECEDOR", "ANO_CONTRATO"], dropna=False)
        .agg(QTD_CONTRATOS=("ID_LICITACAO", "size"), VALOR_TOTAL=("VALOR_GLOBAL_CONTRATO", "sum"))
        .reset_index()
    )
    # Proteção: remove linhas cujo texto de objeto cita número de CNPJ.
    tem_cnpj = agg["OBJETO_AGRUPADO"].astype(str).str.contains(
        r"\d{2}\.\d{3}\.\d{3}/\d{4}-\d{2}", regex=True)
    return agg[~tem_cnpj].reset_index(drop=True)
 
 
def construir_agregados_pagamento(pagamento):
    """Versões agregadas do pagamento, pequenas o bastante para o GitHub e o Streamlit.
 
    - por convênio, mês e tipo de fornecedor;
    - por favorecido pessoa jurídica (nunca por pessoa física).
    """
    pag = pagamento.copy()
    pag["ANO_MES"] = pag["DATA_PAG"].dt.strftime("%Y-%m")
    mensal = (
        pag.groupby(["NR_CONVENIO", "ANO_MES", "TIPO_FORNECEDOR"], dropna=False)
        .agg(QTD_PAGAMENTOS=("VL_PAGO", "size"), VALOR_PAGO=("VL_PAGO", "sum"))
        .reset_index()
    )
    pj = pag[pag["TIPO_FORNECEDOR"] == "Pessoa jurídica"]
    por_fornecedor = (
        pj.groupby(["IDENTIF_FORNECEDOR", "NOME_FORNECEDOR"], dropna=False)
        .agg(QTD_PAGAMENTOS=("VL_PAGO", "size"), VALOR_PAGO=("VL_PAGO", "sum"),
             QTD_CONVENIOS=("NR_CONVENIO", "nunique"))
        .reset_index()
    )
    return mensal, por_fornecedor
 
 
# ---------------------------------------------------------------------------
# Validação das chaves (seção 5.4)
# ---------------------------------------------------------------------------
def validar_chaves(contrato, licitacao, convenio, pagamento):
    testes = [
        ("contrato -> licitação (ID_LICITACAO)", contrato["ID_LICITACAO"].isin(licitacao["ID_LICITACAO"])),
        ("licitação -> convênio (NR_CONVENIO)", licitacao["NR_CONVENIO"].isin(convenio["NR_CONVENIO"])),
        ("pagamento -> convênio (NR_CONVENIO)", pagamento["NR_CONVENIO"].isin(convenio["NR_CONVENIO"])),
        ("contrato -> convênio (NR_CONVENIO via licitação)", contrato["NR_CONVENIO"].isin(convenio["NR_CONVENIO"])),
    ]
    linhas = []
    for nome, achou in testes:
        total, ok = len(achou), int(achou.sum())
        linhas.append({"relacao": nome, "total": total, "com_correspondencia": ok,
                       "orfaos": total - ok, "pct_integrado": round(100 * ok / total, 2)})
    resultado = pd.DataFrame(linhas)
    os.makedirs(OUT, exist_ok=True)
    resultado.to_csv(OUT + "validacao_chaves.csv", index=False, sep=";", encoding="utf-8-sig")
    print("\n=== Validação das chaves entre as tabelas ===")
    print(resultado.to_string(index=False))
    return resultado
 
 
def salvar(df, nome):
    caminho = PROC + nome
    df.to_parquet(caminho, index=False, compression="zstd")
    print(f"  ✅ {nome}: {len(df):,} linhas | {os.path.getsize(caminho) / 1e6:.1f} MB")
 
 
# ---------------------------------------------------------------------------
# Execução
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    os.makedirs(PROC, exist_ok=True)
    print("🚀 Iniciando pipeline de transformação (ETL)...\n")
 
    print("1/5 Lendo os CSV brutos...")
    contrato = ler_csv("siconv_contrato.csv")
    licitacao = ler_csv("siconv_licitacao.csv")
    convenio = ler_csv("siconv_convenio.csv")
    pagamento = ler_csv("siconv_pagamento.csv")
    caminho_proposta = RAW + "siconv_proposta.csv"
    if os.path.exists(caminho_proposta):
        proposta = ler_csv("siconv_proposta.csv", usecols=["ID_PROPOSTA", "IDENTIF_PROPONENTE"])
    elif os.path.exists(LISTA_PRIVADA):
        raise FileNotFoundError(
            "A lista privada de exclusão existe, mas data/raw/siconv_proposta.csv não foi encontrado. "
            "Sem ele o filtro não cobre os convênios em que a entidade é proponente.")
    else:
        proposta = pd.DataFrame(columns=["ID_PROPOSTA", "IDENTIF_PROPONENTE"])
    print(f"  Origem: contrato {len(contrato):,} | licitação {len(licitacao):,} | "
          f"convênio {len(convenio):,} | pagamento {len(pagamento):,}")
 
    print("\n2/5 Exclusão preventiva de convênios...")
    contrato, licitacao, pagamento, convenio = excluir_convenios_conflito(
        contrato, licitacao, pagamento, convenio, proposta)
    verificar_exclusao(contrato, pagamento)
    print(f"  Após a exclusão: contrato {len(contrato):,} | licitação {len(licitacao):,} | "
          f"convênio {len(convenio):,} | pagamento {len(pagamento):,}")
 
    print("\n3/5 Tratamento e anonimização...")
    licitacao_t = tratar_licitacoes(licitacao)
    contrato_t = tratar_contratos(contrato, licitacao_t)
    convenio_t = tratar_convenios(convenio)
    pagamento_t = tratar_pagamentos(pagamento)
 
    print("\n4/5 Dimensões fornecedor e tempo...")
    dim_fornecedor = construir_dim_fornecedor(contrato_t, pagamento_t)
    dim_tempo = construir_dim_tempo(contrato_t, pagamento_t)
 
    print("\n5/5 Gravando o esquema estrela em parquet...")
    salvar(licitacao_t, "dim_licitacao.parquet")
    agg_objeto = construir_agregado_objeto(contrato_t, licitacao_t)
    contrato_t = contrato_t.drop(columns=["OBJETO_NORM"], errors="ignore")
    salvar(contrato_t, "fato_contrato.parquet")
    salvar(agg_objeto, "agg_contrato_objeto.parquet")
    salvar(convenio_t, "dim_convenio.parquet")
    salvar(pagamento_t, "fato_pagamento.parquet")
    salvar(dim_fornecedor, "dim_fornecedor.parquet")
    salvar(dim_tempo, "dim_tempo.parquet")
    agg_mensal, agg_fornecedor = construir_agregados_pagamento(pagamento_t)
    salvar(agg_mensal, "agg_pagamento_convenio_mes.parquet")
    salvar(agg_fornecedor, "agg_pagamento_fornecedor_pj.parquet")
 
    validar_chaves(contrato_t, licitacao_t, convenio_t, pagamento_t)
    print("\n🏁 Pipeline concluído.")