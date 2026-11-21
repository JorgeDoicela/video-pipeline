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
* **Sincronizacion de Metadatos:** Actualiza el nombre del paquete y la configuración `videoDesign` en `package.json` (`project-<slug>`).
* **Inyeccion de Parametros:** Permite fijar el titulo principal (`<h1>`) y la duracion total del video (`data-duration`) directamente por linea de comandos.

### 3.2. Argumentos de Linea de Comandos

| Parametro | Tipo | Defecto | Descripcion |
| :--- | :--- | :--- | :--- |
| `name` | `string` | *(Requerido)* | Nombre o slug del nuevo proyecto a crear en `projects/`. |
| `-t, --template` | `string` | `short_quote_9_16` | Plantilla base (`short_quote_9_16`, `short_tech_9_16`, `talking_head_9_16`, `editorial_16_9`, `talking_head_16_9`). |
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

El módulo [styles.py](../../core/styles.py) implementa una arquitectura componible en 3 niveles que desacopla los **Diseños Macro**, las **Opciones Internas de cada diseño** y los **Ajustes Puntuales (Overrides)** sin alterar el contenido del proyecto. Para la especificación completa de tokens y tablas de referencia, consulta [06-sistema-de-diseno-y-estilos.md](../04-sistema-de-diseno/01-sistema-de-diseno-y-estilos.md):

1. **Nivel 1 — Diseños Macro (`-d, --design` / [`DesignSystem`](../../core/styles.py)):**
   Cambia la arquitectura visual completa (geometría de bordes, sombras estructurales, cabeceras de contenedores, tema nativo y perfil de animación GSAP):
   * `cinematic` *(Defecto)*: Encuadre oscuro con curvas amplias (`28px`), desenfoque suave (`blur(24px)`), bordes simétricos limpios, tema nativo `dark_violet` y subtítulos `minimal_clean`.
   * `editorial`: Estética cálida de lectura con esquinas sobrias (`4px`), bordes sólidos (`2px`), tipografía limpia sin filetes decorativos, tema cálido `paper_warm` y subtítulos `minimal_clean`.
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
python3 core/pipeline.py style --list

# Nivel 1: Cambiar todo el proyecto a otro Diseño Macro diferente (ej. editorial o clean)
python3 core/pipeline.py style mi-proyecto -d editorial

# Nivel 2: Dentro de ese mismo diseño, elegir opciones internas (layout, paleta o motion)
python3 core/pipeline.py style mi-proyecto --layout asymmetric_focus --motion smooth

# Nivel 3: Ajustar propiedades puntuales solo para ese diseño
python3 core/pipeline.py style mi-proyecto --set accent_primary=#e11d48 --set stage_gap=56px

# Inspeccionar el estado efectivo de los 3 niveles en el proyecto
python3 core/pipeline.py style mi-proyecto --inspect

# Limpiar ajustes puntuales (--set) conservando el diseño y sus opciones
python3 core/pipeline.py style mi-proyecto --reset-overrides
```

---

## 4. Modulo de Subtítulos Cinéticos (`core/sync_captions.py`)

El script [sync_captions.py](../../core/sync_captions.py) convierte el archivo `transcript.json` de Whisper en etiquetas HTML estructuradas y animaciones GSAP sincronizadas palabra por palabra.

### 4.1. Funcionalidades Principales
* **Agrupación Inteligente:** Divide el habla en grupos legibles de 3 a 5 palabras, cortando de forma reactiva si detecta pausas naturales superiores a 0.4 segundos.
* **Inyección en HTML/GSAP:** Localiza el contenedor de subtítulos dentro de `index.html` y escribe tanto los elementos `<span>` como las líneas de tiempo pausadas `tl.to(...)`.
* **Exportación Estándar:** Genera archivos `.srt` y `.vtt` para distribución multiplataforma con marcas temporales exactas.

### 4.2. Argumentos de Línea de Comandos

| Parámetro | Tipo | Defecto | Descripción |
| :--- | :--- | :--- | :--- |
| `-i, --input` | `string` | *(Requerido)* | Ruta al archivo `transcript.json` emitido por Whisper. |
| `--inject` | `string` | `None` | Ruta al `index.html` donde inyectar subtítulos y código GSAP. |
| `--export-srt` | `string` | `None` | Ruta para exportar subtítulos en formato SubRip (.srt). |
| `--export-vtt` | `string` | `None` | Ruta para exportar subtítulos en formato WebVTT (.vtt). |
| `--words-per-group`| `int` | `4` | Máximo de palabras por bloque de subtítulo visible. |
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
python3 core/pipeline.py produce \
  -i /ruta/grabacion.mp4 \
  -p mi-proyecto \
  -t talking_head \
  --title "Arquitectura Cloud" \
  --auto-render
```

