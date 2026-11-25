// =====================================================================
// Passo 5 - Validação da carga e visualizações para o PDF
// Rodar UMA consulta por vez na ferramenta Query do Neo4j Desktop
// =====================================================================


// ---------------------------------------------------------------------
// 5.1 VALIDAÇÃO com fatos publicados na imprensa (1º turno da PEC 6x1)
//     Esperado (noticiário): 22 votos "Não"; SC com 10, RS com 5, SP com 4
// ---------------------------------------------------------------------
MATCH (:Deputado)-[v:VOTOU]->(:Votacao {id: '2233802-424'})
WHERE v.voto = 'Não'
RETURN v.uf AS uf, count(*) AS votos_contra
ORDER BY votos_contra DESC;

//     Esperado (noticiário): PL com 11 votos "Não" no 1º turno
MATCH (:Deputado)-[v:VOTOU]->(:Votacao {id: '2233802-424'})
WHERE v.voto = 'Não'
RETURN v.partido AS partido, count(*) AS votos_contra
ORDER BY votos_contra DESC;


// ---------------------------------------------------------------------
// 5.2 ESQUEMA do modelo (tipos de nó e relacionamento) - figura do item 3
// ---------------------------------------------------------------------
CALL db.schema.visualization();


// ---------------------------------------------------------------------
// 5.3 EXEMPLOS: 2 itens de cada tipo de nó e de relacionamento - item 3
//     Escolhe 2 deputados de UFs e partidos diferentes que sejam autores
//     e membros de frente, e traz 1 exemplo de cada relação para cada um.
// ---------------------------------------------------------------------
MATCH (d:Deputado)-[:AUTOR_DE]->()
WHERE d.legislatura57 AND EXISTS { (d)-[:MEMBRO_DE]->() }
WITH collect(DISTINCT d) AS deps
WITH deps[0] AS d1,
     [x IN deps WHERE x.siglaUf <> deps[0].siglaUf
                  AND x.partidoRecente <> deps[0].partidoRecente][0] AS d2
UNWIND [[d1, 0], [d2, 1]] AS par
WITH par[0] AS d, par[1] AS i
CALL (d, i) {
  MATCH p = (d)-[:REPRESENTA]->(:UF) RETURN p
  UNION
  MATCH p = (d)-[:FILIADO_A]->(:Partido) RETURN p LIMIT 1
  UNION
  MATCH p = (d)-[:MEMBRO_DE]->(f:Frente)
  WITH p, f ORDER BY CASE WHEN i = 0 THEN f.id END ASC, CASE WHEN i = 1 THEN f.id END DESC
  RETURN p LIMIT 1
  UNION
  MATCH p = (d)-[:AUTOR_DE]->(:Proposicao) RETURN p LIMIT 1
  UNION
  MATCH p = (d)-[:VOTOU]->(v:Votacao)-[:SOBRE]->(:Proposicao)
  WITH p, v ORDER BY CASE WHEN i = 0 THEN v.id END ASC, CASE WHEN i = 1 THEN v.id END DESC
  RETURN p LIMIT 1
  UNION
  MATCH p = (d)-[r:VOTOU]->(:Votacao)<-[:ORIENTOU]-(pa:Partido)
  WHERE pa.sigla = r.partido
  RETURN p LIMIT 1
}
RETURN p;


// ---------------------------------------------------------------------
// 5.4 TODOS OS DADOS em modo visual - item 4
//     (762 nós; se a tela mostrar menos, aumente o limite de exibição)
// ---------------------------------------------------------------------
MATCH (n)
OPTIONAL MATCH (n)-[r]->(m)
RETURN n, r, m;
