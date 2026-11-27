"""
LIBRAS (da fala em português para sinais na tela)
=================================================
Fluxo:  texto  ->  glosa  ->  sinais (imagens ou vídeos)  ->  tela do tablet

1. GLOSA: a Libras tem gramática própria (não é o português "sinalizado"). A glosa é a frase
   reescrita na ordem e nas palavras da Libras: "Maria comprou uma casa" -> "MARIA COMPRAR CASA".
   - Se o pacote `vlibras_translate` (Suíte VLibras, LAVID/UFPB) estiver instalado, é ele quem traduz.
   - Se não estiver, usa uma regra simples (tira artigos, preposições e "ser/estar").
2. SINAIS: para cada palavra da glosa, procura um arquivo em  libras/sinais/  (oi.gif, bom_dia.mp4...).
   Frases de várias palavras têm prioridade: se existir bom_dia.*, "BOM DIA" vira um sinal só.
3. ALFABETO MANUAL (datilologia): se a palavra não tem sinal, o robô soletra com as imagens
   de  libras/alfabeto/  (a.png ... z.png, 0.png ... 9.png). É assim que nomes próprios são sinalizados.
4. Se faltar até a imagem da letra, a tela mostra a letra escrita (nada quebra).

As imagens e vídeos NÃO vêm no repositório: veja libras/LEIA-ME.md.

Teste sozinho:   python -m robo.libras "Bom dia, Ana! Hoje tem aula de informática."
"""

import json
import os
import re
import sys
import unicodedata

PASTA_RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
EXTENSOES = (".gif", ".webp", ".png", ".jpg", ".jpeg", ".mp4", ".webm")
MAXIMO_DE_PALAVRAS_NO_SINAL = 3   # "bom dia", "muito obrigado", "ate logo"

# Palavras que a Libras não sinaliza (artigos, preposições, "ser/estar"...). Só na regra simples.
SEM_SINAL = {
    "o", "a", "os", "as", "um", "uma", "uns", "umas",
    "de", "do", "da", "dos", "das", "em", "no", "na", "nos", "nas", "por", "pelo", "pela",
    "ao", "aos", "para", "pra", "com", "e", "que",
    "e", "eh", "sao", "esta", "estao", "foi", "era", "sou", "somos", "estou", "estamos",
}


def normalizar(texto: str) -> str:
    """Minúsculas e sem acentos: "Informática" -> "informatica"."""
    texto = unicodedata.normalize("NFD", texto.lower())
    return "".join(c for c in texto if unicodedata.category(c) != "Mn")


def _chave(nome: str) -> str:
    """Nome de arquivo ou palavra -> chave de busca: "Bom_Dia" -> "bom dia"."""
    return " ".join(re.findall(r"[a-z0-9]+", normalizar(nome)))


