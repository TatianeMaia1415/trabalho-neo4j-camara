"""
Passo 1.4 - Coleta das frentes parlamentares da 57ª legislatura e dos seus membros.

Coleta longa (um pedido por frente), por isso SALVA O PROGRESSO:
cada frente baixada vira um arquivo em dados/brutos/frentes_cache/<id>.json.
Se parar no meio, é só rodar de novo: as frentes já baixadas são puladas.

Gera em dados/brutos/:
  frentes_leg57.csv   -> id e título de cada frente
  frentes_membros.csv -> uma linha por (frente, deputado), com o papel (coordenador, membro...)
Rodar com: python scripts\06_coleta_frentes.py
"""
import json
from pathlib import Path

import pandas as pd
from tqdm import tqdm

from api_camara import consultar_dados, consultar_paginado

PASTA = Path(__file__).resolve().parent.parent / "dados" / "brutos"
CACHE = PASTA / "frentes_cache"
CACHE.mkdir(exist_ok=True)

# 1) Lista de frentes
frentes = pd.DataFrame(consultar_paginado("frentes", idLegislatura=57))[["id", "titulo", "idLegislatura"]]
frentes.to_csv(PASTA / "frentes_leg57.csv", index=False, encoding="utf-8-sig")
ja_baixadas = {int(f.stem) for f in CACHE.glob("*.json")}
pendentes = [i for i in frentes["id"] if int(i) not in ja_baixadas]
print(f"Frentes na 57ª legislatura: {len(frentes)} | já baixadas: {len(ja_baixadas)} | faltam: {len(pendentes)}")

# 2) Membros de cada frente (com progresso salvo)
for id_frente in tqdm(pendentes, desc="Buscando membros"):
    membros = consultar_dados(f"frentes/{id_frente}/membros")
    temporario = CACHE / f"{id_frente}.part"
    temporario.write_text(json.dumps(membros, ensure_ascii=False), encoding="utf-8")
    temporario.replace(CACHE / f"{id_frente}.json")   # só conta como baixada quando terminou

# 3) Junta tudo numa tabela
linhas = []
for id_frente in frentes["id"]:
    for m in json.loads((CACHE / f"{id_frente}.json").read_text(encoding="utf-8")):
        linhas.append({
            "idFrente": id_frente,
            "idDeputado": m.get("id"),
            "nome": m.get("nome"),
            "siglaPartido": m.get("siglaPartido"),
            "siglaUf": m.get("siglaUf"),
            "papel": m.get("titulo"),            # Coordenador, Membro, etc.
            "dataInicio": m.get("dataInicio"),
            "dataFim": m.get("dataFim"),
        })
membros = pd.DataFrame(linhas)
membros.to_csv(PASTA / "frentes_membros.csv", index=False, encoding="utf-8-sig")

# 4) Resumo
por_frente = membros.groupby("idFrente").size().rename("n_membros")
resumo = frentes.set_index("id").join(por_frente).fillna({"n_membros": 0})
print(f"\nVínculos frente-deputado: {len(membros)} | deputados distintos: {membros['idDeputado'].nunique()}")
print(f"Frentes sem nenhum membro deputado: {(resumo['n_membros'] == 0).sum()}")
print(f"Papéis encontrados: {membros['papel'].value_counts().to_dict()}")

print("\n== 10 maiores frentes ==")
for id_f, r in resumo.sort_values("n_membros", ascending=False).head(10).iterrows():
    print(f"  {int(r['n_membros']):>4} membros | {id_f} | {r['titulo'][:90]}")

print("\n== Frentes ligadas a meio ambiente / agro (prévia da pergunta 3) ==")
filtro = resumo["titulo"].str.contains(r"ambient|agropec|clima|sustent|florest|indígen|mineraç|agro",
                                        case=False, regex=True)
for id_f, r in resumo[filtro].sort_values("n_membros", ascending=False).iterrows():
    print(f"  {int(r['n_membros']):>4} membros | {id_f} | {r['titulo'][:90]}")

print(f"\nArquivos salvos em {PASTA}")