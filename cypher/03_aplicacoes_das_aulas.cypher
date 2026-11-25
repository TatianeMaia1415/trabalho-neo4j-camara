// =====================================================================
// Passo 7 - Aplicando conteúdos das aulas teóricas ao grafo do trabalho
// Rodar UM bloco por vez na ferramenta Query do Neo4j Desktop.
// =====================================================================


// ---------------------------------------------------------------------
// A. MÚLTIPLOS RÓTULOS (aula "Cypher A-Z": um nó pode ter mais de um rótulo)
//    Os 17 autores de outras legislaturas ganham o rótulo extra :AutorHistorico.
// ---------------------------------------------------------------------
MATCH (d:Deputado)
WHERE d.legislatura57 = false
SET d:AutorHistorico
RETURN count(d) AS autores_historicos;

// Conferência: os nós agora têm dois rótulos
MATCH (d:AutorHistorico)-[:AUTOR_DE]->(p:Proposicao)
RETURN labels(d) AS rotulos, d.nome AS autor, p.rotulo AS proposicao
ORDER BY proposicao;


// ---------------------------------------------------------------------
// B. PROPRIEDADE DERIVADA COM SET (aulas: SET cria/atualiza propriedades)
//    Calcula uma vez o índice ambiental de cada deputado (% de votos pró-ambiente)
//    e grava no nó, para ser reutilizado nas consultas e nos índices abaixo.
// ---------------------------------------------------------------------
MATCH (d:Deputado)-[v:VOTOU]->(vt:Votacao {tema: 'ambiental'})
WHERE v.voto IN ['Sim', 'Não', 'Obstrução']
WITH d, count(*) AS n,
     avg(CASE WHEN (v.voto = 'Sim') = (vt.simSignifica = 'PRO_AMBIENTE') THEN 1.0 ELSE 0.0 END) AS indice
SET d.indiceAmbiental = round(100 * indice, 1),
    d.nVotosAmbientais = n
RETURN count(d) AS deputados_atualizados;


// ---------------------------------------------------------------------
// C. ÍNDICES E PLANO DE EXECUÇÃO (aula "Administração": índices, EXPLAIN e PROFILE)
// ---------------------------------------------------------------------

// C.0 Índices já existentes: os 6 criados pelas restrições de unicidade da
//     importação + os 2 índices "token lookup" que o Neo4j cria sozinho
SHOW INDEXES;

// ---- C.1 TEXT INDEX: busca por parte do nome (CONTAINS) ----
// Antes do índice (tire print do plano: deve aparecer NodeByLabelScan + Filter)
PROFILE
MATCH (d:Deputado)
WHERE d.nome CONTAINS 'Zanatta'
RETURN d.nome, d.siglaUf, d.indiceAmbiental;

CREATE TEXT INDEX deputado_nome_texto IF NOT EXISTS FOR (d:Deputado) ON (d.nome);

CALL db.awaitIndexes();

// Depois do índice (deve aparecer NodeIndexContainsScan e menos db hits)
PROFILE
MATCH (d:Deputado)
WHERE d.nome CONTAINS 'Zanatta'
RETURN d.nome, d.siglaUf, d.indiceAmbiental;

// ---- C.2 RANGE INDEX: busca por intervalo (>, <) ----
// Antes do índice
PROFILE
MATCH (d:Deputado)
WHERE d.indiceAmbiental >= 90
RETURN d.nome, d.partidoRecente, d.indiceAmbiental
ORDER BY d.indiceAmbiental DESC;

CREATE INDEX deputado_indice_ambiental IF NOT EXISTS FOR (d:Deputado) ON (d.indiceAmbiental);

CALL db.awaitIndexes();

// Depois do índice (deve aparecer NodeIndexSeekByRange)
PROFILE
MATCH (d:Deputado)
WHERE d.indiceAmbiental >= 90
RETURN d.nome, d.partidoRecente, d.indiceAmbiental
ORDER BY d.indiceAmbiental DESC;

// ---- C.3 ÍNDICE EM PROPRIEDADE DE RELACIONAMENTO ----
// Antes do índice: encontrar os votos de obstrução
PROFILE
MATCH (d:Deputado)-[v:VOTOU]->(vt:Votacao)
WHERE v.voto = 'Obstrução'
RETURN d.nome, v.partido, vt.proposicao;

CREATE INDEX votou_voto IF NOT EXISTS FOR ()-[v:VOTOU]-() ON (v.voto);

CALL db.awaitIndexes();

// Depois do índice (deve aparecer um operador RelationshipIndexSeek)
PROFILE
MATCH (d:Deputado)-[v:VOTOU]->(vt:Votacao)
WHERE v.voto = 'Obstrução'
RETURN d.nome, v.partido, vt.proposicao;

// ---- C.4 EXPLAIN x PROFILE em uma das perguntas (4b, dissidentes) ----
// EXPLAIN só mostra o plano, sem executar; PROFILE executa e conta os db hits
EXPLAIN
MATCH (p:Partido)-[o:ORIENTOU]->(:Votacao {id: '2233802-424'})<-[v:VOTOU]-(d:Deputado)
WHERE v.partido = p.sigla AND o.orientacao IN ['Sim', 'Não']
  AND v.voto IN ['Sim', 'Não'] AND v.voto <> o.orientacao
RETURN p.sigla, d.nome, v.uf;

PROFILE
MATCH (p:Partido)-[o:ORIENTOU]->(:Votacao {id: '2233802-424'})<-[v:VOTOU]-(d:Deputado)
WHERE v.partido = p.sigla AND o.orientacao IN ['Sim', 'Não']
  AND v.voto IN ['Sim', 'Não'] AND v.voto <> o.orientacao
RETURN p.sigla, d.nome, v.uf;
