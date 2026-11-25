"""
Passo 1.2b - Listar CADA votação das proposições ambientais pré-selecionadas,
para marcarmos a polaridade votação por votação.

Usa os arquivos já baixados no passo 1.2a (não baixa nada de novo),
e consulta a API só para conferir o PL 2564/2025 (que não apareceu na busca).

Gera em dados/brutos/:
  ambiente_votacoes_para_classificar.csv -> uma linha por votação, com colunas em branco
                                            (incluir, sim_significa, justificativa) para preenchermos
Rodar com: python scripts\03_listar_votacoes_ambientais.py
"""
from pathlib import Path

import pandas as pd

from api_camara import consultar_dados

PASTA = Path(__file__).resolve().parent.parent / "dados" / "brutos"
PASTA_ARQUIVOS = PASTA / "arquivos_camara"

# Proposições pré-selecionadas (grupo A = entram; grupo B = conferir)
SELECIONADAS = {
    # grupo A
    "2345368": "A", "345311": "A", "2362190": "A",   # MPV 1150/2022, PL 490/2007, REQ 1526/2023
    "1548579": "A", "2238434": "A", "2456731": "A",  # PL 182/2024, PL 528/2020, PL 3469/2024
    "257161": "A", "2556071": "A",                   # PL 2159/2021, PL 4392/2025
    "2190986": "A", "2422887": "A",                  # PL 364/2019, REC 5/2024
    "2525254": "A", "2486315": "A", "2606189": "A",  # PDL 717/2024, PL 849/2025, REQ 1233/2026
    # grupo B
    "2324721": "B", "2431186": "B", "2244008": "B",  # PL 1366/2022, PL 1594/2024, PL 2950/2019
    "2479834": "B", "2175977": "B", "2428615": "B",  # PL 4870/2024, PL 10273/2018, REC 7/2024
    "2438687": "B", "106701": "B", "2541991": "B",   # PL 2225/2024, PL 5809/2025, MPV 1308/2025
    "2525620": "B",                                  # PL 2898/2025
}

# 1) Votações candidatas (do passo 1.2a) + detalhes extras do arquivo anual de votações
cand = pd.read_csv(PASTA / "ambiente_candidatas_votacoes.csv", dtype=str)
cand = cand[cand["proposicao_id"].isin(SELECIONADAS)]
cand["grupo"] = cand["proposicao_id"].map(SELECIONADAS)

votacoes = pd.concat([pd.read_csv(f, sep=";", dtype=str)
                      for f in sorted(PASTA_ARQUIVOS.glob("votacoes-*.csv"))])
extra = votacoes[["id", "ultimaApresentacaoProposicao_descricao"]].rename(columns={"id": "idVotacao"})

# Uma votação pode estar ligada a 2 proposições (ex.: PL 364/2019 e REC 5/2024) -> junta numa linha
tabela = (cand.groupby("idVotacao")
          .agg(proposicoes=("proposicao", lambda s: " + ".join(sorted(set(s)))),
               grupo=("grupo", "min"), data=("data", "first"),
               sim=("votosSim", "first"), nao=("votosNao", "first"),
               outros=("votosOutros", "first"), aprovacao=("aprovacao", "first"),
               descricao=("descricao", "first"))
          .reset_index()
          .merge(extra, on="idVotacao", how="left")
          .sort_values(["grupo", "data", "idVotacao"]))

# Colunas para preenchermos juntos
tabela["incluir"] = ""          # S ou N
tabela["sim_significa"] = ""    # PRO_AMBIENTE ou CONTRA_AMBIENTE
tabela["justificativa"] = ""

tabela.to_csv(PASTA / "ambiente_votacoes_para_classificar.csv", index=False, encoding="utf-8-sig")

# 2) Mostrar agrupado por proposição
for (grupo, props), bloco in tabela.groupby(["grupo", "proposicoes"], sort=False):
    print(f"\n{'=' * 100}\n[{grupo}] {props}  ({len(bloco)} votações nominais)")
    for _, r in bloco.iterrows():
        aprov = "APROVADA" if r["aprovacao"] == "1" else "REJEITADA"
        print(f"  {r['idVotacao']} | {r['data']} | Sim={r['sim']} Não={r['nao']} Outros={r['outros']} | {aprov}")
        print(f"     {str(r['descricao'])[:400]}")

# 3) Conferir o PL 2564/2025 na API (inclui votações simbólicas)
print(f"\n{'=' * 100}\nConferência: PL 2564/2025 (não apareceu entre as nominais)")
for p in consultar_dados("proposicoes", siglaTipo="PL", numero=2564, ano=2025):
    print(f"  id={p['id']} | {p['ementa'][:150]}")
    for v in consultar_dados(f"proposicoes/{p['id']}/votacoes"):
        if v.get("siglaOrgao") == "PLEN":
            print(f"    {v['id']} | {v['data']} | {v['descricao'][:200]}")

print(f"\nTotal: {tabela['idVotacao'].nunique()} votações. "
      f"Arquivo para classificar: {PASTA / 'ambiente_votacoes_para_classificar.csv'}")