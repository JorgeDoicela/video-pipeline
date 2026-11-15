# Memoria Técnica del Proyecto — video-pipeline

## 1. Decisiones Arquitectónicas
* **Pipeline 100% local:** Transcripción con `faster-whisper` (`int8`), recorte de silencios con `FFmpeg`, renderizado determinista con HyperFrames + GSAP `3.15.0` (prohibido `transition:` en CSS).
* **Catálogo de 11 plantillas multitemáticas:** 9 técnicas/sociales + 2 editoriales/narrativas sin código (`verse_quote_9_16` en 9:16 y `editorial_story` en 16:9), todas compatibles con el sistema de diseño en 3 niveles (`core/styles.py`).
* **Sistema de diseño componible en 3 niveles (`core/styles.py`):** 7 Diseños Macro (`cyber_glass`, `clean_studio`, `swiss_editorial`, `brutalist_terminal`, `cinematic_studio`, `bento_grid`, `academic_paper`), variantes internas de Nivel 2 y overrides `--set` de Nivel 3 persistidos en `package.json` (`videoDesign`).
* **Organización del repositorio:**
  * Documentación técnica centralizada exclusivamente en `docs/` (`00-indice-general.md` y subcarpetas temáticas `01-` a `05-`) y `README.md` raíz.
  * Directrices de agente y memoria persistente en `.agents/` (`AGENTS.md`, `memory.md`).
  * Integración continua activa en `.github/workflows/ci.yml` (sin directorio `ci/` duplicado).
  * `projects/` se mantiene limpio en Git (`projects/.gitkeep`) como espacio de trabajo local.
  * `pyproject.toml` es la fuente única de verdad para dependencias Python (`[project.optional-dependencies] dev`).
  * `core/styles.py` actúa como fachada sobre `core/_styles_catalog.py` (declarativo, sin flags `use_*`) y `core/_styles_renderer.py`.

## 2. Convenciones del Repositorio
* El vídeo renderizado final se exporta como `projects/<slug>/video_<slug>.mp4`.
* Las plantillas con vídeo base (`talking_head`, `talking_head_9_16`) incluyen un fixture mínimo `cut.mp4` exento en `.gitignore` para que `hyperframes check` valide sin errores.
* Las utilidades de arranque de entorno (`sys.path` y re-exec de `.venv`) viven centralizadas en `core/_runtime.py`.

## 3. Estado y Deuda Técnica
* En Windows sin `.venv` ni `node_modules` instalados, la verificación de `pytest`, `ruff` y `hyperframes check` debe ejecutarse en el entorno Linux/WSL o en CI.

## 4. Lecciones Aprendidas
* Evitar pasar contenido dinámico directamente como `repl` en `re.sub` (usar `lambda` + `html.escape`) para no fallar con backslashes o etiquetas HTML en transcripciones y títulos.
* Calcular timestamps SRT/VTT desde milisegundos enteros (`round(seconds * 1000)` + `divmod`) para evitar overflow a `1000ms`.
