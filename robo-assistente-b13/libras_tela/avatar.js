/*
 AVATAR 3D (Three.js r128, WebGL 1: roda em Chrome antigo de tablet Android 7)
 =============================================================================
 Tronco, cabeça com rosto e dois braços com mão articulada (5 dedos).
 Os braços usam cinemática inversa: o sinal diz ONDE fica a mão, o braço se ajeita sozinho.

 FORMATO DE UM SINAL (libras/animacoes/sinais*.json):
   "bom dia": { "quadros": [
       { "t": 0.0, "d": { "p": [0.12, 0.30, 0.30], "o": [0,0,0], "f": [0,0,0,0,0], "a": 0 },
                   "e": null,
                   "r": { "sb": 0.3, "boca": 0, "cab": [0,0,0] } },
       { "t": 0.6, ... } ] }
   d = mão direita, e = mão esquerda (ausente/null = mão em repouso, caída ao lado do corpo).
   p = posição do pulso em metros, do ponto de vista de QUEM SINALIZA, a partir do meio do peito:
       [x para a direita de quem sinaliza, y para cima, z para a frente].
   o = orientação da mão em graus [inclinação, giro, rolagem]. [0,0,0] = dedos para cima, palma para o espectador.
       inclinação>0: dedos para a frente; rolagem: gira em torno da palma (90 = dedos para o lado de dentro).
       Vale igual para as duas mãos (a esquerda é espelhada sozinha).
   f = dobra de cada dedo, de 0 (esticado) a 1 (dobrado): [polegar, indicador, médio, anelar, mínimo].
   a = abertura entre os dedos, de -1 (cruzados) a 1 (bem abertos).
   r = rosto: sb sobrancelhas (-1 baixas, 1 erguidas), boca (0 a 1 aberta), cab = cabeça [inclinação, giro, rolagem].
   t = segundos (na velocidade 1). Entre dois quadros a pose é suavizada.
*/
(function () {
  "use strict";

  var T = window.THREE;
  var RAD = Math.PI / 180;

  // ---------- poses ----------
  var NEUTRO = { p: [0.12, 0.14, 0.32], o: [0, 0, 0], f: [0, 0, 0, 0, 0], a: 0 };
  var REPOUSO_D = { p: [0.24, -0.36, 0.05], o: [0, 90, 180], f: [0.35, 0.35, 0.35, 0.35, 0.35], a: 0 };
  var REPOUSO_E = { p: [-0.24, -0.36, 0.05], o: [0, 90, 180], f: [0.35, 0.35, 0.35, 0.35, 0.35], a: 0 };
  var ROSTO0 = { sb: 0, boca: 0, cab: [0, 0, 0] };

  function copia(x) { return JSON.parse(JSON.stringify(x)); }

  function mao(m, lado) {
    if (!m) return copia(lado === "d" ? REPOUSO_D : REPOUSO_E);
    var n = copia(NEUTRO);
    if (lado === "e") n.p[0] = -n.p[0];
    ["p", "o", "f"].forEach(function (k) { if (m[k]) n[k] = m[k].slice(); });
    if (typeof m.a === "number") n.a = m.a;
    return n;
  }
  function rosto(r) {
    var n = copia(ROSTO0);
    if (r) {
      if (typeof r.sb === "number") n.sb = r.sb;
      if (typeof r.boca === "number") n.boca = r.boca;
      if (r.cab) n.cab = r.cab.slice();
    }
    return n;
  }
  function pose(q) { return { d: mao(q && q.d, "d"), e: mao(q && q.e, "e"), r: rosto(q && q.r) }; }

  function mistura(a, b, u) {
    if (typeof a === "number") return a + (b - a) * u;
    if (Array.isArray(a)) return a.map(function (v, i) { return mistura(v, b[i], u); });
    var o = {};
    for (var k in a) o[k] = mistura(a[k], b[k], u);
    return o;
  }
  function suave(u) { return u * u * (3 - 2 * u); }

  // ---------- peças ----------
  var CINZA_PELE = 0xd9a37e, CAMISA = 0x2f6fd0, CABELO = 0x2b1b12;
  var CURVA_MAX = [1.45, 1.7, 1.3];   // dobra máxima de cada junta dos dedos (radianos)

  function material(cor) { return new T.MeshLambertMaterial({ color: cor }); }
  function esfera(r, mat, sx, sy, sz) {
    var m = new T.Mesh(new T.SphereGeometry(r, 14, 10), mat);
    m.scale.set(sx || 1, sy || 1, sz || 1);
    return m;
  }
  function limitar(v, a, b) { return Math.max(a, Math.min(b, v)); }

  // cilindro de altura 1 que será esticado entre dois pontos
  function segmento(raio, mat) {
    return new T.Mesh(new T.CylinderGeometry(raio, raio, 1, 10), mat);
  }
  var CIMA = new T.Vector3(0, 1, 0);
  function ligar(m, a, b) {
    var d = new T.Vector3().subVectors(b, a);
    var len = Math.max(d.length(), 1e-4);
    m.position.copy(a).addScaledVector(d, 0.5);
    m.scale.set(1, len, 1);
    m.quaternion.setFromUnitVectors(CIMA, d.normalize());
  }

  function criarDedo(x, comprimentos, raio, mat) {
    var base = new T.Group();
    base.position.set(x, 0.09, 0);
    var grupos = [], pai = base;
    comprimentos.forEach(function (c, i) {
      var j = i === 0 ? base : new T.Group();
      if (i > 0) { j.position.y = comprimentos[i - 1]; pai.add(j); }
      var s = segmento(raio, mat); s.scale.y = c; s.position.y = c / 2; j.add(s);
      j.add(esfera(raio * 1.1, mat));
      grupos.push(j); pai = j;
    });
    return { base: base, grupos: grupos };
  }

  function criarMao(lado) {
    var s = lado === "d" ? 1 : -1;   // o polegar da mão direita fica do lado +x quando a palma olha para o espectador
    var mat = material(CINZA_PELE);
    var g = new T.Group();
    var palma = new T.Mesh(new T.BoxGeometry(0.085, 0.09, 0.026), mat);
    palma.position.y = 0.045; g.add(palma);
    var punho = esfera(0.028, mat); g.add(punho);
    var xs = [0.031, 0.0105, -0.0105, -0.031];
    var comp = [[0.04, 0.025, 0.02], [0.045, 0.028, 0.02], [0.04, 0.026, 0.02], [0.031, 0.02, 0.018]];
    var dedos = xs.map(function (x, i) {
      var d = criarDedo(s * x, comp[i], 0.0085, mat); g.add(d.base); return d;
    });
    var polegar = criarDedo(0, [0.032, 0.028], 0.0095, mat);
    polegar.base.position.set(s * 0.043, 0.025, 0.012);
    g.add(polegar.base);
    g.scale.setScalar(1.25);
    return { grupo: g, dedos: dedos, polegar: polegar, lado: s };
  }

  function aplicarMao(m, h, lado) {
    var s = m.lado;
    // orientação (a mão esquerda é o espelho da direita: giro e rolagem trocam de sinal)
    var e = lado === "e" ? -1 : 1;
    m.grupo.rotation.set(h.o[0] * RAD, h.o[1] * RAD * e, h.o[2] * RAD * e, "YXZ");
    // dedos
    for (var i = 0; i < 4; i++) {
      var v = limitar(h.f[i + 1], 0, 1), d = m.dedos[i];
      d.grupos[0].rotation.x = CURVA_MAX[0] * limitar((v - 0.35) / 0.65, 0, 1);
      d.grupos[1].rotation.x = CURVA_MAX[1] * limitar(v / 0.8, 0, 1);
      d.grupos[2].rotation.x = CURVA_MAX[2] * limitar(v / 0.9, 0, 1);
      d.base.rotation.z = s * (-(1.5 - i) * h.a * 0.11);
    }
    var p = limitar(h.f[0], 0, 1), t = m.polegar;
    t.base.rotation.z = s * (-0.75 * (1 - p) + 0.9 * p);
    t.base.rotation.x = p * 0.7;
    t.grupos[1].rotation.x = p * 0.9;
  }

  // ---------- o avatar ----------
  function Avatar3D(canvas) {
    this.ok = false;
    this.canvas = canvas;
    this.atual = pose(null);
    this.trilha = null;
    this.relogio = 0;
    this.piscar = 2;
    try {
      this.renderer = new T.WebGLRenderer({ canvas: canvas, antialias: true, alpha: true });
    } catch (e) { return; }
    if (!this.renderer || !this.renderer.getContext()) return;
    this.renderer.setPixelRatio(Math.min(window.devicePixelRatio || 1, 1.5));
    this.cena = new T.Scene();
    this.camera = new T.PerspectiveCamera(32, 1, 0.1, 20);
    this.camera.position.set(0, 1.22, 2.35);
    this.camera.lookAt(0, 1.2, 0);
    this.cena.add(new T.HemisphereLight(0xffffff, 0x8899aa, 0.85));
    var sol = new T.DirectionalLight(0xffffff, 0.55); sol.position.set(0.8, 2.2, 2.5); this.cena.add(sol);
    this.construir();
    this.ok = true;
    this.redimensionar();
    window.addEventListener("resize", this.redimensionar.bind(this));
    this.laco = this.laco.bind(this);
    requestAnimationFrame(this.laco);
  }

  Avatar3D.prototype.construir = function () {
    var pele = material(CINZA_PELE), camisa = material(CAMISA);
    var corpo = this.corpo = new T.Group(); this.cena.add(corpo);
    var tronco = new T.Mesh(new T.CylinderGeometry(0.17, 0.21, 0.62, 16), camisa);
    tronco.scale.z = 0.58; tronco.position.y = 1.13; corpo.add(tronco);
    var ombros = new T.Mesh(new T.CylinderGeometry(0.06, 0.06, 0.44, 12), camisa);
    ombros.rotation.z = Math.PI / 2; ombros.position.y = 1.38; corpo.add(ombros);
    [-0.22, 0.22].forEach(function (x) { var o = esfera(0.065, camisa); o.position.set(x, 1.38, 0); corpo.add(o); });
    var pescoco = new T.Mesh(new T.CylinderGeometry(0.045, 0.05, 0.1, 12), pele);
    pescoco.position.y = 1.5; corpo.add(pescoco);

    // cabeça
    var cab = this.cabeca = new T.Group(); cab.position.set(0, 1.62, 0); corpo.add(cab);
    cab.add(esfera(0.12, pele, 1, 1.18, 1.02));
    var cabelo = new T.Mesh(new T.SphereGeometry(0.128, 16, 10, 0, Math.PI * 2, 0, Math.PI * 0.52), material(CABELO));
    cabelo.scale.set(1, 1.18, 1.05); cabelo.position.set(0, 0.012, -0.008); cab.add(cabelo);
    var nariz = esfera(0.016, pele, 1, 1.2, 1); nariz.position.set(0, -0.008, 0.123); cab.add(nariz);
    var branco = material(0xffffff), preto = material(0x1a1a1a), marrom = material(0x2b1b12);
    this.olhos = [];
    [-1, 1].forEach(function (s) {
      var o = new T.Group(); o.position.set(s * 0.045, 0.025, 0.1); cab.add(o);
      o.add(esfera(0.02, branco, 1, 1, 0.6));
      var pu = esfera(0.01, preto); pu.position.z = 0.009; o.add(pu);
      this.olhos.push(o);
    }, this);
    this.sobrancelhas = [-1, 1].map(function (s) {
      var b = new T.Mesh(new T.BoxGeometry(0.044, 0.009, 0.008), marrom);
      b.position.set(s * 0.045, 0.062, 0.112); cab.add(b); b.userData.s = s; return b;
    });
    this.boca = esfera(0.028, material(0x8a2f2f), 1, 0.25, 0.4);
    this.boca.position.set(0, -0.06, 0.112); cab.add(this.boca);

    // braços: segmentos entre ombro, cotovelo e pulso são esticados a cada quadro
    this.bracos = {};
    var self = this;
    ["d", "e"].forEach(function (lado) {
      var ombro = new T.Vector3(lado === "d" ? -0.22 : 0.22, 1.38, 0);
      var sup = segmento(0.034, camisa), inf = segmento(0.028, pele), cot = esfera(0.036, camisa);
      var m = criarMao(lado);
      corpo.add(sup); corpo.add(inf); corpo.add(cot); corpo.add(m.grupo);
      self.bracos[lado] = { ombro: ombro, sup: sup, inf: inf, cot: cot, mao: m, L1: 0.3, L2: 0.27 };
    });
  };

  var CENTRO = new T.Vector3(0, 1.25, 0.08);   // meio do peito de quem sinaliza
  var v1 = new T.Vector3(), v2 = new T.Vector3(), v3 = new T.Vector3();

  Avatar3D.prototype.aplicarBraco = function (lado, h) {
    var b = this.bracos[lado];
    // do ponto de vista de quem sinaliza, +x é a direita dele, que aparece à esquerda do espectador (-x do mundo)
    var alvo = new T.Vector3(CENTRO.x - h.p[0], CENTRO.y + h.p[1], CENTRO.z + h.p[2]);
    var dir = v1.subVectors(alvo, b.ombro);
    var d = limitar(dir.length(), 0.12, (b.L1 + b.L2) * 0.995);
    dir.normalize();
    alvo.copy(b.ombro).addScaledVector(dir, d);
    var lado_w = lado === "d" ? -1 : 1;
    var polo = v2.set(lado_w * 0.5, -1, -0.35);              // o cotovelo prefere ficar para baixo e para fora
    polo.addScaledVector(dir, -polo.dot(dir)).normalize();
    var a = (b.L1 * b.L1 - b.L2 * b.L2 + d * d) / (2 * d);
    var alt = Math.sqrt(Math.max(b.L1 * b.L1 - a * a, 0));
    var cot = v3.copy(b.ombro).addScaledVector(dir, a).addScaledVector(polo, alt).clone();
    ligar(b.sup, b.ombro, cot);
    ligar(b.inf, cot, alvo);
    b.cot.position.copy(cot);
    b.mao.grupo.position.copy(alvo);
    aplicarMao(b.mao, h, lado);
  };

  Avatar3D.prototype.aplicar = function (p, agora) {
    this.aplicarBraco("d", p.d);
    this.aplicarBraco("e", p.e);
    var r = p.r;
    this.cabeca.rotation.set((r.cab[0] + Math.sin(agora * 0.0007) * 1.2) * RAD, r.cab[1] * RAD, r.cab[2] * RAD);
    this.sobrancelhas.forEach(function (b) {
      b.position.y = 0.062 + r.sb * 0.012;
      b.rotation.z = b.userData.s * r.sb * 0.18;
    });
    this.boca.scale.y = 0.25 + r.boca * 0.9;
    // respirar e piscar
    this.corpo.position.y = Math.sin(agora * 0.0018) * 0.004;
    var piscando = agora > this.piscar && agora < this.piscar + 120;
    if (agora > this.piscar + 120) this.piscar = agora + 2500 + Math.random() * 3000;
    this.olhos.forEach(function (o) { o.scale.y = piscando ? 0.1 : 1; });
  };

  // ---------- animação ----------
  // quadros: [{t, d, e, r}] em segundos; devolve uma promessa que termina no último quadro
  Avatar3D.prototype.tocarQuadros = function (quadros, velocidade) {
    var self = this;
    this.cancelar();
    var vel = velocidade || 1, entrada = 0.3;
    var lista = [{ t: 0, p: copia(this.atual) }];
    var auto = 0;
    quadros.forEach(function (q, i) {
      var t = typeof q.t === "number" ? q.t : (auto = i * 0.5);
      lista.push({ t: (entrada + t) / vel, p: pose(q) });
    });
    if (lista.length === 2) lista.push({ t: lista[1].t + 0.5 / vel, p: lista[1].p });   // segura a pose um instante
    return new Promise(function (resolve) {
      self.trilha = { inicio: performance.now(), lista: lista, fim: resolve };
    });
  };

  Avatar3D.prototype.descansar = function () {
    return this.tocarQuadros([{ t: 0 }], 1.4);
  };

  Avatar3D.prototype.cancelar = function () {
    if (this.trilha) { var f = this.trilha.fim; this.trilha = null; f(); }
  };

  Avatar3D.prototype.passo = function (agora) {
    var tr = this.trilha;
    if (!tr) return;
    var t = (agora - tr.inicio) / 1000, L = tr.lista, i = 0;
    while (i < L.length - 2 && t > L[i + 1].t) i++;
    var a = L[i], b = L[i + 1];
    var u = b.t > a.t ? limitar((t - a.t) / (b.t - a.t), 0, 1) : 1;
    this.atual = mistura(a.p, b.p, suave(u));
    if (t >= L[L.length - 1].t) { this.atual = copia(L[L.length - 1].p); this.trilha = null; tr.fim(); }
  };

  Avatar3D.prototype.redimensionar = function () {
    var c = this.canvas, w = c.clientWidth || 640, h = c.clientHeight || 480;
    this.renderer.setSize(w, h, false);
    this.camera.aspect = w / h;
    // em tela estreita (retrato), afasta a câmera para caber os braços abertos
    var largura = 1.25, fov = this.camera.fov * RAD;
    var distancia = Math.max(2.35, (largura / this.camera.aspect / 2) / Math.tan(fov / 2));
    this.camera.position.z = distancia;
    this.camera.updateProjectionMatrix();
  };

  Avatar3D.prototype.laco = function (agora) {
    requestAnimationFrame(this.laco);
    if (agora - this.relogio < 30) return;   // ~30 quadros por segundo: poupa o tablet
    this.relogio = agora;
    this.passo(agora);
    this.aplicar(this.atual, agora);
    this.renderer.render(this.cena, this.camera);
  };

  Avatar3D.pose = pose;
  window.Avatar3D = Avatar3D;
})();
