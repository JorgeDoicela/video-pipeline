# 04 — Formatos de Video Soportados

Este documento define la especificacion de diseño, contratos tecnicos y ejemplos de codigo para los dos formatos de video que produce el pipeline.

---

## 1. Formato 1: Grabacion a Camara y Pantalla (Talking Head)

* **Proposito:** Videos donde el autor expone un tema en camara o comparte su escritorio, enriquecido con elementos graficos dinamicos sincronizados con el habla.
* **Componentes Visuales:**
  1. **Subtitulos Cineticos:** Palabras individuales que aparecen o cambian de color en el milisegundo exacto de su pronunciacion (estilo tipografia cinetica).
  2. **Tarjetas Flotantes (*Lower-Thirds*):** Paneles informativos con definiciones, comandos de consola o advertencias tecnicas.
  3. **Llamadas de Atencion:** Recuadros, flechas o efectos de zoom focalizados sobre elementos de la grabacion de pantalla.

### 1.1. Arquitectura de Composicion de Capas

Existen dos estrategias tecnicas para ensamblar este formato:

```mermaid
flowchart LR
    subgraph OpcionA ["Estrategia 1: Video como Fondo en HTML"]
        V1["cut.mp4"] --> HF["HyperFrames (Etiqueta &lt;video&gt;)"]
        O1["Overlays HTML/GSAP"] --> HF
        HF --> R1["MP4 Final Directo"]
    end

    subgraph OpcionB ["Estrategia 2: Render Transparente + Multiplexado"]
        O2["Overlays HTML/GSAP"] --> HF2["HyperFrames (--format webm)"]
        HF2 --> W["overlays.webm (Canal Alfa)"]
        V2["cut.mp4"] --> MUX["FFmpeg Overlay Filter"]
        W --> MUX
        MUX --> R2["MP4 Final Multiplexado"]
    end
```

* **Estrategia Recomendada:** La *Estrategia 1* (incrustar el video crudo recortado directamente en la composicion de HyperFrames mediante `<video src="cut.mp4">`) permite al motor de Chrome sincronizar el fotograma exacto del video con las animaciones de texto sin requerir pasadas adicionales de multiplexado en FFmpeg.

### 1.2. Patron de Composicion HTML para Formato 1

```html
<!doctype html>
<html lang="es">
  <head>
    <meta charset="UTF-8" />
    <meta name="viewport" content="width=1920, height=1080" />
    <script src="https://cdn.jsdelivr.net/npm/gsap@3.15.0/dist/gsap.min.js"></script>
    <style>
      body { margin: 0; width: 1920px; height: 1080px; overflow: hidden; background: #000; font-family: sans-serif; }
      #root { position: relative; width: 100%; height: 100%; }
      #bg-video { position: absolute; top: 0; left: 0; width: 100%; height: 100%; object-fit: cover; }
      .lower-third {
        position: absolute; bottom: 80px; left: 80px;
        background: rgba(15, 23, 42, 0.88); backdrop-filter: blur(12px);
        border-left: 6px solid #38bdf8; padding: 20px 32px; border-radius: 8px; color: #fff;
        opacity: 0; transform: translateY(30px);
      }
      .kinetic-caption {
        position: absolute; bottom: 220px; width: 100%; text-align: center;
        font-size: 54px; font-weight: 800; color: #f8fafc; text-shadow: 0 4px 16px rgba(0,0,0,0.8);
      }
      .word { opacity: 0.3; transition: opacity 0.1s, color 0.1s; }
      .word.active { opacity: 1; color: #38bdf8; }
    </style>
  </head>
  <body>
    <div id="root" data-composition-id="main" data-start="0" data-duration="15" data-width="1920" data-height="1080">
      <video id="bg-video" src="cut.mp4" muted></video>
      <div id="card" class="lower-third">
        <h3 style="margin:0 0 6px 0; font-size: 28px;">Base de Datos Distribuida</h3>
        <p style="margin:0; font-size: 18px; color: #94a3b8;">Consistencia eventual y particionamiento</p>
      </div>
      <div class="kinetic-caption">
        <span id="w1" class="word">Bienvenidos</span>
        <span id="w2" class="word">al</span>
        <span id="w3" class="word">sistema</span>
      </div>
    </div>
    <script>
      const tl = gsap.timeline({ paused: true });
      // Sincronizacion de lower-third (segundo 2.5 al 6.0)
      tl.to("#card", { opacity: 1, y: 0, duration: 0.4, ease: "power2.out" }, 2.5);
      tl.to("#card", { opacity: 0, y: 20, duration: 0.3, ease: "power2.in" }, 6.0);
      // Sincronizacion palabra por palabra con timestamps de Whisper
      tl.to("#w1", { className: "word active", duration: 0.05 }, 1.1);
      tl.to("#w2", { className: "word active", duration: 0.05 }, 1.4);
      tl.to("#w3", { className: "word active", duration: 0.05 }, 1.7);
      window.__timelines = { main: tl };
      tl.seek(0);
    </script>
  </body>
</html>
```

