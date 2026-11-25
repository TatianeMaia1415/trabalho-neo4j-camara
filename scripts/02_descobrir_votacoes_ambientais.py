"""
Passo 1.2a - Descobrir as votações NOMINAIS do Plenário (2023-2026) sobre temas ambientais.

Estratégia:
  1. Baixa os arquivos anuais da Câmara:
       votacoes-{ano}.csv             -> todas as votações do ano (com placar Sim/Não)
       votacoesProposicoes-{ano}.csv  -> quais proposições cada votação afetou (com ementa)
  2. Fica só com votações do Plenário (PLEN) que foram nominais (Sim + Não > 0).
  3. Filtra pelas proposições cuja ementa contém palavras-chave ambientais.
  4. Salva a lista de candidatas para escolhermos juntos.

Gera em dados/brutos/:
  ambiente_candidatas_votacoes.csv     -> uma linha por votação candidata
  ambiente_candidatas_proposicoes.csv  -> resumo por proposição
Rodar com: python scripts\02_descobrir_votacoes_ambientais.py
"""
import time
import unicodedata
from pathlib import Path

import pandas as pd
import requests

ANOS = [2023, 2024, 2025, 2026]
URL = "https://dadosabertos.camara.leg.br/arquivos/{nome}/csv/{nome}-{ano}.csv"
PASTA = Path(__file__).resolve().parent.parent / "dados" / "brutos"
PASTA.mkdir(parents=True, exist_ok=True)
PASTA_ARQUIVOS = PASTA / "arquivos_camara"   # cópia original dos arquivos anuais (vai para o GitHub)
PASTA_ARQUIVOS.mkdir(exist_ok=True)

# Palavras-chave (sem acento, minúsculas) procuradas na ementa da proposição
PALAVRAS = [
    "ambiental", "meio ambiente", "licenciamento", "florest", "desmatamento",
    "terras indigenas", "terra indigena", "terras tradicionalmente ocupadas",
    "carbono", "clima", "efeito estufa", "emissoes", "descarboniz",
    "agrotox", "pesticida", "defensivos agricolas",
    "mata atlantica", "pantanal", "amazonia", "cerrado", "caatinga",
    "unidades de conservacao", "unidade de conservacao", "biodiversidade",
    "recursos hidricos", "residuos solidos", "garimpo", "queimada", "incendios florestais",
    # v2: ementas que citam só o número da lei ambiental (descoberto na 1ª rodada)
    "vegetacao nativa", "codigo florestal", "demarcacao", "ibama", "icmbio",
    "9.605", "9605",        # Lei de Crimes Ambientais
    "12.651", "12651",      # Código Florestal
    "11.428", "11428",      # Lei da Mata Atlântica
    "6.938", "6938",        # Política Nacional do Meio Ambiente
    "9.985", "9985",        # Sistema Nacional de Unidades de Conservação
]


def sem_acento(texto):
    texto = unicodedata.normalize("NFKD", str(texto))
    return "".join(c for c in texto if not unicodedata.combining(c)).lower()


def baixar(nome, ano, tentativas=5):
    """Baixa o arquivo para o disco (só uma vez) e depois lê do disco.
    Se a conexão cair no meio do download, tenta de novo."""
    destino = PASTA_ARQUIVOS / f"{nome}-{ano}.csv"
    if destino.exists() and destino.stat().st_size > 0:
        print(f"  {destino.name} já baixado - usando cópia local")
    else:
        url = URL.format(nome=nome, ano=ano)
        for tentativa in range(1, tentativas + 1):
            try:
                print(f"  baixando {destino.name} (tentativa {tentativa}) ...")
                r = requests.get(url, timeout=180)
                r.raise_for_status()
                esperado = int(r.headers.get("Content-Length", 0))
                if esperado and len(r.content) < esperado:
                    raise IOError(f"download incompleto ({len(r.content)} de {esperado} bytes)")
                temporario = destino.with_suffix(".part")
                temporario.write_bytes(r.content)
                temporario.replace(destino)   # só vira .csv quando o download terminou inteiro
                break
            except (requests.RequestException, IOError) as erro:
                if tentativa == tentativas:
                    raise
                print(f"  ! {erro} - tentando de novo em {5 * tentativa}s")
                time.sleep(5 * tentativa)
    df = pd.read_csv(destino, sep=";", dtype=str, encoding="utf-8")
    df["ano_arquivo"] = ano
    return df


