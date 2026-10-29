import os
import re
import pandas as pd

LISTA_PRIVADA = "data/private/cnpjs_excluir.csv"

def so_digitos(x):
    return re.sub(r"\D", "", str(x))

def excluir_convenios_conflito(contrato, licitacao, pagamento, convenio, proposta):
    """Remove de todas as tabelas os convênios ligados aos CNPJs da lista privada,
    seja como proponente, fornecedor ou favorecido."""
    if not os.path.exists(LISTA_PRIVADA):
        return contrato, licitacao, pagamento, convenio

    lista = pd.read_csv(LISTA_PRIVADA, dtype=str, sep=None,
                        engine="python", encoding="utf-8-sig")
    cnpjs = set(lista.iloc[:, 0].map(so_digitos))
    cnpjs.discard("")

    # 1) como proponente (convenente): proposta -> convênio
    props = set(proposta.loc[proposta["IDENTIF_PROPONENTE"].map(so_digitos).isin(cnpjs),
                             "ID_PROPOSTA"])
    conv_proponente = set(convenio.loc[convenio["ID_PROPOSTA"].isin(props), "NR_CONVENIO"])

    # 2) como fornecedor em contratos (via licitação)
    c = contrato[contrato["ID_FORNECEDOR_CONTRATO"].map(so_digitos).isin(cnpjs)]
    conv_contrato = set(c.merge(licitacao, on="ID_LICITACAO")["NR_CONVENIO"])

    # 3) como favorecido em pagamentos
    p = pagamento[pagamento["IDENTIF_FORNECEDOR"].map(so_digitos).isin(cnpjs)]
    conv_pagamento = set(p["NR_CONVENIO"])

    excluir = conv_proponente | conv_contrato | conv_pagamento
    lic_excluir = set(licitacao.loc[licitacao["NR_CONVENIO"].isin(excluir), "ID_LICITACAO"])

    contrato = contrato[~contrato["ID_LICITACAO"].isin(lic_excluir)]
    licitacao = licitacao[~licitacao["NR_CONVENIO"].isin(excluir)]
    pagamento = pagamento[~pagamento["NR_CONVENIO"].isin(excluir)]
    convenio = convenio[~convenio["NR_CONVENIO"].isin(excluir)]

    print("Filtro de conflito: convênios removidos:", len(excluir),
          "| como proponente:", len(conv_proponente))
    return contrato, licitacao, pagamento, convenio