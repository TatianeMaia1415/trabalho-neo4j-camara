// =====================================================================
// Passo 6 - As 5 perguntas de análise
// Rodar UMA consulta por vez. A consulta "a" de cada pergunta é a principal
// (vai para o PDF); as demais aprofundam ou controlam vieses.
//
// Regra usada em todas as consultas ambientais:
//   o voto é PRÓ-AMBIENTE quando  (votou Sim)  =  (Sim significa PRO_AMBIENTE)
//   Obstrução conta como "Não"; Abstenção e Artigo 17 ficam de fora.
// =====================================================================


// =====================================================================
// PERGUNTA 1 - Estados mais afetados por eventos climáticos possuem
//              deputados que votam mais a favor de medidas ambientais?
// =====================================================================

// 1a. % de votos pró-ambiente por faixa de exposição climática da UF
MATCH (u:UF)<-[:REPRESENTA]-(:Deputado)-[v:VOTOU]->(vt:Votacao {tema: 'ambiental'})
WHERE v.voto IN ['Sim', 'Não', 'Obstrução']
WITH u, CASE WHEN (v.voto = 'Sim') = (vt.simSignifica = 'PRO_AMBIENTE') THEN 1.0 ELSE 0.0 END AS pro
RETURN u.exposicao AS exposicao_climatica,
       count(DISTINCT u) AS ufs,
       count(*) AS votos,
       round(100 * avg(pro), 1) AS pct_votos_pro_ambiente
ORDER BY pct_votos_pro_ambiente DESC;

// 1b. Controle por partido: dentro do MESMO partido, a exposição muda o voto?
MATCH (u:UF)<-[:REPRESENTA]-(:Deputado)-[v:VOTOU]->(vt:Votacao {tema: 'ambiental'})
WHERE v.voto IN ['Sim', 'Não', 'Obstrução']
WITH v.partido AS partido, u.exposicao AS exposicao,
     CASE WHEN (v.voto = 'Sim') = (vt.simSignifica = 'PRO_AMBIENTE') THEN 1.0 ELSE 0.0 END AS pro
WITH partido, exposicao, round(100 * avg(pro), 1) AS pct, count(*) AS votos
WHERE votos >= 20
WITH partido, collect({exp: exposicao, pct: pct}) AS faixas
WHERE size(faixas) = 3
RETURN partido,
       [f IN faixas WHERE f.exp = 'alta'  | f.pct][0] AS pct_pro_exposicao_alta,
       [f IN faixas WHERE f.exp = 'media' | f.pct][0] AS pct_pro_exposicao_media,
       [f IN faixas WHERE f.exp = 'baixa' | f.pct][0] AS pct_pro_exposicao_baixa
ORDER BY partido;

// 1c. Correlação (Pearson) entre intensidade de desastres e voto pró-ambiente, por UF
MATCH (u:UF)<-[:REPRESENTA]-(:Deputado)-[v:VOTOU]->(vt:Votacao {tema: 'ambiental'})
WHERE v.voto IN ['Sim', 'Não', 'Obstrução']
WITH u, avg(CASE WHEN (v.voto = 'Sim') = (vt.simSignifica = 'PRO_AMBIENTE') THEN 1.0 ELSE 0.0 END) AS pro
WITH collect({x: u.registrosPorMunicipio, y: pro}) AS pts
WITH pts,
     reduce(s = 0.0, p IN pts | s + p.x) / size(pts) AS mx,
     reduce(s = 0.0, p IN pts | s + p.y) / size(pts) AS my
RETURN size(pts) AS ufs,
       round(reduce(s = 0.0, p IN pts | s + (p.x - mx) * (p.y - my)) /
             sqrt(reduce(s = 0.0, p IN pts | s + (p.x - mx) ^ 2) *
                  reduce(s = 0.0, p IN pts | s + (p.y - my) ^ 2)), 3) AS correlacao_pearson;


// =====================================================================
// PERGUNTA 2 - Quais partidos apresentam maior proporção de votos
//              contrários a medidas ambientais?
// =====================================================================

// 2a. % de votos contra o ambiente por partido (partido NA DATA do voto)
//     + quantas vezes a orientação oficial do partido foi contra o ambiente
MATCH (:Deputado)-[v:VOTOU]->(vt:Votacao {tema: 'ambiental'})
WHERE v.voto IN ['Sim', 'Não', 'Obstrução']
WITH v.partido AS partido,
     CASE WHEN (v.voto = 'Sim') = (vt.simSignifica = 'PRO_AMBIENTE') THEN 0 ELSE 1 END AS contra
