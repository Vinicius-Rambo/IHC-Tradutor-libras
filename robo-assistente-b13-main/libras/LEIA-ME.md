# Modo Libras do Robô Byte

A fala vira sinais na tela do tablet. Tudo que é reconhecimento de voz continua rodando **na B13, sem internet**
(Parakeet). A internet só é necessária se você usar a Wikipédia/Gemini nas outras funções do robô.

## Como usar

| Diga | O que acontece |
| --- | --- |
| "Ei robô" ... "modo Libras" | Liga o modo: tudo que for dito vira sinais. O robô não volta a dormir. |
| "Traduz para Libras bom dia" | Traduz só essa frase e continua no modo normal. |
| "Como se diz obrigado em Libras?" | Idem. |
| "Sair do modo Libras" | Volta a conversar normalmente. |

Na tela: toque para repetir a frase; o **✕** fecha o painel.

## Pastas (você precisa preencher)

```text
libras/
├── alfabeto/   a.png ... z.png  e  0.png ... 9.png     (alfabeto manual: usado para soletrar nomes)
└── sinais/     oi.gif  bom_dia.mp4  aula.png  ...      (um arquivo por sinal)
```

- Formatos: `.gif .webp .png .jpg .mp4 .webm`. O nome do arquivo é a palavra, sem acento; use `_` para várias palavras
  (`bom_dia`, `ate_logo`). Frases com mais palavras têm prioridade ("bom dia" vira um sinal só).
- Palavra sem sinal na pasta é **soletrada** com o alfabeto. Sem imagem da letra, a tela mostra a letra escrita.
- Ver o que falta: `.venv/bin/python -m robo.libras "sua frase aqui"`.

### De onde vêm as imagens

O repositório **não traz** imagens de sinais, porque a maioria tem direitos autorais. Caminhos seguros:

1. **Gravar com a comunidade surda da escola** (intérprete, professor de Libras, alunos surdos), com autorização
   de uso de imagem. Fica melhor que qualquer banco genérico e dá ao projeto o vocabulário da sua sala de aula.
2. **Alfabeto manual** com licença livre (Wikimedia Commons, Creative Commons). Confira a licença e guarde o crédito do autor.
3. **Bancos de sinais de outros sites** (dicionários, universidades, Spread the Sign): só com autorização de quem mantém.

Comece pelo alfabeto + 50 a 100 palavras da aula (informática: computador, mouse, teclado, tela, internet, salvar...).

## Glosa (tradução de verdade) com o VLibras

Libras não é português sinalizado: a ordem e as palavras mudam. Por padrão o robô usa uma **regra simples** (tira
artigos e preposições). Para a glosa completa, instale o pacote `vlibras-translate` (Suíte VLibras, LAVID/UFPB, LGPLv3):

```bash
apt install -y default-jre-headless libhunspell-dev
.venv/bin/pip install vlibras-translate
systemctl restart robo-byte
```

Atenção: a documentação do pacote pede Java 8 e a B13 tem só 2 GB de memória e processador ARM. **Teste antes** e
observe com `free -h`. Se não funcionar, o robô avisa no log e continua com a regra simples.

## Evolução: avatar 3D

Para sinalizar palavras que você não tem em imagem, dá para usar o avatar do VLibras no tablet (script
`https://vlibras.gov.br/app/vlibras-plugin.js`, precisa de internet e de um tablet com WebGL razoável). Seria uma segunda
etapa: em vez de imagens, o painel chamaria o player do VLibras com o texto.

## API do VLibras: sinais gerados por código (recomendado para o tablet Android 7)

O Chrome do Android 7 parou na versão 119 e um tablet desse porte não aguenta o avatar 3D no navegador (WebGL).
Por isso o robô pede o **vídeo do avatar** ao serviço do VLibras e o tablet só toca um MP4:

```text
texto ──▶ POST /translate ──▶ glosa ──▶ POST /video ──▶ MP4 do avatar ──▶ tablet (tag <video>)
```

- Os vídeos ficam em `libras/cache/` (limite `LIBRAS_CACHE_MAX_MB`, 300 MB). A mesma frase de novo toca na hora, sem internet.
- Sem internet ou com erro: a API é pausada por 60 s e o robô usa as imagens de `libras/` ou soletra. A conversa não trava.
- **Confirme o contrato antes de contar com ele.** O endereço (`traducao2.vlibras.gov.br`) e os campos vêm de um projeto de
  terceiros, não de documentação oficial, e o `/video` pode exigir chave. Rode na B13:

```bash
.venv/bin/python ferramentas/testar_vlibras_api.py "bom dia, Ana"
```

  Se pedir chave, salve em `chave_vlibras.txt`. Se o campo do pedido for outro, ajuste `LIBRAS_API_CAMPO_VIDEO`.
- **Privacidade:** com a API ligada, o texto das frases vai para o servidor do VLibras (governo federal). O áudio continua na B13.
  Antes de usar em sala, veja os termos de uso do serviço e, se for uso contínuo, fale com a equipe do VLibras (LAViD/UFPB).
  Para desligar: `LIBRAS_API_LIGADA = False`.
