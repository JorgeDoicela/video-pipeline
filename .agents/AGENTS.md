# Directrices de Ingeniería y Comportamiento del Agente — video-pipeline

Este archivo define las reglas obligatorias de comportamiento, estándares de calidad y principios de ingeniería para cualquier agente que opere en este repositorio.

---

## 1. Misión y Filosofía del Repositorio

* **Propósito:** Pipeline 100% local, soberano y de coste marginal cero para la producción programática de video técnico y educativo mediante IA.
* **Stack Tecnológico:**
  * **Transcripción:** `faster-whisper` (CTranslate2, modelo int8, marcas de tiempo palabra por palabra).
  * **Procesamiento de Audio/Video:** FFmpeg con aceleración nativa VA-API (Mesa/Radeon ACO).
  * **Renderizado y Motion Graphics:** HyperFrames (Chrome Headless Shell con `BeginFrame` determinista), GSAP 3.15.0 (+ `MotionPathPlugin`) y Three.js (WebGL determinista + `GLTFLoader` para modelos `.glb` de Blender).
* **Política de Cero Costes en la Nube:** Queda prohibida la dependencia de APIs externas de pago (ElevenLabs, fal.ai, HeyGen SaaS, OpenAI Audio). Todo cómputo debe ejecutarse localmente.

---

## 2. Estándares de Ingeniería y Calidad Profesional

* **Perfil Senior:** Opera siempre como un ingeniero de software senior (+10 años en producción). Cero parches, hacks o apaños temporales.
* **Tono Sobrio y Libre de Emojis:**
  * Queda estrictamente prohibido el uso de emojis en documentación, código fuente, commits y mensajes.
  * Prohibido el uso de lenguaje publicitario o inflado. Toda explicación debe ser fáctica, medible y técnicamente rigurosa.
* **Separación de Capas del Sistema (Arquitectura de 3 Capas):**
  * **Capa 1 (Debian Host):** FFmpeg nativo (`/usr/bin/ffmpeg`) para soporte directo de drivers gráficos AMD (`radeonsi_dri.so`).
  * **Capa 2 (Nix Flakes / Home Manager):** Gestores de paquetes (`uv`, `nodejs_22`, `pnpm`, `git`, `gh`).
  * **Capa 3 (Espacio de Trabajo):** Entorno virtual local Python (`.venv`) y módulos de Node.js (`node_modules`).

---

## 3. Contrato de Renderizado HyperFrames

Toda composición HTML dentro de `templates/` o `projects/` debe cumplir estrictamente las reglas del motor HyperFrames:

1. **Elemento Raíz de la Composición:**
   * El elemento contenedor raíz debe incluir los atributos:
     * `data-composition-id="main"`
     * `data-start="0"`
     * `data-duration="<segundos>"`
     * `data-width="<ancho>"` y `data-height="<alto>"`
   * No debe haber elementos hermanos gráficos fuera del contenedor raíz dentro de `<body>`.
2. **Animaciones Deterministas con GSAP:**
   * La línea de tiempo de GSAP debe inicializarse siempre pausada: `const tl = gsap.timeline({ paused: true });`.
   * Debe registrarse obligatoriamente en el objeto global: `window.__timelines["main"] = tl;`.
   * Debe posicionarse en el inicio: `tl.seek(0);`.
   * **Prohibición de Transiciones CSS:** Nunca utilices `transition:` en CSS para animar propiedades visuales. Las transiciones CSS dependen del reloj del navegador y rompen el renderizado determinista fotograma a fotograma en paralelo. Toda animación debe residir en la línea de tiempo de GSAP.
3. **Medios y Video:**
   * Todo elemento `<video>` o `<audio>` debe contar con `data-start="<tiempo>"` y `data-duration="<duración>"`.
   * Los archivos referenciados en `src` deben existir físicamente en disco.
