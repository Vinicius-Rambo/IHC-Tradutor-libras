/* TELA DE LIBRAS: conexão com a B13, microfone, texto na tela e avatar (vídeo do VLibras ou 3D próprio). */
(function () {
  "use strict";
  var $ = function (id) { return document.getElementById(id); };
  var ws = null, avatar = null, config = { avatar: "vlibras", editor: false };
  var ANIM = { sinais: {}, alfabeto: {} };
  var fila = [], tocando = false, geracao = 0, ultima = null, pausado = false, microfoneLigado = false;
  var velocidade = 1, temporizadorDeLimpeza = null;
  try { velocidade = parseFloat(localStorage.getItem("libras_velocidade")) || 1; } catch (e) {}
  $("velocidade").value = velocidade;

  function esperar(s) { return new Promise(function (r) { setTimeout(r, s * 1000); }); }
  function chave(t) {
    return String(t).toLowerCase().normalize("NFD").replace(/[\u0300-\u036f]/g, "").match(/[a-z0-9]+/g) || [];
  }

  // ---------- scripts ----------
  function carregar(url) {
    return new Promise(function (ok, erro) {
      var s = document.createElement("script"); s.src = url; s.onload = ok; s.onerror = erro;
      document.head.appendChild(s);
    });
  }
  function iniciarAvatar() {
    return carregar("vendor/three.min.js")
      .catch(function () { return carregar("https://cdnjs.cloudflare.com/ajax/libs/three.js/r128/three.min.js"); })
      .then(function () { return carregar("avatar.js"); })
      .then(function () { avatar = new window.Avatar3D($("avatar")); })
      .catch(function (e) { console.warn("sem avatar 3D:", e); })
      .then(function () {
        if (!avatar || !avatar.ok) { avatar = null; $("avatar").hidden = true; $("sem3d").hidden = false; }
      });
  }

  // ---------- animações do avatar 3D ----------
  function lerJson(url) {
    return fetch(url, { cache: "no-store" }).then(function (r) { return r.ok ? r.json() : {}; }).catch(function () { return {}; });
  }
  function limpar(o) { var n = {}; for (var k in o) if (k.charAt(0) !== "_") n[k] = o[k]; return n; }
  function carregarAnimacoes() {
    return Promise.all(["alfabeto", "alfabeto_usuario", "sinais", "sinais_usuario"].map(function (n) {
      return lerJson("/libras/animacoes/" + n + ".json");
    })).then(function (r) {
      ANIM.alfabeto = Object.assign({}, limpar(r[0]), limpar(r[1]));
      ANIM.sinais = {};
      var s = Object.assign({}, limpar(r[2]), limpar(r[3]));
      for (var k in s) ANIM.sinais[chave(k).join(" ")] = s[k];
    });
  }

  // ---------- conexão ----------
  function conectar() {
    ws = new WebSocket((location.protocol === "https:" ? "wss://" : "ws://") + location.host + "/ws");
    ws.binaryType = "arraybuffer";
    ws.onopen = function () { chip("ouvindo", "Conectado"); if (pausado) enviar({ tipo: "pausar", ligado: true }); };
    ws.onclose = function () { chip("off", "Sem conexão"); setTimeout(conectar, 1500); };
    ws.onmessage = function (e) {
      if (typeof e.data !== "string") return tocarFalaDoRobo(e.data);
      var m; try { m = JSON.parse(e.data); } catch (x) { return; }
      receber(m);
    };
  }
  function enviar(o) { if (ws && ws.readyState === 1) ws.send(JSON.stringify(o)); }
  function chip(classe, texto) { var c = $("estado"); c.className = "chip " + classe; c.textContent = texto; }

  function receber(m) {
    if (m.tipo === "estado") {
      var t = { ouvindo: "Ouvindo", pensando: "Traduzindo", dormindo: "Pausado", falando: "Falando" };
      chip(m.estado, t[m.estado] || m.estado);
    } else if (m.tipo === "libras_config") {
      config = m; pausado = !!m.pausado; $("pausar").textContent = pausado ? "Continuar" : "Pausar";
      if (m.editor && !$("editor-link")) {
        var a = document.createElement("a"); a.id = "editor-link"; a.href = "editor.html"; a.textContent = "Editor de sinais";
        a.style.cssText = "color:#9fb0c8;font-size:13px"; $("pausar").before(a);
      }
    } else if (m.tipo === "legenda" && m.quem === "pessoa") {
      mostrarOuvido(m.texto);
    } else if (m.tipo === "libras_aguarde") {
      $("aguarde").hidden = false; setTimeout(function () { $("aguarde").hidden = true; }, 40000);
    } else if (m.tipo === "mostrar_libras") {
      $("aguarde").hidden = true; entrar(m);
    } else if (m.tipo === "fechar_libras") {
      parar(); fila = [];
    }
  }

  // ---------- texto na tela ----------
  function mostrarOuvido(texto) {
    if (tocando) { $("ouvido-novo").hidden = false; $("ouvido-novo").textContent = "Ouvido agora: " + texto; return; }
    $("frase").textContent = texto; $("frase").className = "";
    $("glosa").textContent = "traduzindo…"; $("glosa").className = "vazio";
  }
  function mostrarFrase(m) {
    clearTimeout(temporizadorDeLimpeza);
    $("ouvido-novo").hidden = true;
    $("frase").textContent = m.frase; $("frase").className = "";
    var g = $("glosa"); g.textContent = ""; g.className = "";
    (m.glosa || "").split(/\s+/).filter(Boolean).forEach(function (p) {
      var s = document.createElement("span"); s.className = "p"; s.textContent = p; g.appendChild(s);
    });
    if (!g.children.length) { g.textContent = "—"; g.className = "vazio"; }
  }
  function marcar(de, ate) {   // palavras de.. ate-1 da glosa: a atual em destaque, as anteriores esmaecidas
    var ps = $("glosa").children;
    for (var i = 0; i < ps.length; i++) ps[i].className = "p" + (i >= de && i < ate ? " atual" : i < de ? " feito" : "");
    if (ps[de] && ps[de].scrollIntoView) { try { ps[de].scrollIntoView({ block: "nearest" }); } catch (e) {} }
  }
  function adicionarAoHistorico(m) {
    var li = document.createElement("li"); li.textContent = m.frase + "  →  " + m.glosa;
    li.onclick = function () { entrar(m, true); };
    var h = $("historico"); h.insertBefore(li, h.firstChild);
    while (h.children.length > 8) h.removeChild(h.lastChild);
  }

  // ---------- fila de frases ----------
  function entrar(m, repetida) {
    if (!repetida) adicionarAoHistorico(m);
    fila.push(m);
    if (fila.length > 3) fila.splice(0, fila.length - 3);
    if (!tocando) proximo();
  }
  function parar() {
    geracao++;
    if (avatar) avatar.cancelar();
    var v = $("video"); v.pause(); v.hidden = true; v.removeAttribute("src");
    $("midia").hidden = true; $("letras").textContent = ""; tocando = false;
    if ($("avatar")) $("avatar").hidden = !avatar;
  }
  function proximo() {
    var m = fila.shift();
    if (!m) { tocando = false; return; }
    tocando = true; ultima = m;
    var g = ++geracao;
    carregarAnimacoes().then(function () { return tocarFrase(m, g); })
      .catch(function (e) { console.error(e); })
      .then(function () {
        if (g !== geracao) return;
        if (fila.length) return proximo();
        tocando = false;
        if (avatar) avatar.descansar();
        $("letras").textContent = "";
        marcar(999, 999);
        temporizadorDeLimpeza = setTimeout(function () {
          if (!tocando) { $("frase").textContent = "Fale perto do tablet…"; $("frase").className = "vazio";
            $("glosa").textContent = "—"; $("glosa").className = "vazio"; }
        }, (m.segundos_depois || 30) * 1000);
      });
  }

  // ---------- tocar uma frase ----------
  function tocarFrase(m, g) {
    mostrarFrase(m);
    var vivo = function () { return g === geracao; };
    var total = (m.glosa || "").split(/\s+/).filter(Boolean).length;
    var passo = m.video && config.avatar !== "3d" ? tocarVideo(m, total, vivo) : Promise.resolve(false);
    return passo.then(function (feito) { return feito ? null : tocarItens(m, vivo); });
  }

  function tocarVideo(m, total, vivo) {
    return new Promise(function (resolve) {
      var v = $("video"), relogio = null, acabou = false;
      function fim(ok) {
        if (acabou) return; acabou = true; clearInterval(relogio);
        v.hidden = true; v.pause(); v.removeAttribute("src");
        if (avatar) $("avatar").hidden = false;
        resolve(ok);
      }
      v.onerror = function () { fim(false); };
      v.onended = function () { fim(true); };
      v.onloadedmetadata = function () {
        v.playbackRate = velocidade;
        relogio = setInterval(function () {
          if (!vivo()) return fim(true);
          if (v.duration > 0) { var i = Math.min(total - 1, Math.floor(v.currentTime / v.duration * total)); marcar(i, i + 1); }
        }, 120);
      };
      v.src = m.video; v.hidden = false; $("avatar").hidden = true;
      var p = v.play(); if (p && p.catch) p.catch(function () { fim(false); });
      setTimeout(function () { fim(true); }, 90000);   // segurança: nunca trava a fila
    });
  }

  function tocarItens(m, vivo) {
    var indice = 0, cadeia = Promise.resolve();
    var vel = velocidade;
    m.itens.forEach(function (item) {
      var n = Math.max(1, String(item.palavra).split(/\s+/).length), de = indice; indice += n;
      cadeia = cadeia.then(function () {
        if (!vivo()) return;
        marcar(de, de + n);
        if (item.modo === "animacao" && avatar && ANIM.sinais[item.chave]) {
          return avatar.tocarQuadros(ANIM.sinais[item.chave].quadros, vel);
        }
        if (item.modo === "sinal") return mostrarMidia(item.url, m.segundos_por_sinal / vel, vivo);
        return soletrar(item, m.segundos_por_letra / vel, vel, vivo);
      });
    });
    return cadeia;
  }

  function soletrar(item, segundos, vel, vivo) {
    var linha = $("letras"); linha.textContent = "";
    var letras = item.letras || [{ letra: String(item.palavra).toUpperCase(), url: null }];
    var spans = letras.map(function (l) { var s = document.createElement("span"); s.textContent = l.letra; linha.appendChild(s); return s; });
    var cadeia = Promise.resolve();
    letras.forEach(function (l, i) {
      cadeia = cadeia.then(function () {
        if (!vivo()) return;
        spans.forEach(function (s, j) { s.className = j === i ? "atual" : ""; });
        var def = ANIM.alfabeto[l.letra];
        if (avatar && def) return avatar.tocarQuadros(def.quadros, vel);
        if (l.url) return mostrarMidia(l.url, segundos, vivo);
        return esperar(segundos);   // sem avatar e sem imagem: a letra grande na linha já basta
      });
    });
    return cadeia.then(function () { linha.textContent = ""; $("midia").hidden = true; });
  }

  function mostrarMidia(url, segundos, vivo) {
    var caixa = $("midia"); caixa.textContent = ""; caixa.hidden = false;
    var video = /\.(mp4|webm)$/i.test(url), el = document.createElement(video ? "video" : "img");
    el.src = url;
    if (video) { el.muted = true; el.autoplay = true; el.loop = true; el.setAttribute("playsinline", ""); }
    caixa.appendChild(el);
    return esperar(segundos).then(function () { if (vivo()) caixa.hidden = true; });
  }

  // ---------- fala do robô completo (só quando LIBRAS_MODO_DEDICADO = False) ----------
  function tocarFalaDoRobo(dados) {
    var url = URL.createObjectURL(new Blob([dados], { type: "audio/wav" })), a = new Audio(url);
    a.onended = function () { URL.revokeObjectURL(url); enviar({ tipo: "terminei_de_falar" }); };
    a.onerror = a.onended; a.play().catch(a.onended);
  }

  // ---------- microfone: PCM 16 bits, 16 kHz, mono ----------
  function ligarMicrofone() {
    if (!navigator.mediaDevices || !navigator.mediaDevices.getUserMedia) {
      return Promise.reject(new Error("Este navegador não libera o microfone. Abra em http://localhost:8000 (cabo USB) ou use HTTPS."));
    }
    return navigator.mediaDevices.getUserMedia({ audio: { channelCount: 1, echoCancellation: true, noiseSuppression: true } })
      .then(function (fluxo) {
        var Ctx = window.AudioContext || window.webkitAudioContext, ctx = new Ctx();
        var fonte = ctx.createMediaStreamSource(fluxo), proc = ctx.createScriptProcessor(4096, 1, 1);
        var razao = ctx.sampleRate / 16000, fase = 0;
        proc.onaudioprocess = function (e) {
          var x = e.inputBuffer.getChannelData(0), n = Math.floor((x.length - fase) / razao);
          if (n <= 0) { fase -= x.length; return; }
          var saida = new Int16Array(n), soma2 = 0;
          for (var k = 0; k < n; k++) {
            var ini = Math.floor(fase + k * razao), fim = Math.min(x.length, Math.max(ini + 1, Math.floor(fase + (k + 1) * razao))), s = 0;
            for (var j = ini; j < fim; j++) s += x[j];
            var v = Math.max(-1, Math.min(1, s / (fim - ini)));
            saida[k] = v * 32767; soma2 += saida[k] * saida[k];
          }
          fase = Math.max(0, fase + n * razao - x.length);
          $("nivel-barra").style.width = Math.min(100, Math.sqrt(soma2 / n) / 20) + "%";
          if (!pausado && ws && ws.readyState === 1) ws.send(saida.buffer);
        };
        fonte.connect(proc); proc.connect(ctx.destination);
        microfoneLigado = true;
        if (ctx.state === "suspended") ctx.resume();
      });
  }

  // ---------- botões ----------
  $("comecar").onclick = function () {
    $("aviso-inicio").textContent = "";
    ligarMicrofone().then(function () { enviar({ tipo: "tocar" }); $("inicio").className = "escondido"; })
      .catch(function (e) {
        var nome = e && e.name ? e.name + ": " : "";
        $("aviso-inicio").textContent = nome + (e.message || "não consegui abrir o microfone") +
          " — você ainda pode digitar frases e usar a tela sem microfone.";
        $("comecar").textContent = "Usar sem microfone";
        $("comecar").onclick = function () { $("inicio").className = "escondido"; };
      });
  };
  $("pausar").onclick = function () {
    pausado = !pausado; enviar({ tipo: "pausar", ligado: pausado });
    $("pausar").textContent = pausado ? "Continuar" : "Pausar";
    if (pausado) $("nivel-barra").style.width = "0";
  };
  $("repetir").onclick = function () { if (ultima) { parar(); fila = []; entrar(ultima, true); } };
  $("velocidade").oninput = function () {
    velocidade = parseFloat(this.value);
    try { localStorage.setItem("libras_velocidade", String(velocidade)); } catch (e) {}
    var v = $("video"); if (!v.hidden) v.playbackRate = velocidade;
  };
  $("tela-cheia").onclick = function () {
    var d = document.documentElement, f = d.requestFullscreen || d.webkitRequestFullscreen;
    if (f) f.call(d);
  };
  $("digitar").onsubmit = function (e) {
    e.preventDefault(); var t = $("campo").value.trim();
    if (t) { enviar({ tipo: "texto", texto: t }); $("campo").value = ""; }
  };

  carregarAnimacoes();
  iniciarAvatar().then(function () { if (avatar) avatar.descansar(); });
  conectar();
})();