votacoes, vot_prop = [], []
for ano in ANOS:
    votacoes.append(baixar("votacoes", ano))
    vot_prop.append(baixar("votacoesProposicoes", ano))
votacoes = pd.concat(votacoes, ignore_index=True)
vot_prop = pd.concat(vot_prop, ignore_index=True)

# Mostra as colunas (útil se a Câmara mudar o formato dos arquivos)
print("\nColunas de votacoes:", list(votacoes.columns))
print("Colunas de votacoesProposicoes:", list(vot_prop.columns))

# 1) Só Plenário e só nominais
for col in ("votosSim", "votosNao", "votosOutros"):
    votacoes[col] = pd.to_numeric(votacoes[col], errors="coerce").fillna(0).astype(int)
nominais = votacoes[(votacoes["siglaOrgao"] == "PLEN") &
                    (votacoes["votosSim"] + votacoes["votosNao"] > 0)]
print(f"\nVotações do Plenário 2023-2026: {(votacoes['siglaOrgao'] == 'PLEN').sum()}"
      f" | nominais: {len(nominais)}")

# 2) Liga cada votação às proposições afetadas e filtra pela ementa
base = nominais[["id", "data", "votosSim", "votosNao", "votosOutros", "aprovacao", "descricao"]] \
    .merge(vot_prop[["idVotacao", "proposicao_id", "proposicao_siglaTipo", "proposicao_numero",
                     "proposicao_ano", "proposicao_ementa"]],
           left_on="id", right_on="idVotacao", how="inner")
base["ementa_norm"] = base["proposicao_ementa"].map(sem_acento)
base["palavras_achadas"] = base["ementa_norm"].map(
    lambda e: ", ".join(p for p in PALAVRAS if p in e))
amb = base[base["palavras_achadas"] != ""].drop(columns=["ementa_norm", "idVotacao"])
amb = amb.rename(columns={"id": "idVotacao"}).sort_values("data")
amb["proposicao"] = (amb["proposicao_siglaTipo"] + " " + amb["proposicao_numero"]
                     + "/" + amb["proposicao_ano"])

# 3) Resumo por proposição
resumo = (amb.groupby(["proposicao", "proposicao_id", "proposicao_ementa", "palavras_achadas"])
          .agg(n_votacoes=("idVotacao", "nunique"),
               primeira=("data", "min"), ultima=("data", "max"),
               maior_nao=("votosNao", "max"))
          .reset_index().sort_values("primeira"))

amb.to_csv(PASTA / "ambiente_candidatas_votacoes.csv", index=False, encoding="utf-8-sig")
resumo.to_csv(PASTA / "ambiente_candidatas_proposicoes.csv", index=False, encoding="utf-8-sig")

print(f"\n== {len(resumo)} proposições ambientais com votação nominal no Plenário "
      f"({amb['idVotacao'].nunique()} votações) ==")
for _, r in resumo.iterrows():
    print(f"\n{r['proposicao']} (id {r['proposicao_id']}) | {r['n_votacoes']} votações "
          f"| {r['primeira'][:10]} a {r['ultima'][:10]} | maior nº de 'Não': {r['maior_nao']}")
    print(f"   palavras: {r['palavras_achadas']}")
    print(f"   {str(r['proposicao_ementa'])[:220]}")

print(f"\nArquivos salvos em {PASTA}")