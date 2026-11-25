"""
Passo 1.2c - Coleta dos votos individuais nas 14 votações ambientais selecionadas.
Lê a lista e a polaridade de dados/brutos/ambiente_polaridade.csv.

Gera em dados/brutos/:
  ambiente_votos.csv             -> voto de cada deputado (com partido NO MOMENTO do voto)
  ambiente_orientacoes.csv       -> orientação de cada partido/bloco/liderança
  ambiente_recursos_autores.csv  -> quem assinou os recursos (REC 5/2024 e REC 7/2024)
Rodar com: python scripts\04_coleta_votos_ambientais.py
"""
from pathlib import Path

import pandas as pd
from tqdm import tqdm

from api_camara import consultar_dados

PASTA = Path(__file__).resolve().parent.parent / "dados" / "brutos"
RECURSOS = {"2422887": "REC 5/2024 (PL 364/2019)", "2428615": "REC 7/2024 (PL 10273/2018)"}

selecao = pd.read_csv(PASTA / "ambiente_polaridade.csv", dtype=str)
print(f"Votações selecionadas: {len(selecao)}")

# 1) Votos e orientações de cada votação
votos, orientacoes = [], []
for _, s in tqdm(selecao.iterrows(), total=len(selecao), desc="Buscando votos"):
    id_vot = s["idVotacao"]
    for x in consultar_dados(f"votacoes/{id_vot}/votos"):
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

df_votos = pd.DataFrame(votos)
df_votos.to_csv(PASTA / "ambiente_votos.csv", index=False, encoding="utf-8-sig")
pd.DataFrame(orientacoes).to_csv(PASTA / "ambiente_orientacoes.csv", index=False, encoding="utf-8-sig")

# 2) Validação: os votos coletados batem com o placar oficial?
contagem = pd.crosstab(df_votos["idVotacao"], df_votos["tipoVoto"])
print("\n== Conferência: votos coletados x placar oficial ==")
print(f"{'votação':<14} {'proposição':<28} {'Sim':>9} {'Não':>9}  outros tipos")
ok = True
for _, s in selecao.iterrows():
    linha = contagem.loc[s["idVotacao"]] if s["idVotacao"] in contagem.index else pd.Series(dtype=int)
    sim, nao = int(linha.get("Sim", 0)), int(linha.get("Não", 0))
    outros = {k: int(v) for k, v in linha.items() if k not in ("Sim", "Não") and v > 0}
    confere = sim == int(s["sim"]) and nao == int(s["nao"])
    ok &= confere
    marca = "ok" if confere else "DIFERENTE"
    print(f"{s['idVotacao']:<14} {s['proposicao'][:28]:<28} {sim:>4}/{s['sim']:<4} {nao:>4}/{s['nao']:<4} "
          f"{outros}  [{marca}]")
print("\nTodas as votações conferem com o placar oficial." if ok
      else "\nATENÇÃO: alguma votação não bate com o placar - me mande esta saída.")

# 3) Quem apresentou os recursos (para confirmar a polaridade)
autores = []
for id_rec, nome in RECURSOS.items():
    lista = consultar_dados(f"proposicoes/{id_rec}/autores")
    print(f"\n== Autores do {nome}: {len(lista)} assinaturas ==")
    for a in lista:
        uri = a.get("uri") or ""
        autores.append({"idRecurso": id_rec, "recurso": nome, "nome": a.get("nome"),
                        "idDeputado": uri.rstrip("/").split("/")[-1] if "/deputados/" in uri else None,
                        "ordemAssinatura": a.get("ordemAssinatura"), "proponente": a.get("proponente")})
    primeiros = sorted(lista, key=lambda a: a.get("ordemAssinatura") or 999)[:5]
    print("   primeiros signatários:", "; ".join(a.get("nome", "?") for a in primeiros))
pd.DataFrame(autores).to_csv(PASTA / "ambiente_recursos_autores.csv", index=False, encoding="utf-8-sig")

print(f"\nArquivos salvos em {PASTA}")
print(f"  votos: {len(df_votos)} linhas | deputados distintos: {df_votos['idDeputado'].nunique()}"
      f" | orientações: {len(orientacoes)} linhas | assinaturas de recursos: {len(autores)}")