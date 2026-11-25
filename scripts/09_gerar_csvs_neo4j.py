"""
Passo 3 - Transformar os dados brutos/processados nos CSVs de NÓS e RELACIONAMENTOS do Neo4j.

Modelo simplificado (6 nós, 7 relacionamentos):
  (:Deputado)-[:VOTOU {voto, partido, uf}]->(:Votacao)-[:SOBRE]->(:Proposicao)
  (:Deputado)-[:FILIADO_A]->(:Partido)-[:ORIENTOU {orientacao}]->(:Votacao)
  (:Deputado)-[:REPRESENTA]->(:UF)            UF guarda os indicadores de desastres (pergunta 1)
  (:Deputado)-[:MEMBRO_DE {papel}]->(:Frente)  só as 8 frentes temáticas (pergunta 3)
  (:Deputado)-[:AUTOR_DE]->(:Proposicao)
  Despesas e eventos viram propriedades do Deputado (pergunta 5).

Gera os CSVs em dados/processados/neo4j/ (UTF-8 sem BOM, que é o que o LOAD CSV espera).
Rodar com: python scripts\09_gerar_csvs_neo4j.py
"""
from pathlib import Path

import pandas as pd

RAIZ = Path(__file__).resolve().parent.parent
BRUTOS = RAIZ / "dados" / "brutos"
PROC = RAIZ / "dados" / "processados"
SAIDA = PROC / "neo4j"
SAIDA.mkdir(parents=True, exist_ok=True)


def ler(pasta, nome):
    df = pd.read_csv(pasta / nome, dtype=str, encoding="utf-8-sig")
    # IDs salvos como número decimal viram "204379.0" quando a coluna tem algum vazio;
    # padroniza para "204379" para os IDs baterem entre os arquivos.
    for col in df.columns:
        if col.lower().startswith("id"):
            df[col] = df[col].str.replace(r"\.0$", "", regex=True)
    return df


def salvar(df, nome):
    df.to_csv(SAIDA / nome, index=False, encoding="utf-8")
    print(f"  {nome:<22} {len(df):>6} linhas")
    return df


# Frentes temáticas escolhidas para a pergunta 3
FRENTES = {
    "54323": "agro",                 # Frente Parlamentar da Agropecuária - FPA
    "54406": "ambiental",            # Frente Parlamentar Mista Ambientalista
    "54318": "indigena",             # Defesa dos Direitos dos Povos Indígenas
    "54542": "agroecologia",         # Agroecologia e Produção Orgânica
    "54343": "agricultura_familiar", # Agricultura Familiar e Desenvolvimento Rural Sustentável
    "54486": "mineracao",            # Mineração e Construção Civil
    "54563": "petroleo",             # Petróleo, Gás e Energia - FREPPEGEN
    "54558": "sustentabilidade",     # Objetivos de Desenvolvimento Sustentável da ONU
}
# Polaridade das 4 votações nominais da PEC 221/2019 (definida no passo 1.1b)
VOTACOES_6X1 = {
    "2233802-401": ("A_FAVOR_FIM_6X1", "parecer na comissão especial"),
    "2233802-416": ("CONDUCAO_BASE", "requerimento procedimental"),
    "2233802-424": ("A_FAVOR_FIM_6X1", "1º turno"),
    "2233802-438": ("A_FAVOR_FIM_6X1", "2º turno"),
}
REGIAO = {"AC": "Norte", "AM": "Norte", "AP": "Norte", "PA": "Norte", "RO": "Norte", "RR": "Norte",
          "TO": "Norte", "AL": "Nordeste", "BA": "Nordeste", "CE": "Nordeste", "MA": "Nordeste",
          "PB": "Nordeste", "PE": "Nordeste", "PI": "Nordeste", "RN": "Nordeste", "SE": "Nordeste",
          "DF": "Centro-Oeste", "GO": "Centro-Oeste", "MS": "Centro-Oeste", "MT": "Centro-Oeste",
          "ES": "Sudeste", "MG": "Sudeste", "RJ": "Sudeste", "SP": "Sudeste",
          "PR": "Sul", "RS": "Sul", "SC": "Sul"}

# ---------------- leitura ----------------
deps = ler(BRUTOS, "deputados_leg57.csv")
partidos = ler(BRUTOS, "partidos_leg57.csv")
votos = pd.concat([ler(BRUTOS, "6x1_votos.csv"), ler(BRUTOS, "ambiente_votos.csv")], ignore_index=True)
orient = pd.concat([ler(BRUTOS, "6x1_orientacoes.csv"), ler(BRUTOS, "ambiente_orientacoes.csv")],
                   ignore_index=True)
