# Robô Byte Libras: tela com avatar 3D

Fala em português → texto (Parakeet, offline, na B13) → glosa → **avatar 3D** no tablet, com a frase ouvida e a glosa na tela.

## O que há de novo (copie por cima do robo-assistente-b13, mantendo as pastas)

```text
robo/config.py          + LIBRAS_MODO_DEDICADO, LIBRAS_AVATAR, LIBRAS_FILA_MAXIMA, LIBRAS_EDITOR_LIGADO (no final)
robo/escuta.py          ouvido contínuo (corta frases pelo silêncio; não usa o Vosk)
robo/robo_libras.py     robô enxuto: escuta → fila → Parakeet → Libras → tablet
robo/libras.py          + sinais animados do avatar 3D e traduzir(texto, com_video)
robo/servidor.py        escolhe o robô, serve libras_tela/, grava sinais do editor
libras_tela/            index.html, estilo.css, app.js, avatar.js, editor.html
libras/animacoes/       alfabeto.json, sinais.json (+ *_usuario.json, criados pelo editor)
ferramentas/baixar_three.py
tests/test_libras_tela.py
```

Não precisa mexer em `robo.py`, `rosto/`, `vlibras_api.py`. O `rosto/` original continua valendo no robô completo.

## Instalar

```bash
.venv/bin/python ferramentas/baixar_three.py   # uma vez, com internet: guarda o Three.js na B13
systemctl restart robo-byte
```

No tablet (cabo USB, como no projeto base), abra `http://localhost:8000`, toque em **Começar** e permita o microfone.
Sem o `baixar_three.py` o tablet tenta o Three.js pela internet dele; sem os dois, a tela cai para imagens/letras.

## Dois jeitos de mostrar o sinal (`LIBRAS_AVATAR`)

| Valor | Quem sinaliza | Vocabulário | Internet |
| --- | --- | --- | --- |
| `"vlibras"` (padrão) | Vídeo do avatar 3D clássico do VLibras, gerado pela API | Completo | Precisa. Sem ela, usa o avatar próprio |
| `"3d"` | Avatar 3D próprio, desenhado no tablet (WebGL) | Só o que estiver em `libras/animacoes/` | Não precisa |

O contrato da API do VLibras continua **não confirmado** (veja `ferramentas/testar_vlibras_api.py`). Se falhar, a tela usa o avatar próprio sozinha.

## Modo dedicado

`LIBRAS_MODO_DEDICADO = True` (padrão): o robô só traduz. Não carrega IA, Piper, OpenCV nem Vosk, e **não precisa de chave do Gemini nem de "ei robô"**. Escuta o tempo todo e continua gravando a próxima frase enquanto traduz a anterior (até `LIBRAS_FILA_MAXIMA`). Com `False`, volta o robô completo e a tela de Libras fica em `/libras-tela/`.

## O que você precisa saber antes de usar em aula

- **O avatar próprio só sabe o alfabeto manual.** As formas das letras em `alfabeto.json` são **aproximadas e não foram revisadas por falante de Libras** (M, N, S, T e E, por exemplo, são parecidas demais). Palavras fora do alfabeto são soletradas, ou saem no vídeo do VLibras.
- **Revise e grave os sinais com um intérprete ou professor surdo** no `editor.html` (link "Editor de sinais" na tela). Ali você ajusta posição das mãos, dedos e rosto, monta os quadros, toca e salva em `sinais_usuario.json` / `alfabeto_usuario.json`. Gravar só funciona a partir da própria B13.
- **Rosto e corpo importam na Libras.** O avatar próprio tem sobrancelhas, boca e cabeça controláveis por quadro, mas é um modelo simples. Trate como apoio, não como intérprete.
- No vídeo do VLibras, a palavra destacada avança em ritmo igual, porque a API não informa o tempo de cada sinal. É aproximado.

## Formato de um sinal (`libras/animacoes/sinais*.json`)

```json
"bom dia": { "quadros": [
  { "t": 0.0, "d": { "p": [0.12, 0.30, 0.30], "o": [0,0,0], "f": [0,0,0,0,0], "a": 0 }, "e": null,
    "r": { "sb": 0.3, "boca": 0, "cab": [0,0,0] } },
  { "t": 0.7, "d": { "p": [0.12, 0.10, 0.35], "f": [0,0,0,0,0] } }
]}
```

`d`/`e` = mão direita/esquerda (nula = repouso). `p` = pulso em metros do ponto de vista de quem sinaliza [direita, cima, frente], a partir do peito. `o` = [inclinação, giro, rolagem] em graus. `f` = dobra de [polegar, indicador, médio, anelar, mínimo], de 0 a 1. `a` = abertura entre os dedos (-1 a 1). `r` = rosto. `t` = segundos. Palavras com mais de uma palavra usam espaço: `"bom dia"`.

## Como a tela se comporta

Frase ouvida e glosa aparecem na hora; a palavra atual fica destacada. Botões: pausar escuta, repetir, velocidade, tela cheia. Há um campo para **digitar** uma frase (teste sem microfone). Tocar numa frase do histórico repete.

## Testes

```bash
python -m unittest tests.test_libras_tela -v      # escuta, glosa/animações e o fluxo do robô, sem hardware
```

## Estado do que foi verificado

- Python (escuta, libras, fluxo do robô): testado, passa.
- JavaScript: só checagem de sintaxe. **O avatar 3D, a captura do microfone e a tela não foram executados** (sem navegador nem Three.js neste ambiente). Espere ajustes de proporção/posição das mãos ao ver o modelo pela primeira vez; o editor serve para isso.
- Nada foi medido na B13 nem no tablet Android 7 (WebGL, desempenho, memória).
