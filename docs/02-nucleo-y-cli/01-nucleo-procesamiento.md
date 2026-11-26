# 02 — Núcleo de Procesamiento de Medios

Este documento especifica la implementacion tecnica de los componentes del nucleo de procesamiento: transcripcion con marcas temporales palabra por palabra y corte algoritmico de silencios mediante FFmpeg.

---

## 1. Modulo de Transcripcion (`core/transcribe.py`)

El script [transcribe.py](../../core/transcribe.py) se encarga de procesar la pista de audio del archivo crudo y emitir una representacion estructurada en JSON.

### 1.1. Motor de Inferencia
* **Libreria:** `faster-whisper 1.2.1` sobre `ctranslate2 4.8.5`.
* **Cuantizacion:** `int8` para ejecucion eficiente en memoria de CPU (x86_64).
* **Filtro VAD:** Utiliza Voice Activity Detection (Silero VAD integrado) para filtrar fragmentos sin actividad vocal y prevenir alucinaciones de texto.

### 1.2. Esquema de Salida (`transcript.json`)
El archivo JSON generado contiene las coordenadas temporales en segundos redondeadas al milisegundo:

```json
{
  "file": "/ruta/absoluta/al/clip.mp4",
  "language": "es",
  "language_probability": 0.9985,
  "duration": 45.320,
  "segments": [
    {
      "id": 0,
      "start": 0.420,
      "end": 2.850,
      "text": "Bienvenidos a este tutorial sobre arquitectura de software.",
      "words": [
        {
          "word": "Bienvenidos",
          "start": 0.420,
          "end": 0.980,
          "probability": 0.9942
        },
        {
          "word": "a",
          "start": 1.010,
          "end": 1.120,
          "probability": 0.9980
        }
      ]
    }
  ]
}
```

### 1.3. Argumentos de Linea de Comandos

| Parametro | Tipo | Defecto | Descripcion |
| :--- | :--- | :--- | :--- |
| `-i, --input` | `string` | *(Requerido)* | Ruta al archivo de video o audio a transcribir. |
| `-o, --output` | `string` | *(Requerido)* | Ruta destino donde se guardara el JSON estructurado. |
| `-m, --model` | `string` | `base` | Tamaño del modelo Whisper (`tiny`, `base`, `small`, `medium`, `large-v3`). |
| `-l, --language` | `string` | `es` | Codigo de idioma ISO (`es`, `en`, `auto`). |
| `-d, --device` | `string` | `cpu` | Dispositivo de computo (`cpu`, `cuda`). |

---

## 2. Modulo de Recorte de Silencios (`core/cut_silence.py`)

El script [cut_silence.py](../../core/cut_silence.py) automatiza la eliminacion de pausas muertas y muletillas prolongadas sin requerir edicion manual en linea de tiempo.

### 2.1. Algoritmo de Deteccion y Concatenacion
1. **Sondeo con `silencedetect`:**
   Se ejecuta una pasada previa no destructiva mediante el filtro de audio:
   ```bash
   ffmpeg -hide_banner -i input.mp4 -af silencedetect=noise=-30dB:d=0.45 -f null -
   ```
2. **Calculo de Intervalos Utiles:**
   Se extraen los puntos de inicio (`silence_start`) y fin (`silence_end`). Se aplica una ventana de tolerancia (*padding* de 80 ms) en los extremos para preservar la naturalidad de la fonacion.
3. **Poda y Ensamblaje (`filter_complex`):**
   Se generan tramos sincronizados de video y audio (`trim` y `atrim`), reindexando las marcas de tiempo de presentacion (`setpts=PTS-STARTPTS`) y concatenandolos en una unica pista continua mediante el filtro `concat`.

### 2.2. Argumentos de Linea de Comandos

| Parametro | Tipo | Defecto | Descripcion |
| :--- | :--- | :--- | :--- |
| `-i, --input` | `string` | *(Requerido)* | Archivo de video crudo con pausas. |
| `-o, --output` | `string` | *(Requerido)* | Archivo de video resultante con silencios eliminados. |
| `--noise-db` | `float` | `-30.0` | Umbral de presion sonora en decibeles por debajo del cual se considera silencio. |
| `--min-silence` | `float` | `0.45` | Duracion minima en segundos que debe durar la pausa para ser cortada. |

