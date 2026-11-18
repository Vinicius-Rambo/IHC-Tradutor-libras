"""
Descobre como a API do VLibras responde de verdade (rode na B13, com internet).

    .venv/bin/python ferramentas/testar_vlibras_api.py "bom dia, Ana"

Mostra o status, o tipo e o começo da resposta de /translate e de /video (testando alguns nomes de campo),
e guarda o vídeo em /tmp/vlibras_teste.mp4 se vier um. Mande a saída para ajustar o robo/config.py.
"""
import os
import sys

import httpx

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from robo import config  # noqa: E402

base = getattr(config, "LIBRAS_API_URL", "https://traducao2.vlibras.gov.br").rstrip("/")
texto = " ".join(sys.argv[1:]) or "bom dia"
cab = {"User-Agent": "RoboByte/1.0 (teste)"}
chave = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "chave_vlibras.txt")
if os.path.isfile(chave):
    cab[getattr(config, "LIBRAS_API_CABECALHO_DA_CHAVE", "x-api-key")] = open(chave).read().strip()


def mostrar(r):
    print(f"  status {r.status_code} | tipo {r.headers.get('content-type')} | {len(r.content)} bytes")
    if not r.headers.get("content-type", "").startswith("video/"):
        print("  corpo:", r.text[:300].replace("\n", " "))


print(f"== POST {base}/translate  {{'text': {texto!r}}}")
glosa = texto
try:
    r = httpx.post(base + "/translate", json={"text": texto}, headers=cab, timeout=15)
    mostrar(r)
    from robo.vlibras_api import extrair_glosa
    glosa = extrair_glosa(r) or texto
    print("  glosa lida:", glosa)
except Exception as e:
    print("  erro:", type(e).__name__, e)

for campo in ("gloss", "glosa", "text"):
    print(f"== POST {base}/video  {{'{campo}': {glosa!r}}}")
    try:
        r = httpx.post(base + "/video", json={campo: glosa}, headers=cab, timeout=60, follow_redirects=True)
        mostrar(r)
        if r.status_code == 200:
            if r.headers.get("content-type", "").startswith("video/"):
                open("/tmp/vlibras_teste.mp4", "wb").write(r.content)
                print("  vídeo guardado em /tmp/vlibras_teste.mp4  -> use LIBRAS_API_CAMPO_VIDEO =", repr(campo))
            break
    except Exception as e:
        print("  erro:", type(e).__name__, e)
