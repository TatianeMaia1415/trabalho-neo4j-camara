"""
Passo 0 - Teste de acesso à API de Dados Abertos da Câmara dos Deputados.
Verifica se os endpoints que vamos usar respondem e mostra amostras.
Rodar com: python scripts/00_teste_api.py
"""
import requests

BASE = "https://dadosabertos.camara.leg.br/api/v2"
HEADERS = {"Accept": "application/json"}


def get(endpoint, **params):
    r = requests.get(f"{BASE}/{endpoint}", params=params, headers=HEADERS, timeout=30)
    r.raise_for_status()
    return r.json()


# 1) Deputados da 57ª legislatura (2023-2027)
dep = get("deputados", idLegislatura=57, itens=5, ordem="ASC", ordenarPor="nome")
print("== Deputados (amostra) ==")
for d in dep["dados"]:
    print(f"  {d['id']:>7} | {d['nome']:<35} | {d['siglaPartido']:<12} | {d['siglaUf']}")

# 2) Frentes parlamentares da 57ª legislatura
fr = get("frentes", idLegislatura=57, itens=5)
print("\n== Frentes (amostra) ==")
for f in fr["dados"]:
    print(f"  {f['id']:>7} | {f['titulo'][:80]}")

# 3) Localizar a PEC 221/2019 (fim da escala 6x1)
pec = get("proposicoes", siglaTipo="PEC", numero=221, ano=2019)
print("\n== PEC 221/2019 ==")
for p in pec["dados"]:
    print(f"  id={p['id']} | {p['siglaTipo']} {p['numero']}/{p['ano']} | {p['ementa'][:100]}")
    votacoes = get(f"proposicoes/{p['id']}/votacoes")["dados"]
    print("  Votações encontradas:", len(votacoes))
    for v in votacoes:
        print("    ", v["id"], "|", v["data"], "|", v["siglaOrgao"], "|", v["descricao"][:90])

# 4) Arquivo em massa de votos de 2026 (só checa se existe e o tamanho)
url = "https://dadosabertos.camara.leg.br/arquivos/votacoesVotos/csv/votacoesVotos-2026.csv"
h = requests.head(url, timeout=30, allow_redirects=True)
tam = int(h.headers.get("Content-Length", 0)) / 1e6
print(f"\n== Arquivo votacoesVotos-2026.csv: HTTP {h.status_code}, ~{tam:.1f} MB ==")

print("\nOK - API acessível. Pode seguir para o Passo 1.")