---

## 3. Modulo de Scaffolding de Proyectos (`core/create_project.py`)

El script [create_project.py](../../core/create_project.py) genera de manera limpia y automatizada nuevas estructuras de proyectos a partir de plantillas optimizadas, ajustando los metadatos y asegurando el cumplimiento del contrato de HyperFrames.

### 3.1. Funcionalidades Principales
* **Clonacion Segura:** Copia recursivamente la plantilla excluyendo caches temporales (`.hyperframes`, `frames`, `node_modules`).
* **Sincronizacion de Metadatos:** Actualiza el nombre del paquete, `videoProject` (`slug`, `channel`, `profile`, `template`, `title`, `createdAt`) y la configuracion `videoDesign` en `package.json`, y propaga `brand`/`category` del perfil a `storyboard.json` cuando existe.
* **Inyeccion de Parametros:** Permite fijar el titulo principal (`<h1>`) y la duracion total del video (`data-duration`) directamente por linea de comandos.

### 3.2. Argumentos de Linea de Comandos

| Parametro | Tipo | Defecto | Descripcion |
| :--- | :--- | :--- | :--- |
| `name` | `string` | *(Requerido)* | Nombre o slug del nuevo proyecto a crear en el workspace. |
| `-t, --template` | `string` | `None` *(del perfil o `short_quote_9_16`)* | Plantilla base (`explainer_scenes_9_16`, `explainer_scenes_16_9`, `short_quote_9_16`, `short_tech_9_16`, `talking_head_9_16`, `editorial_16_9`, `talking_head_16_9`). |
| `--profile` | `string` | `None` | Slug de perfil en `profiles/<slug>.json` o ruta directa a un JSON de perfil. |
| `--channel` | `string` | `None` *(del perfil)* | Subcarpeta relativa de canal o cliente (`tech`, `editorial`, `clientes/acme`). Bloquea rutas absolutas y `..`. |
| `--output-dir` | `string` | `None` | Directorio raiz del workspace (precedencia: `--output-dir` > `profile.output_root` > `VIDEO_PIPELINE_WORKSPACE` > `projects/`). |
| `--dated` | `flag` | `False` | Antepone el prefijo `YYYY-MM-DD_` al slug del directorio si no lo incluye ya. |
| `-d, --design` | `string` | `cinematic` | Diseño Macro de Nivel 1 (`cinematic`, `editorial`, `clean`). |
| `-s, --style` | `string` | `None` *(hereda del diseño)* | Tema cromático de Nivel 2 (`dark_violet`, `paper_warm`, `clean_light`). |
| `--layout` | `string` | `None` *(hereda del diseño)* | Variante de distribución (`standard`, `asymmetric_focus`, `stacked`). |
| `--motion` | `string` | `None` *(hereda del diseño)* | Perfil de animación GSAP (`smooth`, `snappy`, `minimal`). |
| `--caption-style` | `string` | `None` *(hereda del diseño)* | Estilo de subtítulos cinéticos (`minimal_clean`). |
| `--set` | `list[k=v]` | `None` | Overrides granulares de Nivel 3 (`--set accent_primary=#ff5500 --set stage_gap=56px`). |
| `--title` | `string` | `None` | Titulo principal para inyectar en la etiqueta `<h1>` o `#card-title` de `index.html`. |
| `--duration` | `float` | `None` | Duracion total en segundos para el atributo `data-duration`. |
| `-f, --force` | `flag` | `False` | Sobrescribe el directorio destino si ya existia previamente. |

---

## 3.3. Motor Jerárquico de Sistemas de Diseño en 3 Niveles (`core/styles.py`)

El módulo [styles.py](../../core/styles.py) implementa una arquitectura componible en 3 niveles que desacopla los **Diseños Macro**, las **Opciones Internas de cada diseño** y los **Ajustes Puntuales (Overrides)** sin alterar el contenido del proyecto. Para la especificación completa de tokens y tablas de referencia, consulta [01-sistema-de-diseno-y-estilos.md](../04-sistema-de-diseno/01-sistema-de-diseno-y-estilos.md):