---

## 2. Formato 2: Explicador Tecnico Abstracto (Sin Rostro)

* **Proposito:** Videos de alta densidad tecnica donde la voz en off guia la visualizacion de conceptos de software, flujos de paquetes en redes, arquitectura de microservicios o estructuras de datos.
* **Motor Grafico Principal:** HyperFrames con SVG y Prism.js.

### 2.1. Modelado de Diagramas de Arquitectura con SVG
El agente genera codigo SVG donde los elementos de infraestructura se representan como nodos y aristas:
* **Nodos:** Rectangulos con bordes redondeados y texto tipografico que representan servidores, microservicios, bases de datos o clientes.
* **Conexiones:** Lineas vectoriales con `stroke-dasharray` y `stroke-dashoffset` animados con GSAP para simular flujo continuo de datos o paquetes de red.
* **Resaltado de Codigo:** Bloques `<pre><code>` estilizados con temas de alto contraste, donde GSAP activa el resaltado de lineas especificas al momento en que la voz las explica.

### 2.2. Patron de Animacion SVG para Formato 2

```html
<svg width="1920" height="1080" viewBox="0 0 1920 1080" style="background:#090d16;">
  <!-- Nodo Cliente -->
  <g id="client-node" transform="translate(300, 480)">
    <rect width="240" height="120" rx="12" fill="#1e293b" stroke="#38bdf8" stroke-width="3"/>
    <text x="120" y="68" fill="#f8fafc" font-size="22" font-weight="600" text-anchor="middle">Cliente Web</text>
  </g>

  <!-- Canal de Red -->
  <line id="network-cable" x1="540" y1="540" x2="1380" y2="540" stroke="#334155" stroke-width="6"/>

  <!-- Paquete de Datos Viajando -->
  <circle id="tcp-packet" cx="540" cy="540" r="14" fill="#38bdf8" opacity="0"/>

  <!-- Nodo Servidor API -->
  <g id="server-node" transform="translate(1380, 480)">
    <rect width="240" height="120" rx="12" fill="#1e293b" stroke="#10b981" stroke-width="3"/>
    <text x="120" y="68" fill="#f8fafc" font-size="22" font-weight="600" text-anchor="middle">Servidor API</text>
  </g>
</svg>
<script>
  // En GSAP se anima el envio del paquete de red
  tl.set("#tcp-packet", { opacity: 1 }, 2.0);
  tl.fromTo("#tcp-packet", { cx: 540 }, { cx: 1380, duration: 1.2, ease: "power1.inOut" }, 2.0);
  tl.set("#tcp-packet", { opacity: 0 }, 3.2);
</script>
```

---

## 3. Matriz de Seleccion de Motor

| Caracteristica | Formato 1 (Talking Head) | Formato 2 (Arquitectura/Redes) | Formato 2 (Matematicas/Calculo) |
| :--- | :--- | :--- | :--- |
| **Pista Visual Base** | Grabacion de camara o pantalla | Vacia (generada por codigo) | Vacia (generada por codigo) |
| **Motor Recomendado** | HyperFrames (HTML + GSAP) | HyperFrames (HTML + SVG + GSAP) | Manim (Python / Cairo) |
| **Tiempo de Render** | 0.6x - 1.0x tiempo real | 0.3x - 0.7x tiempo real | 1.5x - 3.0x tiempo real |
| **Manejo de Subtitulos** | Nativo mediante timestamps | Opcional | Raramente utilizado |

---

## 4. Enlaces Relacionados

* Consultar los runbooks paso a paso en [05-guia-operativa-y-flujos.md](./05-guia-operativa-y-flujos.md).
* Volver al indice general en [00-indice-general.md](./00-indice-general.md).
