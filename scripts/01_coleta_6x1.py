"""
Passo 1.1 - Coleta das votações da PEC 221/2019 (fim da escala 6x1).
Gera em dados/brutos/:
  6x1_votacoes_resumo.csv  -> todas as votações candidatas e quantos votos nominais tiveram
  6x1_votos.csv            -> voto de cada deputado (com partido NO MOMENTO do voto)
  6x1_orientacoes.csv      -> orientação de cada partido/bloco/liderança
Rodar com: python scripts\01_coleta_6x1.py
"""
from pathlib import Path

import pandas as pd
from tqdm import tqdm

from api_camara import consultar_dados, consultar_paginado

ID_PEC = 2233802          # PEC 221/2019
ID_PLENARIO = 180         # idOrgao do Plenário da Câmara
PASTA = Path(__file__).resolve().parent.parent / "dados" / "brutos"
PASTA.mkdir(parents=True, exist_ok=True)

# 1) Votações vinculadas diretamente à PEC
vinculadas = consultar_dados(f"proposicoes/{ID_PEC}/votacoes")
for v in vinculadas:
    v["origem"] = "vinculada_PEC"
print(f"Votações vinculadas à PEC: {len(vinculadas)}")

# 2) Todas as votações do Plenário em 27 e 28/05/2026 (a sessão passou da meia-noite)
#    -> serve para achar destaques/requerimentos ligados a outros IDs de proposição
plenario = consultar_paginado("votacoes", idOrgao=ID_PLENARIO,
                              dataInicio="2026-05-27", dataFim="2026-05-28")
for v in plenario:
    v["origem"] = "plenario_27-28mai"
print(f"Votações do Plenário em 27-28/05/2026: {len(plenario)}")

# Junta as duas listas sem repetir
votacoes = {}
for v in vinculadas + plenario:
    if v["id"] in votacoes:
        votacoes[v["id"]]["origem"] = "ambas"
    else:
        votacoes[v["id"]] = v

# 3) Para cada votação: votos nominais e orientações
resumo, votos, orientacoes = [], [], []
for id_vot, v in tqdm(votacoes.items(), desc="Buscando votos"):
    lista_votos = consultar_dados(f"votacoes/{id_vot}/votos")
    contagem = pd.Series([x.get("tipoVoto") for x in lista_votos]).value_counts().to_dict()

    resumo.append({
        "idVotacao": id_vot,
        "data": v.get("data"),
        "siglaOrgao": v.get("siglaOrgao"),
        "origem": v["origem"],
        "aprovacao": v.get("aprovacao"),
        "n_votos": len(lista_votos),
        "sim": contagem.get("Sim", 0),
        "nao": contagem.get("Não", 0),
        "outros": len(lista_votos) - contagem.get("Sim", 0) - contagem.get("Não", 0),
        "descricao": v.get("descricao"),
    })

    if not lista_votos:   # votação simbólica: não tem votos individuais
        continue

    for x in lista_votos:
        dep = x.get("deputado_", {})
        votos.append({
            "idVotacao": id_vot,
            "idDeputado": dep.get("id"),
            "nome": dep.get("nome"),
            "siglaPartido": dep.get("siglaPartido"),   # partido na data do voto
            "siglaUf": dep.get("siglaUf"),
            "tipoVoto": x.get("tipoVoto"),
            "dataRegistroVoto": x.get("dataRegistroVoto"),
        })

    for o in consultar_dados(f"votacoes/{id_vot}/orientacoes"):
        orientacoes.append({
            "idVotacao": id_vot,
            "siglaPartidoBloco": o.get("siglaPartidoBloco"),
            "codTipoLideranca": o.get("codTipoLideranca"),
            "orientacaoVoto": o.get("orientacaoVoto"),
        })

# 4) Salvar (utf-8-sig para o Excel abrir os acentos corretamente)
df_resumo = pd.DataFrame(resumo).sort_values(["n_votos", "data"], ascending=False)
df_resumo.to_csv(PASTA / "6x1_votacoes_resumo.csv", index=False, encoding="utf-8-sig")
pd.DataFrame(votos).to_csv(PASTA / "6x1_votos.csv", index=False, encoding="utf-8-sig")
pd.DataFrame(orientacoes).to_csv(PASTA / "6x1_orientacoes.csv", index=False, encoding="utf-8-sig")

# 5) Mostrar só as votações NOMINAIS (com votos individuais)
nominais = df_resumo[df_resumo["n_votos"] > 0]
print(f"\n== {len(nominais)} votações nominais (de {len(df_resumo)} candidatas) ==")
for _, r in nominais.iterrows():
    print(f"\n{r['idVotacao']} | {r['data']} | {r['siglaOrgao']} | {r['origem']}")
    print(f"   Sim={r['sim']}  Não={r['nao']}  Outros={r['outros']}  Total={r['n_votos']}")
    print(f"   {str(r['descricao'])[:300]}")

print(f"\nArquivos salvos em {PASTA}")
print(f"  votos: {len(votos)} linhas | orientações: {len(orientacoes)} linhas")