1. **Nivel 1 — Diseños Macro (`-d, --design` / [`DesignSystem`](../../core/styles.py)):**
   Cambia la arquitectura visual completa (geometría de bordes, sombras estructurales, cabeceras de contenedores, tema nativo y perfil de animación GSAP):
   * `cinematic` *(Defecto)*: Encuadre oscuro con curvas amplias (`28px`), desenfoque suave (`blur(24px)`), bordes simétricos limpios, tema nativo `dark_violet` y subtítulos `minimal_clean`.
   * `editorial`: Estética cálida y serena de lectura con fondo marfil (`#f5f1ea`), esquinas suaves (`20px`), bordes finos (`1px`), sombra difusa cálida, ocultamiento automático de la barra de progreso superior (`#progress-bar`) y cabecera de marca (`#brand-bar`), titulares estilizados de ancho contenido (`font-size: 56px`/`54px`, `font-weight: 700`, `text-transform: none`, `max-width: 780px`/`1020px`, `text-wrap: balance`), tema `paper_warm` (latón dorado `#875c22` y carmesí terracota `#8c2d19`) y subtítulos `minimal_clean`.
   * `clean`: Tarjetas blancas minimalistas con radios de `24px`, sombras multicapa suaves, tema nativo `clean_light` y animación `smooth`.

2. **Nivel 2 — Opciones Internas dentro de un mismo Diseño:**
   Permite personalizar sub-dimensiones manteniendo el Diseño Macro activo:
   * **Temas Cromáticos (`-s, --style`):** `dark_violet`, `paper_warm`, `clean_light`.
   * **Distribución de Escenario (`--layout`):** `standard` (2 columnas simétricas, lower-third izquierda), `asymmetric_focus` (proporción 60/40, lower-third derecha), `stacked` (filas apiladas verticales).
   * **Perfil de Animación GSAP (`--motion`):** `smooth`, `snappy`, `minimal`.
   * **Estilo de Subtítulos (`--caption-style`):** `minimal_clean` (estándar único limpio sin pastillas).

3. **Nivel 3 — Ajustes Granulares sobre un solo Diseño (`--set clave=valor`):**
   Permite modificar propiedades específicas únicamente en el proyecto/diseño actual (persistidas en `package.json` bajo `videoDesign.overrides`) e inspeccionar la configuración activa con `--inspect`:

```bash
# Listar catálogo completo de los 3 niveles (o en JSON con --json)
uv run python core/pipeline.py style --list

# Nivel 1: Cambiar todo el proyecto a otro Diseño Macro diferente (ej. editorial o clean)
uv run python core/pipeline.py style mi-proyecto -d editorial

# Nivel 2: Dentro de ese mismo diseño, elegir opciones internas (layout, paleta o motion)
uv run python core/pipeline.py style mi-proyecto --layout asymmetric_focus --motion smooth

# Nivel 3: Ajustar propiedades puntuales solo para ese diseño
uv run python core/pipeline.py style mi-proyecto --set accent_primary=#e11d48 --set stage_gap=56px

# Inspeccionar el estado efectivo de los 3 niveles en el proyecto
uv run python core/pipeline.py style mi-proyecto --inspect

# Limpiar ajustes puntuales (--set) conservando el diseño y sus opciones
uv run python core/pipeline.py style mi-proyecto --reset-overrides
```

---

## 4. Modulo de Subtítulos Cinéticos (`core/sync_captions.py`)

El script [sync_captions.py](../../core/sync_captions.py) convierte el archivo `transcript.json` de Whisper en etiquetas HTML estructuradas y animaciones GSAP sincronizadas palabra por palabra.

### 4.1. Funcionalidades Principales
* **Agrupación Inteligente y Sin Solapamiento Temporal:** Divide el habla en bloques balanceados de 1 a 2 líneas (hasta 6 palabras por defecto, con `text-wrap: balance` y `max-width: 780px` en 9:16 o `1180px` en 16:9), cortando de forma reactiva ante pausas superiores a 0.4 segundos o signos de puntuación, y garantizando cero solapamiento temporal entre bloques consecutivos (`hide_time = min(g_end + 0.15, next_start)`) para evitar saltos verticales al cambiar de frase.
* **Inyección en HTML/GSAP y Limpieza sin Habla:** Localiza el contenedor de subtítulos dentro de `index.html` y escribe tanto los elementos `<span>` como las líneas de tiempo pausadas `tl.to(...)`. Cuando Whisper no detecta habla (`0` palabras), `clear_captions_in_html` limpia los subtítulos placeholder y tweens residuales de la plantilla.
* **Exportación Estándar:** Genera archivos `.srt` y `.vtt` para distribución multiplataforma con marcas temporales exactas.