props = ler(BRUTOS, "proposicoes.csv")
autores = ler(BRUTOS, "proposicoes_autores.csv")
ligacoes = ler(BRUTOS, "votacoes_proposicoes_selecionadas.csv")
polaridade = ler(BRUTOS, "ambiente_polaridade.csv")
resumo_6x1 = ler(BRUTOS, "6x1_votacoes_resumo.csv")
frentes = ler(BRUTOS, "frentes_leg57.csv")
membros = ler(BRUTOS, "frentes_membros.csv")
desastres = ler(PROC, "desastres_uf_resumo.csv")
despesas = ler(PROC, "despesas_deputado_resumo.csv")
ev_tipo = ler(PROC, "eventos_deputado_tipo.csv")
ev_resumo = ler(PROC, "eventos_deputado_resumo.csv")

ids_leg57 = set(deps["id"])
print("Gerando CSVs do Neo4j:\n-- nós --")

# ---------------- NÓS ----------------
# Votacao
v6 = resumo_6x1[resumo_6x1["idVotacao"].isin(VOTACOES_6X1)].copy()
v6["tema"] = "6x1"
v6["sim_significa"] = v6["idVotacao"].map(lambda i: VOTACOES_6X1[i][0])
v6["tipo_votacao"] = v6["idVotacao"].map(lambda i: VOTACOES_6X1[i][1])
v6["proposicao"] = "PEC 221/2019"
vamb = polaridade.copy()
vamb["tema"] = "ambiental"
vamb = vamb.rename(columns={"justificativa": "descricao"})
cols_vot = ["idVotacao", "data", "tema", "sim_significa", "tipo_votacao", "proposicao", "sim", "nao", "descricao"]
votacoes = salvar(pd.concat([v6[cols_vot], vamb[cols_vot]], ignore_index=True), "votacoes.csv")

# Proposicao (autores externos -> propriedade, pois não são deputados)
externos = (autores[autores["idDeputado"].isna()].groupby("idProposicao")["nome"]
            .agg("; ".join).rename("autorExterno"))
props["rotulo"] = props["siglaTipo"] + " " + props["numero"] + "/" + props["ano"]
props = props.join(externos, on="id")
salvar(props[["id", "rotulo", "siglaTipo", "numero", "ano", "ementa", "situacao", "autorExterno"]],
       "proposicoes.csv")

# Partido (inclui siglas antigas que aparecem nos votos, ex.: partidos que se fundiram)
siglas = set(partidos["sigla"]) | set(deps["siglaPartido"]) | set(votos["siglaPartido"].dropna())
extras = sorted(siglas - set(partidos["sigla"]))
partidos_no = pd.concat([partidos[["sigla", "nome"]],
                         pd.DataFrame({"sigla": extras, "nome": None})], ignore_index=True)
salvar(partidos_no, "partidos.csv")
if extras:
    print(f"     (siglas sem cadastro na API, incluídas sem nome: {extras})")

# UF (com indicadores de desastres climáticos 2023-2025)
ufs = desastres.rename(columns={"siglaUf": "sigla"})
ufs["regiao"] = ufs["sigla"].map(REGIAO)
salvar(ufs[["sigla", "regiao", "exposicao", "registros_por_municipio", "pct_municipios_afetados",
            "n_registros", "mortos", "desabrigados", "tipo_mais_frequente"]], "ufs.csv")

# Frente (só as temáticas)
fr = frentes[frentes["id"].isin(FRENTES)].copy()
faltando = set(FRENTES) - set(fr["id"])
assert not faltando, f"Frentes não encontradas: {faltando}"
fr["tema"] = fr["id"].map(FRENTES)
membros_sel = membros[membros["idFrente"].isin(FRENTES) & membros["idDeputado"].isin(ids_leg57)]
if membros_sel.empty:   # diagnóstico, caso os IDs ainda não batam
    print("  ! nenhum membro encontrado. Exemplos de IDs em frentes_membros.csv:",
          membros[["idFrente", "idDeputado"]].head(3).to_dict("records"),
          "| exemplo de ID de deputado:", next(iter(ids_leg57)))
fr["n_membros"] = fr["id"].map(membros_sel.groupby("idFrente").size()).fillna(0).astype(int)
salvar(fr[["id", "titulo", "tema", "n_membros"]], "frentes.csv")

# Deputado: dados básicos + despesas + eventos (pergunta 5)
votos["dataRegistroVoto"] = votos["dataRegistroVoto"].fillna("")
partido_recente = (votos.sort_values("dataRegistroVoto").groupby("idDeputado")["siglaPartido"].last())
dep = deps.drop_duplicates("id")[["id", "nome", "siglaUf"]].copy()
dep["partidoRecente"] = dep["id"].map(partido_recente).fillna(
    dep["id"].map(deps.groupby("id")["siglaPartido"].last()))
dep["legislatura57"] = "true"
dep = dep.merge(despesas[["idDeputado", "valor_total", "gasto_mensal", "indice_gasto_uf",
                          "categoria_principal"]], left_on="id", right_on="idDeputado", how="left")

