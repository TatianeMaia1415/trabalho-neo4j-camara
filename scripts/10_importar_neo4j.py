"""
Passo 4 - Importação no Neo4j via driver Python (biblioteca neo4j).

Lê os CSVs de dados/processados/neo4j/ e envia os dados em lotes para o Neo4j,
onde comandos Cypher (UNWIND + MERGE) criam os nós e relacionamentos.
MERGE torna a importação repetível: rodar de novo não duplica nada.

Antes de rodar: o banco do Neo4j Desktop precisa estar ligado (Start/Running).
Rodar com: python scripts\10_importar_neo4j.py
"""
import time
from getpass import getpass
from pathlib import Path

import pandas as pd
from neo4j import GraphDatabase

URI = "neo4j://localhost:7687"   # endereço padrão do Neo4j Desktop
USUARIO = "neo4j"
BANCO = "neo4j"                  # banco padrão
LOTE = 1000
PASTA = Path(__file__).resolve().parent.parent / "dados" / "processados" / "neo4j"

RESTRICOES = [
    "CREATE CONSTRAINT deputado_id IF NOT EXISTS FOR (n:Deputado) REQUIRE n.id IS UNIQUE",
    "CREATE CONSTRAINT partido_sigla IF NOT EXISTS FOR (n:Partido) REQUIRE n.sigla IS UNIQUE",
    "CREATE CONSTRAINT uf_sigla IF NOT EXISTS FOR (n:UF) REQUIRE n.sigla IS UNIQUE",
    "CREATE CONSTRAINT frente_id IF NOT EXISTS FOR (n:Frente) REQUIRE n.id IS UNIQUE",
    "CREATE CONSTRAINT votacao_id IF NOT EXISTS FOR (n:Votacao) REQUIRE n.id IS UNIQUE",
    "CREATE CONSTRAINT proposicao_id IF NOT EXISTS FOR (n:Proposicao) REQUIRE n.id IS UNIQUE",
]

# (arquivo, comando Cypher). Cada linha do CSV chega como "l" pelo UNWIND.
CARGAS = [
    # ---------------- NÓS ----------------
    ("partidos.csv", """
        UNWIND $rows AS l
        MERGE (p:Partido {sigla: l.sigla})
        SET p.nome = l.nome"""),
    ("ufs.csv", """
        UNWIND $rows AS l
        MERGE (u:UF {sigla: l.sigla})
        SET u.regiao = l.regiao, u.exposicao = l.exposicao,
            u.registrosPorMunicipio = toFloat(l.registros_por_municipio),
            u.pctMunicipiosAfetados = toFloat(l.pct_municipios_afetados),
            u.nRegistros = toInteger(toFloat(l.n_registros)), u.mortos = toInteger(toFloat(l.mortos)),
            u.desabrigados = toInteger(toFloat(l.desabrigados)),
            u.tipoMaisFrequente = l.tipo_mais_frequente"""),
    ("frentes.csv", """
        UNWIND $rows AS l
        MERGE (f:Frente {id: l.id})
        SET f.titulo = l.titulo, f.tema = l.tema, f.nMembros = toInteger(l.n_membros)"""),
    ("proposicoes.csv", """
        UNWIND $rows AS l
        MERGE (p:Proposicao {id: l.id})
        SET p.rotulo = l.rotulo, p.siglaTipo = l.siglaTipo, p.numero = toInteger(l.numero),
            p.ano = toInteger(l.ano), p.ementa = l.ementa, p.situacao = l.situacao,
            p.autorExterno = l.autorExterno"""),
    ("votacoes.csv", """
        UNWIND $rows AS l
        MERGE (v:Votacao {id: l.idVotacao})
        SET v.data = date(l.data), v.tema = l.tema, v.simSignifica = l.sim_significa,
            v.tipoVotacao = l.tipo_votacao, v.proposicao = l.proposicao,
            v.sim = toInteger(l.sim), v.nao = toInteger(l.nao), v.descricao = l.descricao"""),
    ("deputados.csv", """
        UNWIND $rows AS l
        MERGE (d:Deputado {id: l.id})
        SET d.nome = l.nome, d.siglaUf = l.siglaUf, d.partidoRecente = l.partidoRecente,
            d.legislatura57 = (l.legislatura57 = 'true'),
            d.valorTotalDespesas = toFloat(l.valor_total), d.gastoMensal = toFloat(l.gasto_mensal),
            d.indiceGastoUf = toFloat(l.indice_gasto_uf), d.categoriaPrincipal = l.categoria_principal,
            d.nEventos = toInteger(l.n_eventos), d.eventosPorMes = toFloat(l.eventos_por_mes),
            d.eventosComissoesPorMes = toFloat(l.eventos_comissoes_por_mes)"""),
    # ---------------- RELACIONAMENTOS ----------------
    ("rel_representa.csv", """
        UNWIND $rows AS l
        MATCH (d:Deputado {id: l.idDeputado}), (u:UF {sigla: l.siglaUf})
        MERGE (d)-[:REPRESENTA]->(u)"""),
    ("rel_filiado_a.csv", """
        UNWIND $rows AS l
        MATCH (d:Deputado {id: l.idDeputado}), (p:Partido {sigla: l.siglaPartido})
        MERGE (d)-[:FILIADO_A]->(p)"""),
    ("rel_membro_de.csv", """
        UNWIND $rows AS l
        MATCH (d:Deputado {id: l.idDeputado}), (f:Frente {id: l.idFrente})
        MERGE (d)-[r:MEMBRO_DE]->(f)
        SET r.papel = l.papel"""),
    ("rel_sobre.csv", """
        UNWIND $rows AS l
        MATCH (v:Votacao {id: l.idVotacao}), (p:Proposicao {id: l.idProposicao})
        MERGE (v)-[:SOBRE]->(p)"""),
    ("rel_autor_de.csv", """
        UNWIND $rows AS l
        MATCH (d:Deputado {id: l.idDeputado}), (p:Proposicao {id: l.idProposicao})
        MERGE (d)-[r:AUTOR_DE]->(p)
        SET r.ordemAssinatura = toInteger(l.ordemAssinatura),
            r.proponente = (l.proponente IN ['1', 'True', 'true'])"""),
    ("rel_orientou.csv", """
        UNWIND $rows AS l
        MATCH (p:Partido {sigla: l.siglaPartido}), (v:Votacao {id: l.idVotacao})
        MERGE (p)-[r:ORIENTOU]->(v)
        SET r.orientacao = l.orientacao"""),
    ("rel_votou.csv", """
        UNWIND $rows AS l
        MATCH (d:Deputado {id: l.idDeputado}), (v:Votacao {id: l.idVotacao})
        MERGE (d)-[r:VOTOU]->(v)
        SET r.voto = l.voto, r.partido = l.partido, r.uf = l.uf"""),
]


