# Pautas Ambientais e a Escala 6x1 na Câmara dos Deputados (2023–2026)

Trabalho 2 da disciplina **Banco de Dados para Ciência de Dados** (DC/UFSCar), Prof.ª Marcela Xavier Ribeiro.

**Integrantes:** Brenda Raquel Maia Gonçalves e Tatiane Maia de Oliveira

Dados públicos da Câmara dos Deputados modelados como grafo no **Neo4j**. As consultas em Cypher respondem a cinco perguntas:

1. Estados mais afetados por eventos climáticos possuem deputados que votam mais a favor de medidas ambientais?
2. Quais partidos apresentam maior proporção de votos contrários a medidas ambientais?
3. Deputados que votam contra medidas ambientais estão concentrados em determinadas frentes parlamentares?
4. Como os deputados votaram sobre o fim da escala 6x1 e quais partidos concentram os votos contrários?
5. Existe relação entre o posicionamento na votação da escala 6x1, as despesas parlamentares e a participação em eventos?

## Fontes de dados

- [Dados Abertos da Câmara dos Deputados](https://dadosabertos.camara.leg.br/swagger/api.html): API v2 e arquivos anuais (deputados, partidos, frentes, proposições, votações, votos, orientações, cota parlamentar e presença em eventos)
- [Atlas Digital de Desastres no Brasil](https://atlasdigital.mdr.gov.br), do Ministério da Integração e do Desenvolvimento Regional, base de 1991 a 2025

## Estrutura

```
cypher/              consultas de validação, visualização, das 5 perguntas e das aplicações das aulas
dados/brutos/        dados originais coletados (API, arquivos anuais e Atlas)
dados/processados/   agregações e CSVs de nós e relacionamentos para o Neo4j
prints/              imagens usadas no relatório
scripts/             scripts Python de coleta, transformação e importação
requirements.txt     bibliotecas utilizadas
```

## Modelo do grafo

- **Nós (762):** Deputado, Partido, UF, Frente, Votacao, Proposicao
- **Relacionamentos (10.975):** VOTOU, MEMBRO_DE, FILIADO_A, REPRESENTA, AUTOR_DE, ORIENTOU, SOBRE

## Como reproduzir

Requisitos: Python 3.13 e Neo4j (testado no Neo4j Desktop, versão 2026.10.2).

```
python -m pip install -r requirements.txt
```

Execute os scripts da pasta `scripts/` na ordem da numeração. Os scripts de coleta usam o módulo `api_camara.py`, que faz as chamadas à API com novas tentativas e paginação.

| Etapa | Scripts |
| --- | --- |
| Teste de acesso à API | `00_teste_api.py` |
| Coleta da PEC 6x1 | `01_coleta_6x1.py`, `01b_detalhe_votacao.py` (detalhe de uma votação, usado para conferir os tipos de voto) |
| Seleção das votações ambientais | `02_descobrir_votacoes_ambientais.py`, `03_listar_votacoes_ambientais.py` (seguidos da revisão manual que define as 14 votações e suas polaridades) |
| Votos ambientais | `04_coleta_votos_ambientais.py` |
| Deputados, partidos e autores | `05_coleta_deputados_partidos_autores.py` |
| Frentes parlamentares | `06_coleta_frentes.py` |
| Desastres (Atlas) | `07_baixar_atlas.py`, `07a_inspecionar_atlas.py` (exploração das colunas), `07b_agregar_desastres_uf.py` |
| Despesas e eventos | `08_baixar_despesas_eventos.py`, `08b_agregar_despesas_eventos.py` |
| CSVs para o Neo4j | `09_gerar_csvs_neo4j.py` |
| Importação no Neo4j | `10_importar_neo4j.py` (a senha do banco é pedida na execução e não fica gravada) |
| Consulta pelo Python | `11_consulta_python.py` |

Com o grafo carregado, rode os arquivos da pasta `cypher/` no Neo4j Browser:

1. `01_validacao_e_visualizacao.cypher`
2. `02_perguntas_analise.cypher`
3. `03_aplicacoes_das_aulas.cypher`

Os dados brutos já estão no repositório, então dá para pular as coletas e começar pelo `09_gerar_csvs_neo4j.py`.