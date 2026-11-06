# 02 — Núcleo de Procesamiento de Medios

Este documento especifica la implementacion tecnica de los componentes del nucleo de procesamiento: transcripcion con marcas temporales palabra por palabra y corte algoritmico de silencios mediante FFmpeg.

---

## 1. Modulo de Transcripcion (`core/transcribe.py`)

El script [transcribe.py](../core/transcribe.py) se encarga de procesar la pista de audio del archivo crudo y emitir una representacion estructurada en JSON.

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

El script [cut_silence.py](../core/cut_silence.py) automatiza la eliminacion de pausas muertas y muletillas prolongadas sin requerir edicion manual en linea de tiempo.

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

El script [create_project.py](../core/create_project.py) genera de manera limpia y automatizada nuevas estructuras de proyectos a partir de plantillas optimizadas, ajustando los metadatos y asegurando el cumplimiento del contrato de HyperFrames.

### 3.1. Funcionalidades Principales
* **Clonacion Segura:** Copia recursivamente la plantilla excluyendo caches temporales (`.hyperframes`, `frames`, `node_modules`).
* **Sincronizacion de Metadatos:** Actualiza el nombre del paquete en `package.json` (`project-<slug>`) y configura `hyperframes.json`.
* **Inyeccion de Parametros:** Permite fijar el titulo principal (`<h1>`) y la duracion total del video (`data-duration`) directamente por linea de comandos.

### 3.2. Argumentos de Linea de Comandos

| Parametro | Tipo | Defecto | Descripcion |
| :--- | :--- | :--- | :--- |
| `name` | `string` | *(Requerido)* | Nombre o slug del nuevo proyecto a crear en `projects/`. |
| `-t, --template` | `string` | `portrait_9_16` | Plantilla base (`portrait_9_16`, `landscape_16_9`, `square_1_1`, `talking_head`, `tech_explainer`). |
| `--title` | `string` | `None` | Titulo principal para inyectar en la etiqueta `<h1>` de `index.html`. |
| `--duration` | `float` | `None` | Duracion total en segundos para el atributo `data-duration`. |
| `-f, --force` | `flag` | `False` | Sobrescribe el directorio destino si ya existia previamente. |

---

## 4. Modulo de Subtítulos Cinéticos (`core/sync_captions.py`)

El script [sync_captions.py](../core/sync_captions.py) convierte el archivo `transcript.json` de Whisper en etiquetas HTML estructuradas y animaciones GSAP sincronizadas palabra por palabra.

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

El script [pipeline.py](../core/pipeline.py) centraliza la ejecución de todas las herramientas en un único flujo declarativo.

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

---

## 6. Enlaces Relacionados

* Consultar la arquitectura del motor de render en [03-motor-renderizado-hyperframes.md](./03-motor-renderizado-hyperframes.md).
* Ver la guia operativa para ejecucion de estos scripts en [05-guia-operativa-y-flujos.md](./05-guia-operativa-y-flujos.md).