4. **Accesibilidad Visual (WCAG AA):**
   * El contraste de texto sobre fondo debe cumplir un ratio mínimo de 4.5:1 para texto normal y 3:1 para texto grande.
   * La escala de fuentes para texto legible debe ser de al menos 28px en paneles 1080p, o marcarse con `data-layout-ignore` si se trata de textura gráfica puramente decorativa.
5. **Preferencias Estéticas Obligatorias de Jorge (Restricciones Absolutas):**
   * **Cero pastillas en palabras de subtítulos:** Queda terminantemente prohibido encerrar palabras de subtítulos en pastillas o cajas contenedoras (`background`, `border`, `border-radius`, `padding` en `.word.active`). Los subtítulos deben usar tipografía limpia (`minimal_clean`), iluminando la palabra activa exclusivamente con color (`var(--caption-active)`), opacidad y sombra tipográfica sutil.
   * **Cero cápsulas/pastillas en badges e iconos SVG:** Queda prohibido rodear badges, etiquetas o iconos SVG con cajas o fondos redondeados (`background`, `border`, `padding` en `.badge`, `.hook-badge` o SVGs). Los badges deben ser texto tipográfico limpio (tracking amplio, mayúsculas, peso 700-800, color de acento, fondo y borde transparentes/inexistentes) y los iconos vectoriales deben renderizarse limpios y desnudos sin cápsula.
   * **Cero franjas o bordes de acento asimétricos a la izquierda:** Queda estrictamente prohibido usar `border-left: 6px solid var(--accent-primary)` o barras de acento laterales en tarjetas (`#main-card`, `.panel`, `.lower-third`). Las tarjetas deben tener bordes simétricos y uniformes en los cuatro lados (`border: var(--border-width) solid var(--border)`).
   * **Cero líneas o filetes en títulos o subtítulos:** Queda estrictamente prohibido colocar líneas horizontales decorativas, filetes, subrayados o bordes (`border-top`, `border-bottom`, `text-decoration: underline`, `<hr>`) en títulos, encabezados (`header`, `h1`-`h6`) o subtítulos. Los textos deben ser tipografía pura y limpia respirando directamente sobre el fondo.

---

## 4. Estructura del Proyecto y Convenciones de Directorios

