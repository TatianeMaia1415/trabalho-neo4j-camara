"""
Funções reutilizadas por todos os scripts de coleta (01_..., 02_..., etc.):
  - consultar / consultar_dados / consultar_paginado -> API de Dados Abertos da Câmara
  - baixar_arquivo -> download robusto de arquivos grandes (arquivos anuais, cota parlamentar)
"""
import time
from pathlib import Path

import requests
from tqdm import tqdm

BASE = "https://dadosabertos.camara.leg.br/api/v2"

sessao = requests.Session()
sessao.headers.update({"Accept": "application/json"})


def consultar(endpoint, tentativas=4, **params):
    """Faz um GET na API e devolve o JSON completo.
    Tenta de novo se a API falhar (erro 5xx) ou pedir para esperar (429)."""
    url = endpoint if endpoint.startswith("http") else f"{BASE}/{endpoint}"
    for tentativa in range(1, tentativas + 1):
        try:
            r = sessao.get(url, params=params, timeout=60)
            if r.status_code in (429, 500, 502, 503, 504):
                raise requests.HTTPError(f"HTTP {r.status_code}")
            r.raise_for_status()
            time.sleep(0.2)  # pausa curta para não sobrecarregar a API
            return r.json()
        except (requests.HTTPError, requests.ConnectionError, requests.Timeout) as erro:
            if tentativa == tentativas:
                raise
            espera = 2 * tentativa
            tqdm.write(f"  ! {erro} em {url} - tentando de novo em {espera}s")  # não quebra a barra
            time.sleep(espera)


def consultar_dados(endpoint, **params):
    """Devolve só a parte 'dados' da resposta (uma página)."""
    return consultar(endpoint, **params)["dados"]


def consultar_paginado(endpoint, itens=100, **params):
    """Percorre todas as páginas de um endpoint e devolve a lista completa."""
    resultado = []
    resposta = consultar(endpoint, itens=itens, pagina=1, **params)
    while True:
        resultado.extend(resposta["dados"])
        proxima = next((l["href"] for l in resposta.get("links", []) if l["rel"] == "next"), None)
        if not proxima:
            break
        resposta = consultar(proxima)  # o link 'next' já traz todos os parâmetros
    return resultado


def baixar_arquivo(url, destino, tentativas=5):
    """Baixa um arquivo grande em partes, com barra de progresso e novas tentativas.
    - Se o arquivo já existe, não baixa de novo.
    - Só vira o arquivo final quando o download termina inteiro (antes fica como .part).
    - Devolve o caminho do arquivo, ou None se ele não existe no servidor (HTTP 404)."""
    destino = Path(destino)
    destino.parent.mkdir(parents=True, exist_ok=True)
    if destino.exists() and destino.stat().st_size > 0:
        print(f"  {destino.name} já baixado - usando cópia local")
        return destino
    temporario = destino.with_name(destino.name + ".part")
    for tentativa in range(1, tentativas + 1):
        try:
            with requests.get(url, stream=True, timeout=120) as r:
                if r.status_code == 404:
                    print(f"  {destino.name}: não existe no servidor (404)")
                    return None
                r.raise_for_status()
                total = int(r.headers.get("Content-Length", 0)) or None
                with open(temporario, "wb") as f, tqdm(total=total, unit="B", unit_scale=True,
                                                        desc=f"  {destino.name}", leave=False) as barra:
                    for pedaco in r.iter_content(chunk_size=1024 * 256):
                        f.write(pedaco)
                        barra.update(len(pedaco))
            if total and temporario.stat().st_size < total:
                raise IOError(f"download incompleto ({temporario.stat().st_size} de {total} bytes)")
            temporario.replace(destino)
            print(f"  {destino.name} baixado ({destino.stat().st_size / 1e6:.1f} MB)")
            return destino
        except (requests.RequestException, IOError) as erro:
            if tentativa == tentativas:
                raise
            tqdm.write(f"  ! {erro} - tentando de novo em {5 * tentativa}s")
            time.sleep(5 * tentativa)