class Libras:
    def __init__(self):
        from robo import config
        self.config = config
        self.pasta = os.path.join(PASTA_RAIZ, getattr(config, "LIBRAS_PASTA", "libras"))
        self.sinais = self._indexar("sinais")
        self.alfabeto = self._indexar("alfabeto")
        self.animacoes = set()      # sinais que o avatar 3D próprio sabe fazer (libras/animacoes/*.json)
        self._marcas = {}
        self.carregar_animacoes()
        self.tradutor = None
        self.api = None
        if getattr(config, "LIBRAS_API_LIGADA", True):
            from robo.vlibras_api import ClienteVLibras
            self.api = ClienteVLibras(config, os.path.join(self.pasta, "cache"), PASTA_RAIZ)
        if getattr(config, "LIBRAS_USAR_VLIBRAS", True):
            self._carregar_vlibras()
        print(f"[libras] {len(self.sinais)} sinal(is) e {len(self.alfabeto)} letra(s)/número(s) encontrados em {self.pasta}")
        print(f"[libras] avatar 3D próprio sabe {len(self.animacoes)} sinal(is) animado(s)")

    # ---------- sinais do avatar 3D próprio ----------
    ARQUIVOS_DE_ANIMACAO = ("sinais.json", "sinais_usuario.json")

    def carregar_animacoes(self, forcar=False):
        """Lê as chaves dos JSON de libras/animacoes. Só relê se algum arquivo mudou (o editor grava ali)."""
        marcas = {}
        for nome in self.ARQUIVOS_DE_ANIMACAO:
            caminho = os.path.join(self.pasta, "animacoes", nome)
            if os.path.isfile(caminho):
                marcas[caminho] = os.path.getmtime(caminho)
        if not forcar and marcas == self._marcas:
            return
        self._marcas, chaves = marcas, set()
        for caminho in marcas:
            try:
                with open(caminho, encoding="utf-8") as f:
                    chaves |= {_chave(k) for k in json.load(f) if not k.startswith("_")}
            except Exception as erro:
                print(f"[libras] não consegui ler {caminho}: {erro}")
        self.animacoes = chaves

    def _indexar(self, subpasta: str) -> dict:
        """chave -> caminho do arquivo (relativo à pasta libras, como o tablet vai pedir)."""
        achados = {}
        raiz = os.path.join(self.pasta, subpasta)
        if not os.path.isdir(raiz):
            return achados
        for nome in sorted(os.listdir(raiz)):
            base, extensao = os.path.splitext(nome)
            if extensao.lower() in EXTENSOES:
                achados.setdefault(_chave(base), f"{subpasta}/{nome}")
        return achados

    def _carregar_vlibras(self):
        try:
            import vlibras_translate
            self.tradutor = vlibras_translate.translation.Translation()
            print("[libras] usando o vlibras_translate para montar a glosa")
        except Exception as erro:   # não instalado, sem Java, sem hunspell...
            print(f"[libras] vlibras_translate indisponível ({type(erro).__name__}); usando a regra simples")

    # ---------- 1. texto -> glosa ----------
    def glosa(self, texto: str) -> list:
        """Lista de palavras da glosa, em maiúsculas: ["BOM", "DIA", "ANA"]."""
        if self.api is not None:
            da_api = self.api.glosa(texto)
            if da_api:
                return da_api.split()
        if self.tradutor is not None:
            try:
                saida = self.tradutor.rule_translation(texto)
                palavras = [p for p in str(saida).split() if not (p.startswith("[") and p.endswith("]"))]
                if palavras:
                    return palavras
            except Exception as erro:
                print(f"[libras] o vlibras_translate falhou ({erro}); usando a regra simples")
        return self._glosa_simples(texto)

    @staticmethod
    def _glosa_simples(texto: str) -> list:
        palavras = re.findall(r"[\wÀ-ÿ]+", texto.lower())
        uteis = [p for p in palavras if normalizar(p) not in SEM_SINAL]
        return [p.upper() for p in (uteis or palavras)]

    # ---------- 2 e 3. glosa -> sinais ou letras ----------
    def _url(self, caminho: str) -> str:
        return "/libras/" + caminho

    def _soletrar(self, palavra: str) -> dict:
        letras = []
        for c in normalizar(palavra):
            if c.isalnum():
                letras.append({"letra": c.upper(), "url": self._url(self.alfabeto[c]) if c in self.alfabeto else None})
        return {"palavra": palavra, "modo": "letras", "letras": letras}

    def montar(self, glosa: list) -> list:
        itens, i = [], 0
        while i < len(glosa):
            for tamanho in range(min(MAXIMO_DE_PALAVRAS_NO_SINAL, len(glosa) - i), 0, -1):
                trecho = glosa[i:i + tamanho]
                chave = _chave(" ".join(trecho))
                if chave in self.animacoes:
                    itens.append({"palavra": " ".join(trecho), "modo": "animacao", "chave": chave})
                    i += tamanho
                    break
                caminho = self.sinais.get(chave)
                if caminho:
                    itens.append({"palavra": " ".join(trecho), "modo": "sinal", "url": self._url(caminho)})
                    i += tamanho
                    break
            else:
                itens.append(self._soletrar(glosa[i]))
                i += 1
        return itens

    def usa_video(self) -> bool:
        """Vai pedir o vídeo do avatar à API? (o robô avisa o tablet para mostrar "gerando...")"""
        return bool(self.api and self.api.video_ligado and self.api.disponivel())

    def traduzir(self, texto: str, com_video=True) -> dict:
        """Tudo que o tablet precisa para mostrar a frase em Libras.
        com_video=False: não pede o vídeo do avatar (a tela usa o avatar 3D próprio)."""
        self.carregar_animacoes()
        glosa = self.glosa(texto)
        itens = self.montar(glosa)
        c = self.config
        video = self.api.video(" ".join(glosa)) if (self.api and com_video) else None
        return {"frase": texto.strip(), "glosa": " ".join(glosa), "itens": itens,
                "video": self._url(video) if video else None,
                "segundos_por_sinal": getattr(c, "LIBRAS_SEGUNDOS_POR_SINAL", 2.0),
                "segundos_por_letra": getattr(c, "LIBRAS_SEGUNDOS_POR_LETRA", 1.0),
                "segundos_depois": getattr(c, "LIBRAS_SEGUNDOS_DEPOIS", 30)}


# ---- Teste: python -m robo.libras "Bom dia, Ana!" ----
if __name__ == "__main__":
    from robo import config  # noqa: F401  (só para falhar cedo se o config estiver quebrado)
    libras = Libras()
    resultado = libras.traduzir(" ".join(sys.argv[1:]) or "Bom dia, Ana! Hoje tem aula de informática.")
    print("glosa:", resultado["glosa"])
    for item in resultado["itens"]:
        if item["modo"] == "animacao":
            print(f"  3D      {item['palavra']:<14} (avatar 3D próprio)")
        elif item["modo"] == "sinal":
            print(f"  SINAL   {item['palavra']:<14} {item['url']}")
        else:
            faltam = [l["letra"] for l in item["letras"] if not l["url"]]
            print(f"  SOLETRA {item['palavra']:<14} {len(item['letras'])} letras" + (f"  (sem imagem: {''.join(faltam)})" if faltam else ""))
