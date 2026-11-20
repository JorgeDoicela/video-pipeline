# Memoria Técnica del Proyecto — video-pipeline

## 1. Decisiones Arquitectónicas
* **Pipeline 100% local:** Transcripción con `faster-whisper` (`int8`), recorte de silencios con `FFmpeg`, renderizado determinista con HyperFrames + GSAP `3.15.0` (prohibido `transition:` en CSS).
* **Catálogo consolidado (7 plantillas + sistema 4x4):** `short_quote_9_16`, `short_tech_9_16`, `talking_head_9_16`, `editorial_16_9`, `talking_head_16_9`, `explainer_scenes_9_16`, `explainer_scenes_16_9`, combinables con 4 Diseños Macro (`cinematic`, `editorial`, `clean`, `terminal`), 4 Paletas WCAG AA (`dark_violet`, `paper_warm`, `clean_light`, `terminal_green`) y subtítulos con `minimal_clean` como estándar por defecto.
* **Motor Multi-Escena Faceless (`core/scenes.py`, `core/audio_mix.py`, `core/generate_sfx.py`, `core/fetch_assets.py`, `core/image_tools.py`):** Compila `storyboard.json` en escenas GSAP con 25 componentes universales (`timeline_steps`, `comparison_split`, `quote_focus`, `bar_chart`, `code_spotlight`, `icon_spotlight` con auto-fetch de Iconify, `phone_mockup` con modos `list`/`app_grid`, `capture_flash` y `show_cursor`, `network_graph`, `terminal_grid`, `connector_flow`, `stat_callout`, `radar_map` con `map_preset` desde `assets/maps/*.svg` y `route`, `xray_scanner`, `system_alert`, `hex_inspector`, `desktop_monitor`, `keyboard_type`, `padlock_denied`, `file_cards`, `toggle_alert`, `conveyor_factory`, `cta_card`, `canvas_fx` determinista por proxy GSAP, `image_cutout` para recortes transparentes de `assets/images/` y `custom_scene`), tree-shaking de CSS en `/* @scenes-css:start/end */`, cámara virtual (`camera_motion`), viñeta/grano (`film_grain`), subtítulos `hero_top` o `bottom` con cortes por puntuación y `emphasis_words`, reemplazos multi-palabra en Whisper (`--replace "lo sabrás=los abras"`), flags `--no-cut-silence` y `--no-sfx`, 15 SFX WAV (`assets/audio/`), 3 camas musicales procedurales loopables (`assets/music/`: `tension_pulse`, `tech_minimal`, `editorial_warm`) con `sidechaincompress` + `alimiter`, conector CLI `pipeline.py assets` (Iconify SVG + 18 iconos semilla, mapas Natural Earth GeoJSON CC0 y audio CC0) y procesador de imágenes `pipeline.py image` (`rembg` por IA local ONNX IS-Net 1024x1024 o extracción cromática, acabado sticker/cutout con borde y sombra, `crop` por aspect-ratio/auto-trim y `convert` Lanczos).
* **Gotcha crítico de GSAP en HyperFrames:** Todo `tl.fromTo(...)` programado en `t > 0` que anime un overlay inicialmente oculto (como flashes o alertas tardías) debe declarar `immediateRender: false` en `toVars`, pues el valor por defecto `immediateRender: true` de GSAP aplica `fromVars` desde `t = 0`.
* **Estándares visuales limpios de Jorge:** Erradicadas las pastillas en subtítulos (cero cajas alrededor de palabras), los contenedores de pastilla en badges/iconos SVG (tipografía limpia con fondo transparente y cero bordes), las barras de acento asimétricas a la izquierda en tarjetas (`border-left` eliminado a favor de bordes perimetrales simétricos) y las líneas horizontales en títulos/subtítulos (`border-top`, `border-bottom`, filetes eliminados). Codificados de forma ejecutable en la skill local `.agents/skills/diseno-video/SKILL.md`.
* **Sistema de diseño componible en 3 niveles (`core/styles.py`):** Los tokens, variantes de Nivel 2 y overrides `--set` de Nivel 3 se persisten en `package.json` (`videoDesign`).
* **Organización del repositorio:**
  * Documentación técnica centralizada exclusivamente en `docs/` (`00-indice-general.md` y subcarpetas temáticas `01-` a `05-`) y `README.md` raíz.
  * Directrices de agente y memoria persistente en `.agents/` (`AGENTS.md`, `memory.md`).
  * Integración continua activa en `.github/workflows/ci.yml` (sin directorio `ci/` duplicado).
  * `projects/` se mantiene limpio en Git (`projects/.gitkeep`) como espacio de trabajo local.
  * `pyproject.toml` es la fuente única de verdad para dependencias Python (`[project.optional-dependencies] dev`).
  * `core/styles.py` actúa como fachada sobre `core/_styles_catalog.py` (declarativo, sin flags `use_*`) y `core/_styles_renderer.py`.

## 2. Convenciones del Repositorio
* El vídeo renderizado final se exporta como `projects/<slug>/video_<slug>.mp4`.
* Las plantillas con vídeo base (`talking_head_16_9`, `talking_head_9_16`) incluyen un fixture mínimo `cut.mp4` exento en `.gitignore` para que `hyperframes check` valide sin errores.
* Las utilidades de arranque de entorno (`sys.path` y re-exec de `.venv`) viven centralizadas en `core/_runtime.py`.

## 3. Estado y Deuda Técnica
* En Windows sin `.venv` ni `node_modules` instalados, la verificación de `pytest`, `ruff` y `hyperframes check` debe ejecutarse en el entorno Linux/WSL o en CI.

## 4. Lecciones Aprendidas
* Evitar pasar contenido dinámico directamente como `repl` en `re.sub` (usar `lambda` + `html.escape`) para no fallar con backslashes o etiquetas HTML en transcripciones y títulos.
* Calcular timestamps SRT/VTT desde milisegundos enteros (`round(seconds * 1000)` + `divmod`) para evitar overflow a `1000ms`.