```text
video-pipeline/
├── .agents/           # Directrices, memoria y skills locales del repositorio
│   ├── AGENTS.md         # Reglas obligatorias de ingeniería y comportamiento
│   ├── memory.md         # Memoria técnica y decisiones arquitectónicas
│   └── skills/           # Skills especializadas locales
│       └── diseno-video/ # Estándares visuales limpios, tipografía y HyperFrames
├── core/              # Scripts CLI de procesamiento y orquestación
│   ├── pipeline.py       # Orquestador maestro end-to-end (--voice-polish, --no-cut-silence, --no-sfx, --words-per-group, assets, image)
│   ├── scenes.py         # Motor multi-escena (30 componentes SVG/HTML/Canvas/3D/Video/Manim: infinite_canvas, svg_draw, scene_3d, video_clip, manim_clip, image_cutout, custom_scene, cue_word, hero_top, tree-shaking CSS)
│   ├── audio_mix.py      # Mezclador determinista de voz (--voice-polish), música/cama con ducking y 15 SFX (FFmpeg)
│   ├── styles.py         # Fachada del motor de diseño en 3 niveles y estilos de subtítulos
│   ├── _styles_catalog.py# Catálogo declarativo de diseños, temas, layouts y tokens
│   ├── _styles_renderer.py# Compilador CSS, inyección idempotente y persistencia
│   ├── sync_captions.py  # Generador de subtítulos cinéticos (cortes por puntuación, emphasis_words, HTML, GSAP, SRT, VTT)
│   ├── cut_silence.py    # Recorte algorítmico de pausas (FFmpeg)
│   ├── transcribe.py     # Transcripción con word timestamps y reemplazos multi-palabra (faster-whisper)
│   ├── create_project.py # Scaffolding automatizado de proyectos
│   ├── generate_sfx.py   # Síntesis matemática de 15 efectos de sonido WAV y 3 pistas musicales loopables
│   ├── fetch_assets.py   # Gestor de assets abiertos (Iconify SVG + 18 iconos semilla, mapas Natural Earth GeoJSON CC0, audio CC0 y conector Blender headless + 6 modelos 3D semilla .glb)
│   ├── image_tools.py    # Procesador de imágenes: rembg (IA local ONNX IS-Net 1024x1024 y color), crop, auto-trim, cutout sticker y conversión
│   ├── manim_tools.py    # Integración Manim Community (doctor, new, render 16:9/9:16/alpha, paleta sincronizada y componente manim_clip)
│   └── workspace.py      # Perfiles de canal/cliente (profiles/*.json), workspaces externos (VIDEO_PIPELINE_WORKSPACE) e historial append-only (catalog.jsonl)
├── profiles/          # Perfiles declarativos reutilizables por canal o cliente (tech_short, editorial_essay, client_clean)
├── templates/         # Catálogo de 7 plantillas esenciales (9:16 y 16:9)
│   ├── explainer_scenes_9_16/ # Explainer faceless multi-escena vertical 9:16 (1080x1920)
│   ├── explainer_scenes_16_9/ # Explainer faceless multi-escena horizontal 16:9 (1920x1080)
│   ├── short_quote_9_16/ # Citas, versículos y reflexiones en formato vertical 9:16
│   ├── short_tech_9_16/  # Shorts/Reels/TikTok código y subtítulos (1080x1920)
│   ├── talking_head_9_16/# Presentador vertical 9:16 para Shorts/Reels/TikTok
│   ├── editorial_16_9/   # Narrativa histórica, bíblica y ensayos en 16:9
│   └── talking_head_16_9/# Presentador widescreen 16:9 con lower-third y subtítulos
├── projects/          # Proyectos de video concretos generados a partir de templates
├── assets/            # Recursos estáticos globales (audio/ SFX, music/ camas, maps/ SVG, images/ cutouts, models/ glTF-GLB, manim/ escenas .py, icons/ SVG, fonts/)
├── tests/             # Suite automatizada de pruebas unitarias (pytest)
├── docs/              # Documentación modular Docs-as-Code (00- y subcarpetas 01- a 05-)
├── .github/workflows/ # Pipeline de integración continua (CI) en GitHub Actions
├── package.json       # Dependencias de HyperFrames y scripts de ejecución
└── pyproject.toml     # Dependencias Python, extras dev, Ruff y pytest
```

---

## 5. Protocolo Operativo y Verificación Obligatoria

Antes de dar por concluida cualquier modificación o creación de proyecto:

1. **Flujo de Producción Rápido Unificado (Presentador o Faceless Multi-Escena):**
   ```bash
   # Presentador a cámara / pantalla
   uv run python core/pipeline.py produce -i ruta/grabacion.mp4 -p nombre-proyecto -t talking_head_16_9 --auto-render

   # Explainer faceless multi-escena desde solo voz con storyboard, ducking y vocabulario técnico
   uv run python core/pipeline.py produce -i mi_voz.wav -p mi-explainer -t explainer_scenes_9_16 -d cinematic -s dark_violet --storyboard guion.json --replace lidis=Redis --ambient-bed --auto-render
   ```
2. **Validación de Estándares HyperFrames:**
   ```bash
   pnpm exec hyperframes check projects/<nombre_proyecto>
   ```
   No se permiten errores de contraste, layout o media faltante.
3. **Auditoría de Código y Suite de Pruebas:**
   ```bash
   ruff check core tests
   ruff format --check core tests
   pytest tests
   ```
4. **Renderizado de Producción:**
   ```bash
   pnpm exec hyperframes render projects/<nombre_proyecto> -o projects/<nombre_proyecto>/video_<nombre_proyecto>.mp4
   ```
