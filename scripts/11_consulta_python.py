"""
Passo 7 - Consulta ao grafo pelo Python (aula "Administração": conexão Neo4j com Python).

A importação (script 10) já usa o driver para ESCREVER no banco. Este script mostra
a LEITURA: recebe o nome (ou parte do nome) de um deputado e devolve o perfil dele
no grafo, usando parâmetros ($nome) em vez de montar a consulta com texto,
o que evita erros e injeção de código.

Rodar com: python scripts\11_consulta_python.py
"""
from getpass import getpass

from neo4j import GraphDatabase

URI = "neo4j://localhost:7687"
USUARIO = "neo4j"
BANCO = "neo4j"

CONSULTA = """
MATCH (d:Deputado)-[:REPRESENTA]->(u:UF)
WHERE toLower(d.nome) CONTAINS toLower($nome) AND d.legislatura57
OPTIONAL MATCH (d)-[:MEMBRO_DE]->(f:Frente)
WITH d, u, collect(f.tema) AS frentes
OPTIONAL MATCH (d)-[v:VOTOU]->(vt:Votacao {tema: '6x1'})
WHERE vt.id = '2233802-424'
RETURN d.nome AS nome, d.partidoRecente AS partido, u.sigla AS uf,
       u.exposicao AS exposicao_climatica_uf, d.indiceAmbiental AS indice_ambiental,
       v.voto AS voto_6x1_1turno, frentes,
       d.indiceGastoUf AS indice_gasto_uf, d.eventosComissoesPorMes AS eventos_comissoes_mes
ORDER BY nome
"""

senha = getpass("Senha do banco Neo4j: ")
with GraphDatabase.driver(URI, auth=(USUARIO, senha)) as driver:
    driver.verify_connectivity()
    while True:
        nome = input("\nNome (ou parte) do deputado - Enter vazio para sair: ").strip()
        if not nome:
            break
        registros = driver.execute_query(CONSULTA, nome=nome, database_=BANCO).records
        if not registros:
            print("  Nenhum deputado encontrado.")
        for r in registros:
            print(f"\n  {r['nome']} ({r['partido']}-{r['uf']})")
            print(f"    exposição climática da UF: {r['exposicao_climatica_uf']}")
            print(f"    índice ambiental: {r['indice_ambiental']}% de votos pró-ambiente")
            print(f"    voto no 1º turno da PEC 6x1: {r['voto_6x1_1turno'] or 'não votou'}")
            print(f"    frentes temáticas: {', '.join(r['frentes']) or 'nenhuma'}")
            print(f"    índice de gasto (UF = 1,0): {r['indice_gasto_uf']}"
                  f" | eventos de comissão por mês: {r['eventos_comissoes_mes']}")