"""Baixa o Three.js (r128) para libras_tela/vendor/, para o tablet não depender da internet.
Rode na B13, com internet, na pasta do projeto:   .venv/bin/python ferramentas/baixar_three.py"""
import os
import sys

import httpx

URL = "https://cdnjs.cloudflare.com/ajax/libs/three.js/r128/three.min.js"
DESTINO = os.path.join("libras_tela", "vendor", "three.min.js")

os.makedirs(os.path.dirname(DESTINO), exist_ok=True)
resposta = httpx.get(URL, timeout=60, follow_redirects=True)
resposta.raise_for_status()
if b"REVISION" not in resposta.content[:200000] or len(resposta.content) < 400_000:
    sys.exit("O arquivo baixado não parece o three.min.js; confira a internet.")
with open(DESTINO, "wb") as f:
    f.write(resposta.content)
print(f"ok: {DESTINO} ({len(resposta.content) // 1024} KB)")
