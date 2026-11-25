"""
Passo 1.6b - Agregar despesas (cota parlamentar) e presença em eventos por deputado (2023-2026).

Cuidados para comparar deputados de forma justa:
  - só deputados da 57ª legislatura (sai a cota das lideranças partidárias)
  - médias MENSAIS, porque suplentes ficaram poucos meses no cargo
  - índice de gasto relativo à UF, porque o teto da cota varia por estado (passagens aéreas)

Gera em dados/processados/:
  despesas_deputado_categoria.csv, despesas_deputado_resumo.csv,
  eventos_deputado_tipo.csv, eventos_deputado_resumo.csv
Rodar com: python scripts\08b_agregar_despesas_eventos.py
"""
from pathlib import Path

import pandas as pd

RAIZ = Path(__file__).resolve().parent.parent
BRUTOS = RAIZ / "dados" / "brutos"
SAIDA = RAIZ / "dados" / "processados"
SAIDA.mkdir(parents=True, exist_ok=True)
pd.set_option("display.width", 200)


def ler(caminho):
    for codificacao in ("utf-8-sig", "latin-1"):
        try:
            return pd.read_csv(caminho, sep=";", dtype=str, encoding=codificacao,
                               compression="zip" if str(caminho).endswith(".zip") else None)
        except UnicodeDecodeError:
            continue


deputados = pd.read_csv(BRUTOS / "deputados_leg57.csv", dtype=str)
ids_leg57 = set(deputados["id"])
uf_deputado = deputados.drop_duplicates("id").set_index("id")["siglaUf"]

# ======================= DESPESAS =======================
desp = pd.concat([ler(f) for f in sorted((BRUTOS / "despesas").glob("Ano-*.csv.zip"))], ignore_index=True)
print(f"Despesas: {len(desp)} registros no total")
desp["valor"] = pd.to_numeric(desp["vlrLiquido"], errors="coerce").fillna(0)
desp["mes"] = desp["numAno"] + "-" + desp["numMes"].str.zfill(2)

sem_id = desp["ideCadastro"].isna()
print(f"  sem ideCadastro (lideranças etc.): {sem_id.sum()} registros, "
      f"R$ {desp.loc[sem_id, 'valor'].sum():,.0f}")
desp = desp[desp["ideCadastro"].isin(ids_leg57)].rename(columns={"ideCadastro": "idDeputado"})
print(f"  de deputados da 57ª legislatura: {len(desp)} registros, "
      f"{desp['idDeputado'].nunique()} deputados")
print("  total por ano (R$):", desp.groupby("numAno")["valor"].sum().round(0).to_dict())

por_categoria = (desp.groupby(["idDeputado", "txtDescricao"])
                 .agg(valor_total=("valor", "sum"), n_documentos=("valor", "size"))
                 .reset_index().rename(columns={"txtDescricao": "categoria"}))
por_categoria["valor_total"] = por_categoria["valor_total"].round(2)
por_categoria.to_csv(SAIDA / "despesas_deputado_categoria.csv", index=False, encoding="utf-8-sig")

resumo_desp = desp.groupby("idDeputado").agg(valor_total=("valor", "sum"), meses_com_despesa=("mes", "nunique"))
resumo_desp["gasto_mensal"] = (resumo_desp["valor_total"] / resumo_desp["meses_com_despesa"]).round(2)
resumo_desp["siglaUf"] = uf_deputado
resumo_desp["indice_gasto_uf"] = (resumo_desp["gasto_mensal"]
                                  / resumo_desp.groupby("siglaUf")["gasto_mensal"].transform("median")).round(3)
resumo_desp["categoria_principal"] = (por_categoria.sort_values("valor_total")
                                      .groupby("idDeputado")["categoria"].last())
resumo_desp["valor_total"] = resumo_desp["valor_total"].round(2)
resumo_desp.to_csv(SAIDA / "despesas_deputado_resumo.csv", encoding="utf-8-sig")

print("\n== Categorias de despesa (R$ total 2023-2026) ==")
print(por_categoria.groupby("categoria")["valor_total"].sum().sort_values(ascending=False)
      .map("{:,.0f}".format).to_string())

# ======================= EVENTOS =======================
eventos = pd.concat([ler(f) for f in sorted((BRUTOS / "eventos").glob("eventos-*.csv"))], ignore_index=True)
eventos = eventos.drop_duplicates("id")[["id", "descricaoTipo", "situacao"]]
presenca = pd.concat([ler(f) for f in sorted((BRUTOS / "eventos").glob("eventosPresencaDeputados-*.csv"))],
                     ignore_index=True).drop_duplicates(["idEvento", "idDeputado"])
print(f"\nEventos: {len(eventos)} | registros de presença: {len(presenca)}")

presenca = presenca.merge(eventos, left_on="idEvento", right_on="id", how="left")
print(f"  presenças sem evento correspondente: {presenca['descricaoTipo'].isna().sum()}")
presenca = presenca[presenca["idDeputado"].isin(ids_leg57)]
presenca["mes"] = presenca["dataHoraInicio"].str[:7]
print(f"  presenças de deputados da 57ª legislatura: {len(presenca)}, "
      f"{presenca['idDeputado'].nunique()} deputados")
print("\n== Tipos de evento (nº de presenças) ==")
print(presenca["descricaoTipo"].value_counts().to_string())

por_tipo = (presenca.groupby(["idDeputado", "descricaoTipo"]).size()
            .rename("n_eventos").reset_index().rename(columns={"descricaoTipo": "tipoEvento"}))
por_tipo.to_csv(SAIDA / "eventos_deputado_tipo.csv", index=False, encoding="utf-8-sig")

resumo_ev = presenca.groupby("idDeputado").agg(n_eventos=("idEvento", "nunique"), meses_ativos=("mes", "nunique"))
resumo_ev["eventos_por_mes"] = (resumo_ev["n_eventos"] / resumo_ev["meses_ativos"]).round(2)
resumo_ev.to_csv(SAIDA / "eventos_deputado_resumo.csv", encoding="utf-8-sig")

# ======================= PRÉVIA DA PERGUNTA 5 =======================
votos = pd.read_csv(BRUTOS / "6x1_votos.csv", dtype=str)
turno1 = votos[(votos["idVotacao"] == "2233802-424") & votos["tipoVoto"].isin(["Sim", "Não"])]
juntos = turno1.set_index("idDeputado")[["tipoVoto"]].join(resumo_desp).join(resumo_ev)
print("\n== Prévia da pergunta 5: 1º turno da PEC 6x1 (medianas) ==")
print(juntos.groupby("tipoVoto")[["gasto_mensal", "indice_gasto_uf", "eventos_por_mes"]]
      .median().round(2).assign(n_deputados=juntos["tipoVoto"].value_counts()).to_string())
print(f"  votantes sem dados de despesa: {juntos['gasto_mensal'].isna().sum()} | "
      f"sem dados de eventos: {juntos['eventos_por_mes'].isna().sum()}")

print(f"\nArquivos salvos em {SAIDA}")