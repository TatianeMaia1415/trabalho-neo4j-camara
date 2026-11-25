"""
Passo 1.5b - Agregar os desastres CLIMÁTICOS (2023-2025) do Atlas Digital por UF.

Critérios:
  - período: 2023 a 2025 (pela Data_Evento; o Atlas ainda não tem 2026)
  - grupos climáticos: Climatológico, Hidrológico e Meteorológico ("Outros" sai: inclui doenças etc.)
  - indicador principal: % dos municípios da UF com pelo menos 1 desastre climático
    (contar registros favoreceria UFs com muitos municípios, como MG e RS)

Gera em dados/processados/:
  desastres_uf_resumo.csv    -> 1 linha por UF
  desastres_uf_tipo_ano.csv  -> 1 linha por UF + ano + tipo de desastre (para o grafo)
Rodar com: python scripts\07b_agregar_desastres_uf.py
"""
from pathlib import Path

import pandas as pd

RAIZ = Path(__file__).resolve().parent.parent
ARQUIVO = next((RAIZ / "dados" / "brutos" / "desastres").glob("BD_Atlas*.csv"))
SAIDA = RAIZ / "dados" / "processados"
SAIDA.mkdir(parents=True, exist_ok=True)

ANOS = [2023, 2024, 2025]
GRUPOS_CLIMATICOS = ["Climatológico", "Hidrológico", "Meteorológico"]

# Número oficial de municípios por UF (IBGE, inclui DF e Fernando de Noronha = 5.571)
MUNICIPIOS_UF = {
    "AC": 22, "AL": 102, "AP": 16, "AM": 62, "BA": 417, "CE": 184, "DF": 1, "ES": 78,
    "GO": 246, "MA": 217, "MT": 142, "MS": 79, "MG": 853, "PA": 144, "PB": 223, "PR": 399,
    "PE": 185, "PI": 224, "RJ": 92, "RN": 167, "RS": 497, "RO": 52, "RR": 15, "SC": 295,
    "SP": 645, "SE": 75, "TO": 139,
}

df = pd.read_csv(ARQUIVO, sep=";", dtype=str, encoding="latin-1")
print(f"Base completa: {len(df)} registros (1991-2025)")

# Conferências antes de filtrar
print("\nStatus dos registros:", df["Status"].value_counts(dropna=False).to_dict())
fora = df[~df["Sigla_UF"].isin(MUNICIPIOS_UF)]["Sigla_UF"].value_counts(dropna=False)
print("UFs fora da lista oficial:", fora.to_dict() if len(fora) else "nenhuma")
# Correção de qualidade: 6 registros vieram com "pa" minúsculo -> padroniza para maiúsculas
df["Sigla_UF"] = df["Sigla_UF"].str.strip().str.upper()
fora = df[~df["Sigla_UF"].isin(MUNICIPIOS_UF)]["Sigla_UF"].value_counts(dropna=False)
print("UFs fora da lista após padronizar maiúsculas:", fora.to_dict() if len(fora) else "nenhuma")
print("Grupo 'Outros' contém:", df[df["grupo_de_desastre"] == "Outros"]["descricao_tipologia"]
      .value_counts().to_dict())

# Filtros: período e grupos climáticos
df["ano"] = pd.to_datetime(df["Data_Evento"], format="%d/%m/%Y", errors="coerce").dt.year
clima = df[df["ano"].isin(ANOS) & df["grupo_de_desastre"].isin(GRUPOS_CLIMATICOS)
           & df["Sigla_UF"].isin(MUNICIPIOS_UF)].copy()
print(f"\nDesastres climáticos 2023-2025: {len(clima)} registros "
      f"({clima['Cod_IBGE_Mun'].nunique()} municípios distintos)")
print("Por ano:", clima["ano"].value_counts().sort_index().to_dict())

NUMERICAS = {
    "DH_MORTOS": "mortos", "DH_DESABRIGADOS": "desabrigados", "DH_DESALOJADOS": "desalojados",
    "DH_total_danos_humanos_diretos": "afetados_diretos", "PE_PLePR": "prejuizo_reais",
}
for col in NUMERICAS:
    clima[col] = pd.to_numeric(clima[col], errors="coerce").fillna(0)

# 1) Resumo por UF
resumo = (clima.groupby("Sigla_UF")
          .agg(n_registros=("Protocolo_S2iD", "count"),
               municipios_afetados=("Cod_IBGE_Mun", "nunique"),
               **{novo: (col, "sum") for col, novo in NUMERICAS.items()})
          .reindex(MUNICIPIOS_UF.keys(), fill_value=0))   # UFs sem desastre entram com zero
resumo["total_municipios"] = pd.Series(MUNICIPIOS_UF)
resumo["pct_municipios_afetados"] = (100 * resumo["municipios_afetados"]
                                     / resumo["total_municipios"]).round(1)
resumo["registros_por_municipio"] = (resumo["n_registros"] / resumo["total_municipios"]).round(2)
resumo["tipo_mais_frequente"] = clima.groupby("Sigla_UF")["descricao_tipologia"] \
    .agg(lambda s: s.value_counts().index[0])
# Exposição climática em 3 faixas (tercis) pela intensidade = registros por município.
# O % de municípios afetados "satura" em 100% em várias UFs, por isso não serve para separar grupos.
resumo["exposicao"] = pd.qcut(resumo["registros_por_municipio"].rank(method="first"), 3,
                              labels=["baixa", "media", "alta"])
resumo = resumo.sort_values("registros_por_municipio", ascending=False)
resumo.index.name = "siglaUf"
resumo.to_csv(SAIDA / "desastres_uf_resumo.csv", encoding="utf-8-sig")

# 2) Detalhe por UF + ano + tipo (para o grafo)
detalhe = (clima.groupby(["Sigla_UF", "ano", "grupo_de_desastre", "descricao_tipologia"])
           .agg(n_registros=("Protocolo_S2iD", "count"),
                municipios_afetados=("Cod_IBGE_Mun", "nunique"),
                **{novo: (col, "sum") for col, novo in NUMERICAS.items()})
           .reset_index()
           .rename(columns={"Sigla_UF": "siglaUf", "grupo_de_desastre": "grupo",
                            "descricao_tipologia": "tipo"}))
detalhe.to_csv(SAIDA / "desastres_uf_tipo_ano.csv", index=False, encoding="utf-8-sig")

# 3) Mostrar
pd.set_option("display.width", 200)
colunas = ["exposicao", "registros_por_municipio", "pct_municipios_afetados", "n_registros",
           "mortos", "desabrigados", "tipo_mais_frequente"]
print("\n== UFs por intensidade de desastres climáticos (registros por município, 2023-2025) ==")
print(resumo[colunas].to_string())

# 4) Validação com um fato conhecido: enchentes do RS em 2024
rs24 = clima[(clima["Sigla_UF"] == "RS") & (clima["ano"] == 2024)]
print(f"\nValidação - RS em 2024: {len(rs24)} registros, {int(rs24['DH_MORTOS'].sum())} mortos, "
      f"{int(rs24['DH_DESABRIGADOS'].sum())} desabrigados")

print(f"\nArquivos salvos em {SAIDA}")
print(f"  desastres_uf_resumo.csv: {len(resumo)} UFs | desastres_uf_tipo_ano.csv: {len(detalhe)} linhas")