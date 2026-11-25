"""
Passo 1.6a - Baixar e INSPECIONAR as bases da pergunta 5 (2023-2026):
  - Cota parlamentar (CEAP): uma linha por despesa reembolsada
  - Eventos: audiências, reuniões, sessões
  - Presença em eventos: quais deputados estiveram em cada evento

Só baixa e mostra a estrutura; a agregação vem no passo seguinte.
Gera em dados/brutos/despesas/ e dados/brutos/eventos/ os arquivos originais.
Rodar com: python scripts\08_baixar_despesas_eventos.py
"""
from pathlib import Path

import pandas as pd

from api_camara import baixar_arquivo

ANOS = [2023, 2024, 2025, 2026]
BRUTOS = Path(__file__).resolve().parent.parent / "dados" / "brutos"
ARQ = "https://dadosabertos.camara.leg.br/arquivos"

BASES = {
    "despesas": ("https://www.camara.leg.br/cotas/Ano-{ano}.csv.zip", "despesas", "Ano-{ano}.csv.zip"),
    "eventos": (ARQ + "/eventos/csv/eventos-{ano}.csv", "eventos", "eventos-{ano}.csv"),
    "presenca": (ARQ + "/eventosPresencaDeputados/csv/eventosPresencaDeputados-{ano}.csv",
                 "eventos", "eventosPresencaDeputados-{ano}.csv"),
}


def ler(caminho):
    """Lê CSV (ou CSV dentro de .zip) separado por ';', testando as codificações mais comuns."""
    for codificacao in ("utf-8-sig", "latin-1"):
        try:
            return pd.read_csv(caminho, sep=";", dtype=str, encoding=codificacao,
                               compression="zip" if str(caminho).endswith(".zip") else None)
        except UnicodeDecodeError:
            continue


for nome, (url, pasta, arquivo) in BASES.items():
    print(f"\n{'=' * 90}\n{nome.upper()}")
    caminhos = {ano: baixar_arquivo(url.format(ano=ano), BRUTOS / pasta / arquivo.format(ano=ano))
                for ano in ANOS}

    linhas = {}
    exemplo = None
    for ano, caminho in caminhos.items():
        if caminho is None:
            continue
        df = ler(caminho)
        linhas[ano] = len(df)
        if ano == 2024:
            exemplo = df
    print(f"Linhas por ano: {linhas}")

    if exemplo is not None:
        print(f"Colunas ({len(exemplo.columns)}), com exemplo do arquivo de 2024:")
        for i, c in enumerate(exemplo.columns):
            valor = exemplo[c].dropna().iloc[0] if exemplo[c].notna().any() else ""
            print(f"  {i:>2}. {c:<42} ex.: {str(valor)[:60]}")

print("\nInspeção concluída. Me mande esta saída para escrevermos a agregação.")