### 4.2. Argumentos de Línea de Comandos

| Parámetro | Tipo | Defecto | Descripción |
| :--- | :--- | :--- | :--- |
| `-i, --input` | `string` | *(Requerido)* | Ruta al archivo `transcript.json` emitido por Whisper. |
| `--inject` | `string` | `None` | Ruta al `index.html` donde inyectar subtítulos y código GSAP. |
| `--export-srt` | `string` | `None` | Ruta para exportar subtítulos en formato SubRip (.srt). |
| `--export-vtt` | `string` | `None` | Ruta para exportar subtítulos en formato WebVTT (.vtt). |
| `--words-per-group`| `int` | `6` | Máximo de palabras por bloque de subtítulo visible (1–2 líneas balanceadas). |
| `--pause-threshold`| `float` | `0.4` | Pausa en segundos para forzar el salto de frase. |

---

## 5. Orquestador Maestro de Producción (`core/pipeline.py`)

El script [pipeline.py](../../core/pipeline.py) centraliza la ejecución de todas las herramientas en un único flujo declarativo.

### 5.1. Subcomando `produce` (End-to-End)
Ejecuta de forma secuencial:
1. Creación del proyecto base (`create_project`).
2. Poda de pausas con FFmpeg (`cut_silence`).
3. Transcripción con Whisper int8 (`transcribe`).
4. Generación e inyección de subtítulos cinéticos (`sync_captions`).
5. Validación estricta con `hyperframes check`.
6. Opcionalmente, renderizado acelerado por GPU (`hyperframes render`).

```bash
uv run python core/pipeline.py produce \
  -i grabacion.mp4 \
  -p mi-proyecto \
  -t talking_head_16_9 \
  --title "Arquitectura Cloud" \
  --auto-render
```

### 5.2. Motor Multi-Escena y Mezcla de Audio (`core/scenes.py`, `core/audio_mix.py`)

El subcomando `storyboard` compila un guion declarativo `storyboard.json` en escenas HTML/SVG secuenciadas en GSAP e inyecta una pista maestra `<audio id="master-audio">` mezclada de forma determinista con FFmpeg:

* **Componentes narrativos (`COMPONENT_REGISTRY`):** 30 primitivas universales: `timeline_steps`, `comparison_split`, `quote_focus`, `bar_chart`, `code_spotlight`, `icon_spotlight`, `phone_mockup` (modos `list` y `app_grid`, con `capture_flash` y `show_cursor`), `network_graph`, `terminal_grid`, `connector_flow`, `stat_callout`, `radar_map` (con `map_preset` desde `assets/maps/*.svg` y `route`), `xray_scanner`, `system_alert`, `hex_inspector`, `desktop_monitor`, `keyboard_type`, `padlock_denied`, `file_cards`, `toggle_alert`, `conveyor_factory`, `cta_card`, `canvas_fx` (Canvas 2D determinista conducido por proxy en GSAP), `image_cutout` (recortes transparentes PNG/WEBP desde `assets/images/`), `infinite_canvas` (cámara virtual 2D sobre lienzo continuo con nodos conectados por curvas Bezier y zoom-out final), `svg_draw` (trazos SVG progresivos sincronizados con timestamps mediante `stroke-dashoffset` y `MotionPathPlugin`), `scene_3d` (motor WebGL 3D determinista sobre Three.js con 9 primitivos procedurales, carga de modelos `.glb`/`.gltf` mediante `GLTFLoader` y grilla de puntos 3D en perspectiva), `video_clip` (clips de video reales de presentador o B-roll en modos `card`, `full` y `pip`), `manim_clip` (escenas matemáticas/algorítmicas de Manim compiladas bajo demanda con la paleta del proyecto en `16:9`/`9:16` o canal alfa) y `custom_scene` (inyección abierta de SVG/HTML y GSAP a medida por escena).
* **Sincronización por voz (`align_storyboard_to_transcript`):** Si una escena define `cue_word`, ajusta su inicio automáticamente al instante exacto en que Whisper detecta esa palabra en `transcript.json`.
* **Vocabulario técnico y reemplazos multi-palabra (`core/transcribe.py`):** Soporta `--prompt`, `--hotwords` y `--replace "FRASE ERRONEA=FRASE CORRECTA"` para garantizar exactitud ortográfica tanto en términos individuales como en secuencias de varias palabras preservando puntuación y marcas temporales.
* **Subtítulos Hero-Top, puntuación y palabras de énfasis:** `caption_position: "hero_top"` ubica los subtítulos cinéticos como titular gigante superior, `words_per_group` controla la densidad respetando cortes naturales de puntuación, y `emphasis_words` resalta palabras clave con color secundario y `text-shadow` sin cápsulas ni pastillas.
* **Cámara virtual, textura cinematográfica y Tree-Shaking CSS:** `camera_motion: true` aplica un push-in determinista sobre `#scenes-stage`, `film_grain: true` activa viñeta radial profunda y grano sutil (`data-film-grain="true"`), y `build_scenes_css()` inyecta únicamente el CSS de los componentes utilizados en el storyboard.
* **Generación automática semántica (`build_storyboard_from_transcript`):** Construye un `storyboard.json` editable desde los segmentos de `transcript.json` mediante `--auto-storyboard`, eligiendo componentes según el contenido.
* **Atmósfera y color dinámicos por escena:** Cada escena puede conmutar `atmosphere` (`sunburst`, `grid`, `clean`) y `accent` (`primary`, `danger`, `secondary`, `warning`, `tertiary` o color hex), con cortes `snap`, `zoom_in`, `slide_up`.
* **Mezcla procedural de 15 SFX, limpieza vocal y bases musicales con ducking (`core/audio_mix.py`):** Posiciona los 15 SFX base y cualquier `.wav` personalizado autodescubierto en `assets/audio/` (importable y normalizable a WAV 48 kHz 16-bit con `assets audio <nombre> --file <ruta>|--url <url>|--freesound <consulta> --type sfx|music`), soporta sub-eventos intra-escena y supresión por escena (`sfx: "none"` o `--no-sfx`) con `adelay`, aplica opcionalmente la cadena de limpieza vocal de estudio `--voice-polish` (`highpass=f=80`, `afftdn=nf=-25`, `acompressor` y `loudnorm=I=-14:TP=-1.5:LRA=11`) antes del *sidechain*, y mezcla `--music` (presets `tension_pulse`, `tech_minimal`, `editorial_warm` o cualquier pista `.wav` personalizada en `assets/music/` referenciada por slug) o `--ambient-bed` (`drone.wav`) aplicando *ducking* automático con `sidechaincompress` y `alimiter=limit=0.95`. También vincula automáticamente la pista de audio en plantillas sin storyboard (`talking_head_9_16`, `talking_head_16_9`, etc.).

```bash
uv run python core/pipeline.py storyboard mi-explainer --mix-sfx
```

### 5.3. Capa de Workspace, Perfiles de Canal e Historial (`core/workspace.py`)

El modulo [workspace.py](../../core/workspace.py) centraliza la operacion multi-canal y de clientes mediante perfiles JSON validados en `profiles/`, resolucion segura de rutas y registro append-only en `catalog.jsonl`:

| Subcomando | Accion | Descripcion |
| :--- | :--- | :--- |
| `profiles list [--json]` | Listar | Muestra los perfiles registrados en `profiles/` (`tech_short`, `editorial_essay`, `client_clean` y personalizados). |
| `profiles show <slug\|ruta>` | Inspeccionar | Imprime el esquema JSON completo validado del perfil indicado. |
| `profiles init <slug> [opts]` | Crear | Genera y valida un nuevo perfil en `profiles/<slug>.json` (`--channel`, `-t`, `-d`, `-s`, `--layout`, `--motion`, `--set`, `--music`, `--voice-polish`, `--output-root`). |
| `history [--channel] [--profile] [--limit] [--output-dir] [--json]` | Consultar | Lee `<workspace>/catalog.jsonl` ordenado del evento mas reciente al mas antiguo (`scaffold`, `produce`, `render`). |