WITH partido, count(*) AS votos, sum(contra) AS votos_contra
WHERE votos >= 50
OPTIONAL MATCH (p:Partido {sigla: partido})-[o:ORIENTOU]->(vt2:Votacao {tema: 'ambiental'})
WHERE o.orientacao IN ['Sim', 'Não']
RETURN partido, votos,
       round(100.0 * votos_contra / votos, 1) AS pct_votos_contra_ambiente,
       count(o) AS orientacoes_registradas,
       sum(CASE WHEN o IS NULL THEN 0
                WHEN (o.orientacao = 'Sim') = (vt2.simSignifica = 'PRO_AMBIENTE') THEN 0
                ELSE 1 END) AS orientacoes_contra_ambiente
ORDER BY pct_votos_contra_ambiente DESC;

// 2b. Coesão: em cada votação, quanto o partido votou unido? (% do voto majoritário)
MATCH (:Deputado)-[v:VOTOU]->(vt:Votacao {tema: 'ambiental'})
WHERE v.voto IN ['Sim', 'Não']
WITH v.partido AS partido, vt, v.voto AS voto, count(*) AS n
WITH partido, vt, max(n) * 1.0 / sum(n) AS coesao, sum(n) AS total
WHERE total >= 5
RETURN partido, count(vt) AS votacoes, round(100 * avg(coesao), 1) AS coesao_media_pct
ORDER BY coesao_media_pct DESC;


// =====================================================================
// PERGUNTA 3 - Deputados que votam contra medidas ambientais estão
//              concentrados em determinadas frentes parlamentares?
// =====================================================================

// 3a. Índice de concentração: taxa de votos contra dos membros / taxa da Câmara
//     (índice > 1 = frente concentra deputados que votam contra o ambiente)
MATCH (d:Deputado)-[v:VOTOU]->(vt:Votacao {tema: 'ambiental'})
WHERE v.voto IN ['Sim', 'Não', 'Obstrução']
WITH d, avg(CASE WHEN (v.voto = 'Sim') = (vt.simSignifica = 'PRO_AMBIENTE') THEN 0.0 ELSE 1.0 END) AS taxa_contra,
     count(*) AS n
WHERE n >= 5
WITH collect({d: d, t: taxa_contra}) AS deps, avg(taxa_contra) AS media_camara
UNWIND deps AS x
WITH x.d AS d, x.t AS t, media_camara
MATCH (d)-[:MEMBRO_DE]->(f:Frente)
WITH f, media_camara, count(d) AS membros_votantes, avg(t) AS taxa_membros,
     sum(CASE WHEN t >= 0.5 THEN 1 ELSE 0 END) AS majoritariamente_contra
RETURN f.tema AS frente, membros_votantes,
       round(100 * taxa_membros, 1) AS pct_contra_membros,
       round(100 * media_camara, 1) AS pct_contra_camara,
       round(taxa_membros / media_camara, 2) AS indice_concentracao,
       round(100.0 * majoritariamente_contra / membros_votantes, 1) AS pct_membros_maioria_contra
ORDER BY indice_concentracao DESC;

// 3b. Sobreposição FPA x Ambientalista: quem está nas duas vota como?
MATCH (d:Deputado)-[v:VOTOU]->(vt:Votacao {tema: 'ambiental'})
WHERE v.voto IN ['Sim', 'Não', 'Obstrução']
WITH d, avg(CASE WHEN (v.voto = 'Sim') = (vt.simSignifica = 'PRO_AMBIENTE') THEN 0.0 ELSE 1.0 END) AS t
WITH d, t,
     EXISTS { (d)-[:MEMBRO_DE]->(:Frente {tema: 'agro'}) } AS fpa,
     EXISTS { (d)-[:MEMBRO_DE]->(:Frente {tema: 'ambiental'}) } AS amb
RETURN CASE WHEN fpa AND amb THEN 'FPA e Ambientalista'
            WHEN fpa THEN 'so FPA'
            WHEN amb THEN 'so Ambientalista'
            ELSE 'nenhuma das duas' END AS grupo,
       count(*) AS deputados,
       round(100 * avg(t), 1) AS pct_votos_contra_ambiente
ORDER BY pct_votos_contra_ambiente DESC;


