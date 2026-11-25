"""
Passo 1.1b - Descobrir o que foi votado na 2233802-416 e comparar a orientação dos partidos
nas 3 votações nominais do Plenário (1º turno, 2º turno e requerimento).
Rodar com: python scripts\01b_detalhe_votacao.py
"""
import json
from pathlib import Path

import pandas as pd

from api_camara import consultar_dados

ID_VOT = "2233802-416"
PASTA = Path(__file__).resolve().parent.parent / "dados" / "brutos"

# 1) Detalhe da votação: qual proposição/requerimento foi votado
d = consultar_dados(f"votacoes/{ID_VOT}")
print(f"== Detalhe da votação {ID_VOT} ==")
print("Descrição:", d.get("descricao"))
for chave in ("objetosPossiveis", "proposicoesAfetadas", "ultimaApresentacaoProposicao"):
    valor = d.get(chave)
    if valor:
        print(f"\n-- {chave} --")
        print(json.dumps(valor, ensure_ascii=False, indent=2)[:1500])

# 2) Orientação dos partidos nas 3 votações do Plenário, lado a lado
ori = pd.read_csv(PASTA / "6x1_orientacoes.csv")
nomes = {"2233802-416": "Requerimento", "2233802-424": "1o turno", "2233802-438": "2o turno"}
ori["votacao"] = ori["idVotacao"].map(nomes)
tabela = ori.pivot_table(index="siglaPartidoBloco", columns="votacao",
                         values="orientacaoVoto", aggfunc="first").fillna("-")
print("\n== Orientação dos partidos/blocos ==")
print(tabela.to_string())

# 3) Tipos de voto que aparecem (para confirmar o 'Outros')
votos = pd.read_csv(PASTA / "6x1_votos.csv")
print("\n== Tipos de voto por votação ==")
print(pd.crosstab(votos["idVotacao"], votos["tipoVoto"]).to_string())