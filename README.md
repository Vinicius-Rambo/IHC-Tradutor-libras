# Robô Byte Libras: stack e plano do projeto

Assistente de fala que converte a fala comum em português (pt-BR) em **sinais de Libras** na tela de um tablet, rodando em **hardware pequeno** (TV box BTV B13 + tablet Android). A base é o repositório [robo-assistente-b13](https://github.com/marcosroquerosa/robo-assistente-b13).

> **Este documento é um plano.** Marca o que já tem protótipo (✅), o que é proposta (🟡) e o que depende de uma decisão (❓). Nada aqui foi testado no hardware real.

## 1. Objetivo e escopo

**Direção da tradução:** fala em português → sinais em Libras (uma pessoa ouvinte fala, a pessoa surda lê os sinais na tela).

**Dentro do escopo**
- Reconhecer a fala em pt-BR, offline, na B13.
- Converter o texto em glosa Libras.
- Mostrar os sinais (imagens ou vídeos) e soletrar o que não tiver sinal.
- Funcionar em sala de aula, com 2 GB de memória.

**Fora do escopo (por enquanto)**
- Libras → português (reconhecer sinais pela câmera).
- Tradução perfeita: a Libras tem gramática, expressão facial e espaço próprios, e imagens isoladas só aproximam isso.

## 2. Visão geral da arquitetura

```text
 ┌───────── TABLET (Android + Chrome) ─────────┐        ┌────────── B13 (Debian 13) ──────────┐
 │  Microfone ── áudio ─────────────────────────┼─USB──▶│ Vosk (palavra de ativação)          │
 │                                              │ cabo  │ Parakeet int8 (fala → texto)        │
 │  Painel de sinais ◀── lista de sinais (JSON)─┼◀──────│ Glosa (regra simples ou VLibras)    │
 │  Imagens/vídeos ◀── arquivos estáticos ──────┼◀──────│ Pasta libras/ (sinais, alfabeto)    │
 └──────────────────────────────────────────────┘       └─────────────────────────────────────┘
          página HTML em http://localhost:8000 (adb reverse)          FastAPI + WebSocket
```

A B13 faz o trabalho pesado. O tablet só capta o som e desenha. A conexão por cabo (`adb reverse`) existe porque o Chrome só libera o microfone em `localhost` ou HTTPS.

## 3. Stack

### 3.1 Hardware e sistema

| Camada | Escolha | Status | Observação |
| --- | --- | --- | --- |
| Computador | BTV B13 (Amlogic S905X4, 4 núcleos ARM, 2 GB RAM, 16 GB) | ✅ base | O limite de 2 GB decide quase todas as outras escolhas |
| Sistema | Debian 13 na memória interna | ✅ base | Wi-Fi e Bluetooth internos não funcionam; usar cabo de rede ou adaptador USB |
| Tablet | Samsung, Android 7, Chrome até a versão 119 | ✅ definido | Sem WebGL confiável: tocar vídeo MP4, não rodar o avatar no navegador |
| Ligação | Cabo USB + `adb reverse` | ✅ base | Alternativa por rede exige HTTPS por causa do microfone |

### 3.2 Backend (B13)

| Parte | Tecnologia | Status | Para que serve |
| --- | --- | --- | --- |
| Linguagem | Python | ✅ | Todo o programa |
| Servidor | FastAPI + Uvicorn | ✅ | Entrega a página e as imagens, e abre o WebSocket |
| Tempo real | WebSocket | ✅ | Áudio do tablet para a B13 e sinais da B13 para o tablet |
| Palavra de ativação | Vosk (modelo pequeno pt) | ✅ base | Fica ouvindo gastando pouco |
| Fala → texto | Parakeet TDT 0.6B v3 `int8`, via onnx-asr | ✅ base | Offline. Alternativa mais leve: Whisper (faster-whisper) |
| Texto → glosa (API) | VLibras `/translate` | ✅ protótipo | Primeira opção; cai para as de baixo sem internet |
| Texto → glosa | Regra simples própria | ✅ protótipo | Tira artigos, preposições e "ser/estar". Não reordena frases |
| Texto → glosa (melhor) | `vlibras-translate` (VLibras, LGPLv3) | 🟡 opcional | Pede Java e hunspell; risco em ARM e 2 GB |
| Glosa → vídeo do avatar | `robo/vlibras_api.py` (`/translate` e `/video`) | ✅ protótipo | Contrato não oficial: confirmar com `testar_vlibras_api.py`; cache em disco |
| Glosa → sinais | `robo/libras.py` | ✅ protótipo | Procura em `libras/sinais/`, depois soletra com `libras/alfabeto/` |
| Comandos de voz | `robo/comandos.py` (expressões regulares) | ✅ protótipo | "modo Libras", "traduz para Libras ..." |
| Início automático | systemd (serviço `robo-byte`) | ✅ base | Liga com a B13 e religa se cair |

O que **não** é usado no modo Libras: Gemini, Piper (voz), OpenCV e detector de mãos. Dá para desligar a visão (`VISAO_LIGADA = False`) para poupar memória.

### 3.3 Frontend (tablet)

| Parte | Tecnologia | Status |
| --- | --- | --- |
| Página | HTML, CSS e JavaScript puros, no Chrome | ✅ |
| Painel de sinais | Sequência de imagens ou vídeos com a palavra atual destacada | ✅ protótipo |
| Interação | Tocar repete a frase; ✕ fecha | ✅ protótipo |
| Avatar 3D | Vídeo MP4 gerado pela API do VLibras e tocado em `<video>` | ✅ protótipo (contrato da API a confirmar) |

### 3.4 Conteúdo (o ponto mais importante do projeto)

| Item | Proposta | Status |
| --- | --- | --- |
| Alfabeto manual | `a.png ... z.png`, `0.png ... 9.png` | ❓ falta obter |
| Sinais de palavras | Um arquivo por sinal em `libras/sinais/` | ❓ falta obter |
| Formatos | `.gif .webp .png .jpg .mp4 .webm`, até ~480 px | ✅ aceitos pelo código |
| Metadados e crédito | Um `manifesto.json` com autor, licença e origem de cada arquivo | 🟡 proposta |

A qualidade da tradução depende mais do **vocabulário disponível** do que do código. O projeto não traz imagens, porque a maioria tem direitos autorais.

## 4. Como vamos construir (fases)

| Fase | Entrega | Pronto quando |
| --- | --- | --- |
| 0. Base | Projeto base rodando na B13 com o tablet | O robô conversa por voz hoje |
| 1. Protótipo ✅ | Modo Libras com regra simples, alfabeto e painel | Fala vira letras e sinais na tela |
| 2. Conteúdo | Alfabeto + 50 a 100 palavras da aula | Frases do dia a dia saem com poucos soletrados |
| 3. Medição | Teste de memória, temperatura e tempo de resposta na B13 | Resposta em poucos segundos sem estourar a RAM |
| 4. Qualidade | Glosa melhor (VLibras), correção de erros de fala, revisão com falantes de Libras | Surdos da escola entendem e aprovam |
| 5. Extras | Avatar 3D, mais vocabulário, modo offline total | Conforme a necessidade |

**Como medir o sucesso:** porcentagem de palavras de uma aula que têm sinal (cobertura), tempo entre o fim da fala e o primeiro sinal na tela, e a avaliação de pessoas surdas e de intérpretes.

## 5. Riscos

| Risco | Impacto | O que fazer |
| --- | --- | --- |
| 2 GB de memória | Robô trava ou reinicia | Desligar visão e IA da web, imagens leves, zram, medir cedo |
| Falta de vocabulário | Muita soletração e pouco sinal | Gravar o vocabulário da aula primeiro |
| Direitos autorais dos sinais | Problema legal | Gravar com a comunidade surda, com autorização por escrito |
| Libras ≠ português sinalizado | Tradução considerada pobre ou errada | Revisar com intérprete e deixar claro que é apoio, não substituto |
| Erros do reconhecimento de fala | Sinal errado na tela | Mostrar a frase ouvida junto com os sinais, para a pessoa conferir |
| VLibras pesado em ARM | Não instala ou trava | Manter a regra simples como reserva |
| Tablet sem cabo | Sem microfone no Chrome | Seguir o `adb reverse` ou configurar HTTPS |

## 6. Decisões em aberto (preciso da sua opinião)

1. **Forma de mostrar o sinal:** decidido pelo caminho do vídeo do avatar via API (funciona no tablet antigo). Falta confirmar se a API aceita o uso e se exige chave. As imagens ficam só como reserva offline.
2. **Quem fornece os sinais:** vocês vão gravar com alguém da escola ou da comunidade surda? Já existe um banco de imagens autorizado?
3. **Glosa:** a regra simples basta para a primeira turma, ou queremos o VLibras já na fase 1?
4. **Vocabulário inicial:** só informática ou uso geral de sala de aula?
5. **Quem fala e quem lê:** o professor fala e o aluno surdo lê no tablet. Essa é a situação principal? O tablet fica na mesa do aluno ou na frente da sala?
6. **Internet:** a escola tem rede estável? Isso decide se o avatar é viável.
7. ~~Tablet~~ Definido: Samsung com Android 7. Falta o modelo exato (memória e tamanho da tela) e a versão do Chrome instalada.
8. **Ativação:** palavra "ei robô" ou o modo Libras fica sempre ligado durante a aula?

## 7. Estrutura do repositório (proposta)

```text
robo-assistente-b13/
├── robo/
│   ├── libras.py          texto → glosa → sinais ou letras            ✅
│   ├── comandos.py        + comandos de Libras                        ✅
│   ├── robo.py            + modo Libras                               ✅
│   ├── servidor.py        + entrega de libras/                        ✅
│   └── config.py          + ajustes LIBRAS_*                          ✅
├── rosto/                 painel de sinais no tablet                  ✅
├── libras/
│   ├── alfabeto/          a.png ... z.png                             ❓ conteúdo
│   ├── sinais/            oi.gif, bom_dia.mp4, ...                    ❓ conteúdo
│   └── manifesto.json     autor, licença e origem de cada arquivo     🟡
├── tests/                 testes da glosa e do mapeamento             🟡
└── ferramentas/
    └── cobertura.py       diz que palavras da aula ainda não têm sinal 🟡
```

## 8. Créditos

- [robo-assistente-b13](https://github.com/marcosroquerosa/robo-assistente-b13): projeto base.
- [VLibras](https://pypi.org/project/vlibras-translate/) (LAVID/UFPB): tradução opcional de português para glosa.