### 5.2. Motor Multi-Escena y Mezcla de Audio (`core/scenes.py`, `core/audio_mix.py`)

El subcomando `storyboard` compila un guion declarativo `storyboard.json` en escenas HTML/SVG secuenciadas en GSAP e inyecta una pista maestra `<audio id="master-audio">` mezclada de forma determinista con FFmpeg:

* **Componentes narrativos (`COMPONENT_REGISTRY`):** 25 primitivas universales: `timeline_steps`, `comparison_split`, `quote_focus`, `bar_chart`, `code_spotlight`, `icon_spotlight`, `phone_mockup` (modos `list` y `app_grid`, con `capture_flash` y `show_cursor`), `network_graph`, `terminal_grid`, `connector_flow`, `stat_callout`, `radar_map` (con `map_preset` desde `assets/maps/*.svg` y `route`), `xray_scanner`, `system_alert`, `hex_inspector`, `desktop_monitor`, `keyboard_type`, `padlock_denied`, `file_cards`, `toggle_alert`, `conveyor_factory`, `cta_card`, `canvas_fx` (Canvas 2D determinista conducido por proxy en GSAP), `image_cutout` (recortes transparentes PNG/WEBP desde `assets/images/`) y `custom_scene` (inyección abierta de SVG/HTML y GSAP a medida por escena).
* **Sincronización por voz (`align_storyboard_to_transcript`):** Si una escena define `cue_word`, ajusta su inicio automáticamente al instante exacto en que Whisper detecta esa palabra en `transcript.json`.
* **Vocabulario técnico y reemplazos multi-palabra (`core/transcribe.py`):** Soporta `--prompt`, `--hotwords` y `--replace "FRASE ERRONEA=FRASE CORRECTA"` para garantizar exactitud ortográfica tanto en términos individuales como en secuencias de varias palabras preservando puntuación y marcas temporales.
* **Subtítulos Hero-Top, puntuación y palabras de énfasis:** `caption_position: "hero_top"` ubica los subtítulos cinéticos como titular gigante superior, `words_per_group` controla la densidad respetando cortes naturales de puntuación, y `emphasis_words` resalta palabras clave con color secundario y `text-shadow` sin cápsulas ni pastillas.
* **Cámara virtual, textura cinematográfica y Tree-Shaking CSS:** `camera_motion: true` aplica un push-in determinista sobre `#scenes-stage`, `film_grain: true` activa viñeta radial profunda y grano sutil (`data-film-grain="true"`), y `build_scenes_css()` inyecta únicamente el CSS de los componentes utilizados en el storyboard.
* **Generación automática semántica (`build_storyboard_from_transcript`):** Construye un `storyboard.json` editable desde los segmentos de `transcript.json` mediante `--auto-storyboard`, eligiendo componentes según el contenido.
* **Atmósfera y color dinámicos por escena:** Cada escena puede conmutar `atmosphere` (`sunburst`, `grid`, `clean`) y `accent` (`primary`, `danger`, `secondary`, `warning`, `tertiary` o color hex), con cortes `snap`, `zoom_in`, `slide_up`.
* **Mezcla procedural de 15 SFX, sub-eventos y bases musicales con ducking (`core/audio_mix.py`):** Posiciona los 15 SFX de `assets/audio/` (incluyendo sub-eventos intra-escena y supresión por escena con `sfx: "none"` o global con `--no-sfx`) con `adelay`, y mezcla opcionalmente `--music` (presets `tension_pulse`, `tech_minimal`, `editorial_warm` en `assets/music/` o archivo local) o `--ambient-bed` (`drone.wav`) aplicando *ducking* automático con `sidechaincompress` y `alimiter=limit=0.95`.

```bash
python3 core/pipeline.py storyboard mi-explainer --mix-sfx
```

---

## 6. Enlaces Relacionados

* Consultar la arquitectura del motor de render en [03-motor-renderizado-hyperframes.md](../03-renderizado-y-formatos/01-motor-renderizado-hyperframes.md).
* Ver la guia operativa para ejecucion de estos scripts en [05-guia-operativa-y-flujos.md](../05-operacion-y-flujos/01-guia-operativa-y-flujos.md).
