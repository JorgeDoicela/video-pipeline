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

## 3. Enlaces Relacionados

* Consultar la arquitectura del motor de render en [03-motor-renderizado-hyperframes.md](./03-motor-renderizado-hyperframes.md).
* Ver la guia operativa para ejecucion de estos scripts en [05-guia-operativa-y-flujos.md](./05-guia-operativa-y-flujos.md).
