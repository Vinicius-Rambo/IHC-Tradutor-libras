# Robô Byte Libras: da fala para os sinais, em hardware pequeno

Extensão do [robo-assistente-b13](https://github.com/marcosroquerosa/robo-assistente-b13) que ouve a fala em português do Brasil e mostra **sinais de Libras** na tela de um tablet. A **TV box BTV B13** faz o trabalho pesado e o **tablet** é a interface (tela, microfone e caixa de som).

A fala é entendida **na própria B13, sem internet**. No modo Libras o robô não usa a IA da web nem a câmera, então o consumo fica baixo.

> **Estado do projeto:** a lógica foi testada em computador comum. Os ajustes de memória abaixo são recomendações e ainda precisam ser conferidos na B13 real.

## O que ele faz

- **Traduz a fala em sinais:** cada frase vira uma sequência de imagens ou vídeos, um sinal por vez, com a palavra atual destacada.
- **Soletra o que não tem sinal:** nomes próprios e palavras fora do vocabulário saem em alfabeto manual (datilologia).
- **Nunca quebra:** se faltar a imagem de uma letra, a tela mostra a letra escrita.
- **Funciona por voz:** "modo Libras" liga, "sair do modo Libras" desliga. Toque na tela para repetir a frase.

## Como funciona

```text
Tablet (microfone) ──áudio──▶ B13
                               │ 1. Parakeet int8: fala vira texto      (offline)
                               │ 2. Texto vira glosa                    (regra simples, ou VLibras)
                               │ 3. Glosa vira lista de imagens/vídeos  (pasta libras/)
Tablet (tela)      ◀──sinais───┘
```

A **glosa** é a frase reescrita na gramática da Libras ("Maria comprou uma casa" vira `MARIA COMPRAR CASA`). A Libras não é o português sinalizado.

## Equipamentos

| Aparelho | Modelo | Papel |
| --- | --- | --- |
| TV box | BTV B13 (Amlogic S905X4, 4 núcleos ARM, 2 GB de memória, 16 GB internos) com Debian 13 | Roda o programa e o reconhecimento de fala |
| Tablet | Samsung com Android 7, Chrome (no máximo a versão 119) e depuração USB | Toca os vídeos dos sinais e capta o som |
| Cabo USB | De dados, ligado à B13 | Leva os dados e abre o `localhost` no tablet |

A instalação do Debian na B13 e a configuração do Android são as mesmas do projeto base: [LEIA-ME-B13.md](LEIA-ME-B13.md) e [CONFIGURAR-CELULAR.md](CONFIGURAR-CELULAR.md).

## Rodando em hardware pequeno

A B13 tem só 2 GB de memória, então o jeito é cortar tudo que o modo Libras não usa.

| Ajuste | Onde | Por quê |
| --- | --- | --- |
| `VISAO_LIGADA = False` | `robo/config.py` | Libras não usa a câmera. Desligar poupa processador e memória. |
| `MOTOR_ENTENDIMENTO = "parakeet"` com `PARAKEET_QUANTIZACAO = "int8"` | `robo/config.py` | Já é o padrão. A versão completa do Parakeet não cabe na B13. |
| Não instalar o `vlibras-translate` de início | `requirements.txt` | O pacote é pesado e pede Java. Comece com a regra simples e teste o VLibras depois. |
| Imagens leves | `libras/` | GIF ou WebP de até uns 480 px e vídeos MP4 em 480p. Arquivos grandes demoram no cabo USB e pesam no tablet. |
| Frases curtas | no uso | `SEGUNDOS_MAXIMOS_DE_FALA` limita a fala a 25 s. Falar uma frase por vez reduz o tempo de espera. |
| Zram (opcional) | sistema | `apt install -y zram-tools` cria memória compactada e ajuda quando falta RAM. |
| Sem chave do Gemini | `chave_web.txt` | No modo Libras a IA da web não é usada. Ela só é necessária para as outras funções do robô. Não testei iniciar sem a chave. |

Para acompanhar a saúde da B13 enquanto testa:

```bash
free -h                                          # memória livre
cat /sys/class/thermal/thermal_zone0/temp        # temperatura, em milésimos de grau
journalctl -u robo-byte -f | grep -E "ouvi:|libras|tempo"
```

## Instalação

Com o projeto base instalado (`bash instalar.sh`), copie estes arquivos por cima dele, mantendo as pastas:

```text
robo/libras.py      robo/comandos.py    robo/robo.py     robo/servidor.py     robo/config.py
rosto/              libras/             requirements.txt
```

Depois, reinicie o robô:

```bash
systemctl restart robo-byte
```

## Sinais gerados pela API do VLibras

Como o tablet é antigo, o robô pede à API do VLibras o **vídeo do avatar** (`/translate` para a glosa e `/video` para o MP4) e o tablet só toca o arquivo. Os vídeos ficam em `libras/cache/` (até 300 MB). Sem internet, o robô usa as imagens da pasta `libras/` ou soletra.

O contrato da API foi descrito por um projeto de terceiros e **ainda não foi confirmado**. Rode `.venv/bin/python ferramentas/testar_vlibras_api.py "bom dia"` na B13 e ajuste os `LIBRAS_API_*` do `config.py`. Detalhes em `libras/LEIA-ME.md`.

## Imagens dos sinais (reserva)

O projeto **não traz** imagens de sinais, porque a maioria tem direitos autorais. Preencha estas pastas:

```text
libras/
├── alfabeto/   a.png ... z.png  e  0.png ... 9.png     (para soletrar)
└── sinais/     oi.gif  bom_dia.mp4  aula.png  ...      (um arquivo por sinal)
```

- Formatos aceitos: `.gif .webp .png .jpg .mp4 .webm`.
- O nome do arquivo é a palavra, sem acento. Use `_` entre palavras: `bom_dia`, `ate_logo`.
- Comece pelo alfabeto e por 50 a 100 palavras da sua aula.
- O melhor caminho é gravar com a comunidade surda da escola (intérprete, professor de Libras, alunos), com autorização de uso de imagem. Se usar imagens de terceiros, confira a licença e guarde o crédito.

## Como usar

Teste à mão: ligue o tablet no cabo, rode `./iniciar.sh` e abra `http://localhost:8000` no Chrome do tablet. Toque na tela e permita o microfone.

| Diga | O que acontece |
| --- | --- |
| "Ei robô, modo Libras" | Liga o modo. O robô não volta a dormir e traduz tudo que ouvir. |
| "Traduz para Libras bom dia" | Traduz só essa frase. |
| "Como se diz obrigado em Libras?" | Idem. |
| "Sair do modo Libras" | Volta a conversar normalmente. |

Para ligar sozinho com a B13: `./ativar_modo_automatico.sh`.

## Configurações do modo Libras

Ficam no final de `robo/config.py`. Depois de mudar, rode `systemctl restart robo-byte`.

| Ajuste | Padrão | Para que serve |
| --- | --- | --- |
| `LIBRAS_LIGADO` | `True` | Liga ou desliga o recurso |
| `LIBRAS_PASTA` | `"libras"` | Onde ficam `sinais/` e `alfabeto/` |
| `LIBRAS_USAR_VLIBRAS` | `True` | Usa o `vlibras-translate` se estiver instalado; senão, regra simples |
| `LIBRAS_SEGUNDOS_POR_SINAL` | 2.0 | Tempo de cada sinal na tela |
| `LIBRAS_SEGUNDOS_POR_LETRA` | 1.0 | Tempo de cada letra soletrada |
| `LIBRAS_SEGUNDOS_DEPOIS` | 30 | A tela some sozinha depois do último sinal |

## Comandos úteis

Rode como `root`, na pasta do projeto.

| Para | Comando |
| --- | --- |
| Ver a glosa de uma frase e o que falta nas pastas | `.venv/bin/python -m robo.libras "Bom dia, Ana!"` |
| Ver qual comando uma frase vira | `.venv/bin/python -m robo.comandos` |
| Ver o que o robô está fazendo | `journalctl -u robo-byte -f` |
| Conferir o tablet no cabo | `adb devices` |

## Glosa completa com o VLibras (opcional)

O pacote [`vlibras-translate`](https://pypi.org/project/vlibras-translate/), da Suíte VLibras (LAVID/UFPB, LGPLv3), faz a tradução para glosa de verdade. Sua documentação pede Java e hunspell:

```bash
apt install -y default-jre-headless libhunspell-dev
.venv/bin/pip install vlibras-translate
systemctl restart robo-byte
```

Teste com `free -h` aberto. Se faltar memória ou o pacote não rodar em ARM, desinstale e fique com a regra simples. O robô avisa no log qual das duas está em uso.

## Estrutura do que foi adicionado

```text
robo-assistente-b13/
├── robo/libras.py         texto → glosa → sinais ou letras
├── robo/comandos.py       + comandos "modo Libras" e "traduz para Libras"
├── robo/robo.py           + modo Libras (não chama a IA, só mostra os sinais)
├── robo/servidor.py       + entrega as imagens da pasta libras/
├── rosto/                 + painel de sinais no tablet
└── libras/                imagens e vídeos dos sinais (você preenche)
```

## Privacidade

- **Áudio:** nunca sai da B13 e não é gravado.
- **Texto:** com `LIBRAS_API_LIGADA = True`, o texto das frases vai para o servidor do VLibras (governo federal) para gerar o vídeo do avatar. Com `False`, nada sai da B13.
- **Imagens dos sinais:** ficam na pasta `libras/` e são servidas só pelo cabo, ao tablet.

Avise a turma e a escola de que o robô escuta.

## Créditos

- [robo-assistente-b13](https://github.com/marcosroquerosa/robo-assistente-b13): projeto base.
- [VLibras](https://pypi.org/project/vlibras-translate/) (LAVID/UFPB): tradução opcional de português para glosa.