ev = ev_tipo[ev_tipo["tipoEvento"] != "Teste do Painel Eletrônico"].copy()   # não é participação real
ev["n_eventos"] = ev["n_eventos"].astype(int)
plenario = ev["tipoEvento"].isin(["Sessão Deliberativa", "Sessão Preparatória - Eleição"])
ev_total = ev.groupby("idDeputado")["n_eventos"].sum()
ev_comissoes = ev[~plenario].groupby("idDeputado")["n_eventos"].sum()
meses = ev_resumo.set_index("idDeputado")["meses_ativos"].astype(int)
dep["n_eventos"] = dep["id"].map(ev_total).fillna(0).astype(int)
dep["eventos_por_mes"] = (dep["n_eventos"] / dep["id"].map(meses)).round(2)
dep["eventos_comissoes_por_mes"] = (dep["id"].map(ev_comissoes).fillna(0) / dep["id"].map(meses)).round(2)

# Autores de proposições que não são da 57ª legislatura (ex.: autores do PL 490/2007)
aut_dep = autores[autores["idDeputado"].notna()]
antigos = aut_dep[~aut_dep["idDeputado"].isin(ids_leg57)].drop_duplicates("idDeputado")
antigos = pd.DataFrame({"id": antigos["idDeputado"], "nome": antigos["nome"], "legislatura57": "false"})
dep = pd.concat([dep.drop(columns="idDeputado"), antigos], ignore_index=True)
dep["n_eventos"] = dep["n_eventos"].astype("Int64")   # mantém inteiro (sem ".0") mesmo com vazios
salvar(dep, "deputados.csv")
print(f"     ({len(antigos)} autores de outras legislaturas incluídos com legislatura57=false)")

# ---------------- RELACIONAMENTOS ----------------
print("-- relacionamentos --")
votou = votos.rename(columns={"siglaPartido": "partido", "siglaUf": "uf", "tipoVoto": "voto"})
salvar(votou[["idDeputado", "idVotacao", "voto", "partido", "uf"]].drop_duplicates(["idDeputado", "idVotacao"]),
       "rel_votou.csv")
salvar(ligacoes.rename(columns={"proposicao_id": "idProposicao"})[["idVotacao", "idProposicao"]]
       [lambda d: d["idVotacao"].isin(votacoes["idVotacao"])], "rel_sobre.csv")
salvar(deps[["id", "siglaPartido"]].drop_duplicates().rename(columns={"id": "idDeputado"}), "rel_filiado_a.csv")
salvar(deps[["id", "siglaUf"]].drop_duplicates("id").rename(columns={"id": "idDeputado"}), "rel_representa.csv")
salvar(membros_sel[["idDeputado", "idFrente", "papel"]].drop_duplicates(["idDeputado", "idFrente"]),
       "rel_membro_de.csv")
salvar(aut_dep[["idDeputado", "idProposicao", "ordemAssinatura", "proponente"]], "rel_autor_de.csv")

# ORIENTOU: só partidos; federações ("Fdr PT-PCdoB-PV") valem para cada partido membro;
# blocos, Governo, Maioria, Minoria e Oposição não são partidos e ficam de fora.
mapa_siglas = {s.upper(): s for s in partidos_no["sigla"]}
linhas, ignoradas = [], set()
for _, o in orient.iterrows():
    nome = str(o["siglaPartidoBloco"]).strip()
    candidatas = nome[4:].split("-") if nome.startswith("Fdr ") else [nome]
    achou = False
    for c in candidatas:
        if c.strip().upper() in mapa_siglas:
            linhas.append({"siglaPartido": mapa_siglas[c.strip().upper()], "idVotacao": o["idVotacao"],
                           "orientacao": o["orientacaoVoto"]})
            achou = True
    if not achou:
        ignoradas.add(nome)
salvar(pd.DataFrame(linhas).drop_duplicates(["siglaPartido", "idVotacao"]), "rel_orientou.csv")
print(f"     (orientações ignoradas por não serem partido: {sorted(ignoradas)})")

# ---------------- VALIDAÇÕES ----------------
print("\n-- validações --")
ids_dep = set(dep["id"])
print("  votos de deputados sem nó Deputado:", (~votou["idDeputado"].isin(ids_dep)).sum())
print("  votações sem proposição (SOBRE):",
      sorted(set(votacoes["idVotacao"]) - set(ligacoes["idVotacao"])) or "nenhuma")
print("  deputados da 57ª sem dados de despesa:", dep[dep["legislatura57"] == "true"]["gasto_mensal"].isna().sum())
print("  membros por frente:", fr.set_index("tema")["n_membros"].to_dict())
print(f"\nArquivos em {SAIDA}")