// =====================================================================
// PERGUNTA 4 - Como os deputados votaram sobre o fim da escala 6x1 e
//              quais partidos concentram os votos contrários?
// =====================================================================

// 4a. Votos contra por partido: mérito (1º e 2º turno) x requerimento procedimental
MATCH (:Deputado)-[v:VOTOU]->(vt:Votacao {tema: '6x1'})
WHERE vt.id IN ['2233802-424', '2233802-438', '2233802-416']
WITH v.partido AS partido, vt.id AS id, v.voto AS voto
WITH partido,
     sum(CASE WHEN id = '2233802-424' AND voto IN ['Não', 'Obstrução'] THEN 1 ELSE 0 END) AS contra_1_turno,
     sum(CASE WHEN id = '2233802-438' AND voto IN ['Não', 'Obstrução'] THEN 1 ELSE 0 END) AS contra_2_turno,
     sum(CASE WHEN id = '2233802-416' AND voto = 'Não' THEN 1 ELSE 0 END) AS nao_requerimento,
     sum(CASE WHEN id = '2233802-424' THEN 1 ELSE 0 END) AS votantes_1_turno
WHERE contra_1_turno + contra_2_turno + nao_requerimento > 0
RETURN partido, votantes_1_turno, contra_1_turno, contra_2_turno, nao_requerimento
ORDER BY contra_1_turno DESC, nao_requerimento DESC;

// 4b. Dissidentes: deputados que votaram contra a orientação do próprio partido (1º turno)
MATCH (p:Partido)-[o:ORIENTOU]->(:Votacao {id: '2233802-424'})<-[v:VOTOU]-(d:Deputado)
WHERE v.partido = p.sigla
  AND o.orientacao IN ['Sim', 'Não'] AND v.voto IN ['Sim', 'Não']
  AND v.voto <> o.orientacao
RETURN p.sigla AS partido, o.orientacao AS orientacao_do_partido, v.voto AS voto,
       d.nome AS deputado, v.uf AS uf
ORDER BY partido, uf;

// 4c. Resistência procedimental: votou "Não" no requerimento mas "Sim" no 1º turno
MATCH (d:Deputado)-[r:VOTOU]->(:Votacao {id: '2233802-416'}),
      (d)-[t:VOTOU]->(:Votacao {id: '2233802-424'})
WHERE r.voto = 'Não' AND t.voto = 'Sim'
RETURN t.partido AS partido, count(*) AS nao_no_procedimento_sim_no_merito
ORDER BY nao_no_procedimento_sim_no_merito DESC;


// =====================================================================
// PERGUNTA 5 - Existe relação entre o posicionamento na votação da 6x1,
//              as despesas parlamentares e a participação em eventos?
// =====================================================================

// 5a. Medianas de gasto e participação, por voto no 1º turno
MATCH (d:Deputado)-[v:VOTOU]->(:Votacao {id: '2233802-424'})
WHERE v.voto IN ['Sim', 'Não'] AND d.gastoMensal IS NOT NULL
RETURN v.voto AS voto_1_turno, count(*) AS deputados,
       round(percentileCont(d.gastoMensal, 0.5)) AS gasto_mensal_mediano,
       round(percentileCont(d.indiceGastoUf, 0.5), 2) AS indice_gasto_uf_mediano,
       round(percentileCont(d.eventosPorMes, 0.5), 1) AS eventos_mes_mediano,
       round(percentileCont(d.eventosComissoesPorMes, 0.5), 1) AS eventos_comissoes_mes_mediano
ORDER BY voto_1_turno;

// 5b. Controle por partido: comparando Sim x Não DENTRO do mesmo partido
MATCH (d:Deputado)-[v:VOTOU]->(:Votacao {id: '2233802-424'})
WHERE v.voto IN ['Sim', 'Não'] AND d.indiceGastoUf IS NOT NULL
WITH v.partido AS partido, v.voto AS voto, count(d) AS n,
     avg(d.indiceGastoUf) AS gasto, avg(d.eventosComissoesPorMes) AS eventos
WITH partido, collect({voto: voto, n: n, gasto: gasto, eventos: eventos}) AS grupos
WHERE size(grupos) = 2
UNWIND grupos AS g
RETURN partido, g.voto AS voto, g.n AS deputados,
       round(g.gasto, 2) AS indice_gasto_uf_medio,
       round(g.eventos, 1) AS eventos_comissoes_por_mes
ORDER BY partido, voto;