def linhas(arquivo):
    """Lê o CSV como texto e troca vazios por None (que vira null no Neo4j)."""
    df = pd.read_csv(PASTA / arquivo, dtype=str, encoding="utf-8")
    return df.astype(object).where(df.notna(), None).to_dict("records")


senha = getpass("Senha do banco Neo4j (não aparece enquanto você digita): ")
inicio = time.time()
with GraphDatabase.driver(URI, auth=(USUARIO, senha)) as driver:
    driver.verify_connectivity()
    print("Conectado ao Neo4j.")

    existentes = driver.execute_query("MATCH (n) RETURN count(n) AS n", database_=BANCO).records[0]["n"]
    if existentes:
        resposta = input(f"O banco já tem {existentes} nós. Apagar tudo e importar do zero? (s/n) ")
        if resposta.strip().lower() == "s":
            driver.execute_query("MATCH (n) DETACH DELETE n", database_=BANCO)
            print("Banco limpo.")

    for comando in RESTRICOES:
        driver.execute_query(comando, database_=BANCO)
    print(f"Restrições de unicidade criadas: {len(RESTRICOES)}")

    for arquivo, cypher in CARGAS:
        dados = linhas(arquivo)
        for i in range(0, len(dados), LOTE):
            driver.execute_query(cypher, rows=dados[i:i + LOTE], database_=BANCO)
        print(f"  {arquivo:<22} {len(dados):>6} linhas enviadas")

    # Validação: o que ficou no banco
    print("\n== Conferência no Neo4j ==")
    for r in driver.execute_query("MATCH (n) RETURN labels(n)[0] AS tipo, count(*) AS total ORDER BY tipo",
                                  database_=BANCO).records:
        print(f"  nó {r['tipo']:<12} {r['total']:>6}")
    for r in driver.execute_query("MATCH ()-[r]->() RETURN type(r) AS tipo, count(*) AS total ORDER BY tipo",
                                  database_=BANCO).records:
        print(f"  rel {r['tipo']:<11} {r['total']:>6}")

print(f"\nImportação concluída em {time.time() - inicio:.0f}s.")