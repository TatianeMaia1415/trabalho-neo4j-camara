"""
Passo 1.5 - Download da base do Atlas Digital de Desastres no Brasil (MIDR), 1991-2025.
Fonte: https://atlasdigital.mdr.gov.br  (menu Downloads > Base de Dados Completa > CSV)

O arquivo é grande, então é baixado em partes (streaming), com barra de progresso
e novas tentativas se a conexão cair. Só vira .csv quando o download termina inteiro.

Gera: dados/brutos/desastres/BD_Atlas_1991_2025_v1.1_2026.08.06_Consolidado.csv
Rodar com: python scripts\07_baixar_atlas.py
"""
import time
from pathlib import Path

import requests
from tqdm import tqdm

URL = "https://atlasdigital.mdr.gov.br/arquivos/2026/BD_Atlas_1991_2025_v1.1_2026.08.06_Consolidado.csv"
PASTA = Path(__file__).resolve().parent.parent / "dados" / "brutos" / "desastres"
PASTA.mkdir(parents=True, exist_ok=True)
destino = PASTA / URL.rsplit("/", 1)[-1]

if destino.exists() and destino.stat().st_size > 0:
    raise SystemExit(f"Já baixado: {destino.name} ({destino.stat().st_size / 1e6:.1f} MB)")

temporario = destino.with_suffix(".part")
for tentativa in range(1, 6):
    try:
        with requests.get(URL, stream=True, timeout=120) as r:
            r.raise_for_status()
            total = int(r.headers.get("Content-Length", 0)) or None
            with open(temporario, "wb") as f, tqdm(total=total, unit="B", unit_scale=True,
                                                    desc=f"Baixando (tentativa {tentativa})") as barra:
                for pedaco in r.iter_content(chunk_size=1024 * 256):
                    f.write(pedaco)
                    barra.update(len(pedaco))
        if total and temporario.stat().st_size < total:
            raise IOError(f"download incompleto ({temporario.stat().st_size} de {total} bytes)")
        temporario.replace(destino)
        break
    except (requests.RequestException, IOError) as erro:
        if tentativa == 5:
            raise
        tqdm.write(f"  ! {erro} - tentando de novo em {5 * tentativa}s")
        time.sleep(5 * tentativa)

print(f"\nArquivo salvo: {destino} ({destino.stat().st_size / 1e6:.1f} MB)")