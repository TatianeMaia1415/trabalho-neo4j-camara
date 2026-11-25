"""
Passo 1.5a - Inspecionar a base do Atlas Digital de Desastres (download manual, em CSV).
Só LÊ e MOSTRA a estrutura do arquivo, para escrevermos a agregação por UF no próximo passo.

Antes de rodar: salve o CSV baixado do Atlas em  dados/brutos/desastres/
Rodar com: python scripts\07a_inspecionar_atlas.py
"""
import re
from pathlib import Path

import pandas as pd

PASTA = Path(__file__).resolve().parent.parent / "dados" / "brutos" / "desastres"
arquivos = sorted(PASTA.glob("*.csv"))
if not arquivos:
    raise SystemExit(f"Nenhum .csv encontrado em {PASTA} - salve o arquivo do Atlas lá.")
arquivo = arquivos[0]
print(f"Arquivo: {arquivo.name} ({arquivo.stat().st_size / 1e6:.1f} MB)")

# A codificação de arquivos do governo varia: tenta as mais comuns
for codificacao in ("utf-8-sig", "latin-1"):
    try:
        df = pd.read_csv(arquivo, sep=";", dtype=str, encoding=codificacao)
        print(f"Codificação: {codificacao}")
        break
    except UnicodeDecodeError:
        continue

print(f"Linhas: {len(df)} | Colunas: {len(df.columns)}")
print("\n== Colunas ==")
for i, c in enumerate(df.columns):
    exemplo = df[c].dropna().iloc[0] if df[c].notna().any() else ""
    print(f"  {i:>2}. {c:<45} ex.: {str(exemplo)[:60]}")

# Mostra os valores das colunas que parecem ser de ano, UF, grupo ou tipo de desastre
print("\n== Valores das colunas-chave ==")
for c in df.columns:
    partes = set(re.split(r"[^a-z]+", c.lower()))   # "Sigla_UF" -> {"sigla", "uf"}; evita pegar "danos" como "ano"
    if partes & {"ano", "uf", "grupo", "tipo", "tipologia", "cobrade", "evento", "desastre"}:
        valores = df[c].value_counts()
        print(f"\n-- {c} ({valores.size} valores distintos) --")
        print(valores.head(15).to_string())