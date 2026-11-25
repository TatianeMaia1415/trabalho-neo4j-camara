"""
Passo 1.3 - Coleta de deputados, partidos e proposições (com autores).

Gera em dados/brutos/:
  deputados_leg57.csv     -> deputados da 57ª legislatura (2023-2027); um deputado pode
                             aparecer mais de uma vez se trocou de partido
  partidos_leg57.csv      -> partidos da 57ª legislatura (sigla e nome)
  proposicoes.csv         -> as proposições ligadas às votações escolhidas (6x1 + ambientais)
  proposicoes_autores.csv -> autores de cada proposição (relação AUTOR_DE)
Rodar com: python scripts\05_coleta_deputados_partidos_autores.py
"""
from pathlib import Path

import pandas as pd
from tqdm import tqdm

from api_camara import consultar_dados, consultar_paginado

PASTA = Path(__file__).resolve().parent.parent / "dados" / "brutos"
ID_PEC_6X1 = "2233802"

# 1) Deputados da 57ª legislatura
deputados = pd.DataFrame(consultar_paginado("deputados", idLegislatura=57))
deputados = deputados[["id", "nome", "siglaPartido", "siglaUf", "idLegislatura", "email", "urlFoto"]]
deputados.to_csv(PASTA / "deputados_leg57.csv", index=False, encoding="utf-8-sig")
trocaram = deputados.groupby("id")["siglaPartido"].nunique()
print(f"Deputados: {deputados['id'].nunique()} distintos ({len(deputados)} linhas; "
      f"{(trocaram > 1).sum()} aparecem com mais de um partido)")

# 2) Partidos da 57ª legislatura
partidos = pd.DataFrame(consultar_paginado("partidos", idLegislatura=57))
partidos = partidos[["id", "sigla", "nome"]]
partidos.to_csv(PASTA / "partidos_leg57.csv", index=False, encoding="utf-8-sig")
print(f"Partidos: {len(partidos)}")
siglas_sem_cadastro = set(deputados["siglaPartido"]) - set(partidos["sigla"])
if siglas_sem_cadastro:
    print(f"  siglas usadas por deputados mas ausentes da lista de partidos: {sorted(siglas_sem_cadastro)}")

# 3) Validação: todo deputado que votou está na lista?
ids_lista = set(deputados["id"].astype(str))
for arquivo in ("6x1_votos.csv", "ambiente_votos.csv"):
    votos = pd.read_csv(PASTA / arquivo, dtype=str)
    faltando = set(votos["idDeputado"]) - ids_lista
    print(f"Validação {arquivo}: {votos['idDeputado'].nunique()} deputados votantes, "
          f"{len(faltando)} fora da lista de deputados" + (f" -> {sorted(faltando)}" if faltando else " (ok)"))

# 4) Proposições ligadas às votações escolhidas
selecao = pd.read_csv(PASTA / "ambiente_polaridade.csv", dtype=str)
candidatas = pd.read_csv(PASTA / "ambiente_candidatas_votacoes.csv", dtype=str)
ligacoes = candidatas[candidatas["idVotacao"].isin(selecao["idVotacao"])][["idVotacao", "proposicao_id"]]
ligacoes = pd.concat([ligacoes, pd.DataFrame([{"idVotacao": v, "proposicao_id": ID_PEC_6X1}
                      for v in pd.read_csv(PASTA / "6x1_votacoes_resumo.csv", dtype=str)
                      .query("n_votos != '0'")["idVotacao"]])], ignore_index=True).drop_duplicates()
ligacoes.to_csv(PASTA / "votacoes_proposicoes_selecionadas.csv", index=False, encoding="utf-8-sig")

ids_prop = sorted(ligacoes["proposicao_id"].unique())
print(f"\nProposições ligadas às votações escolhidas: {len(ids_prop)}")

proposicoes, autores = [], []
for id_prop in tqdm(ids_prop, desc="Buscando proposições e autores"):
    p = consultar_dados(f"proposicoes/{id_prop}")
    proposicoes.append({
        "id": p.get("id"), "siglaTipo": p.get("siglaTipo"), "numero": p.get("numero"),
        "ano": p.get("ano"), "ementa": p.get("ementa"), "dataApresentacao": p.get("dataApresentacao"),
        "situacao": (p.get("statusProposicao") or {}).get("descricaoSituacao"),
    })
    for a in consultar_dados(f"proposicoes/{id_prop}/autores"):
        uri = a.get("uri") or ""
        autores.append({
            "idProposicao": id_prop, "nome": a.get("nome"), "tipo": a.get("tipo"),
            "idDeputado": uri.rstrip("/").split("/")[-1] if "/deputados/" in uri else None,
            "ordemAssinatura": a.get("ordemAssinatura"), "proponente": a.get("proponente"),
        })

df_prop = pd.DataFrame(proposicoes)
df_aut = pd.DataFrame(autores)
df_prop.to_csv(PASTA / "proposicoes.csv", index=False, encoding="utf-8-sig")
df_aut.to_csv(PASTA / "proposicoes_autores.csv", index=False, encoding="utf-8-sig")

print("\n== Proposições e autores ==")
for _, p in df_prop.iterrows():
    aut = df_aut[df_aut["idProposicao"] == str(p["id"])]
    deps = aut["idDeputado"].notna().sum()
    primeiros = "; ".join(aut.sort_values("ordemAssinatura")["nome"].head(3))
    print(f"  {p['siglaTipo']} {p['numero']}/{p['ano']} (id {p['id']}): {len(aut)} autores "
          f"({deps} deputados) - {primeiros}")

print(f"\nArquivos salvos em {PASTA}")