> [!NOTE]
> El orden de precedencia para resolver la raiz del workspace es: `--output-dir` en CLI > `output_root` del perfil > variable de entorno `VIDEO_PIPELINE_WORKSPACE` > directorio local `projects/`. En `core/scenes.py`, `_sync_local_3d_assets` valida de forma *fail-fast* la presencia del runtime local de Three.js (`node_modules/three/build/`) y de los modelos `.glb`/`.gltf` referenciados.

### 5.4. Integracion Manim Community (`core/manim_tools.py`)

El modulo [manim_tools.py](../../core/manim_tools.py) permite compilar escenas matematicas, geometricas y algoritmicas en Manim Community sincronizadas con los tokens de diseno del proyecto (`VP_MANIM_PALETTE_JSON` inyectado desde `package.json`) y sin requerir LaTeX para operar:

* **Comandos CLI:** `manim doctor`, `manim presets [--json]`, `manim seed [--force]`, `manim list [--json]`, `manim new <slug> --preset <math_proof|algorithm_flow|vector_field|fourier_epicycles|neural_network|matrix_transform|sorting_algorithm>` y `manim render <script> [--project] [--aspect 16:9|9:16] [--quality preview|hd|prod] [--transparent]`.
* **Biblioteca semilla (`assets/manim/`):** 5 escenas listas para usar y adaptar (`demo_sine_wave.py`, `fourier_series.py`, `neural_forward.py`, `matrix_transform.py`, `sorting_bars.py`) usando el helper limpio `build_scene_header()` y los 3 temas del pipeline.
* **Integracion declarativa:** El componente `manim_clip` en `core/scenes.py` compila bajo demanda el `.py` si el video no existe o si cambiaron el script o `package.json`, y valida de forma *fail-fast* su existencia.

### 5.5. Exportador Modular para Editores NLE (`core/nle_export.py`)

El modulo [nle_export.py](../../core/nle_export.py) empaqueta cualquier proyecto renderizado (las 7 plantillas base y composiciones full-bleed) en un directorio autocontenido `<proyecto>/export_nle/` listo para importar en DaVinci Resolve (Free y Studio), Adobe Premiere Pro y Final Cut Pro:

| Artefacto | Descripcion tecnica |
| :--- | :--- |
| `01_video_clips/` | Clips MP4 (H.264 `crf 16`, sin pista de audio) cortados por escenas de `storyboard.json` o marcas `--cuts` usando conteo exacto de fotogramas (`-frames:v` y `-r <fps>`), garantizando sincronia 1:1 con el XML. Con `--split-layers`, separa capa base (`*_bg.mp4`) y overlay con canal alfa (`*_overlay.mov` ProRes 4444 `yuva444p10le` o `*_overlay.webm` VP9 `yuva420p`). |
| `02_audio_stems/` | Pistas WAV PCM 48 kHz 16-bit independientes (`stem_voz.wav`, `stem_musica.wav`, `stem_sfx.wav`, o `stem_master.wav` en piezas full-bleed sin storyboard). |
| `03_subtitulos/` | Copia de `subtitles.srt` y `subtitles.vtt` editables si existen en el proyecto. |
| `timeline.fcpxml` | Proyecto FCPXML v1.10 con marcadores por acto, `FFVideoFormat<H>p<FPS>` para `16:9` estandar y `FFVideoFormatRateUndefined` para vertical `9:16` u otras resoluciones, insercion automatica de `<gap>` en `<spine>` si existen huecos, overlays alfa en `lane="1"` y stems anclados en `t=0s` en `lane="-1"`, `"-2"`, `"-3"`. |
| `manifest.json` | Inventario estructurado de resolucion, FPS, clips, capas, stems y subtitulos exportados. |

---

## 6. Enlaces Relacionados

* Consultar la arquitectura del motor de render en [01-motor-renderizado-hyperframes.md](../03-renderizado-y-formatos/01-motor-renderizado-hyperframes.md).
* Ver la guia operativa para ejecucion de estos scripts en [01-guia-operativa-y-flujos.md](../05-operacion-y-flujos/01-guia-operativa-y-flujos.md).
