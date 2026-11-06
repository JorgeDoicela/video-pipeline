# Video Pipeline

Entorno local automatizado de produccion y edicion de video programatico gobernado por agentes de inteligencia artificial y codigo declarativo.

El sistema resuelve el problema del costo y la friccion de la edicion audiovisual manual mediante una tuberia local que sincroniza modelos de transcripcion temporalizada con motores de composicion web (HTML5, SVG y GSAP) y aceleracion grafica por hardware, operando bajo una politica estricta de **cero costes adicionales**.

---

## 1. Requisitos Previos y Compatibilidad de Entorno

* **Sistema Operativo:** Linux (Debian 13 Trixie / Nix Flakes).
* **Controlador Grafico:** AMDGPU con aceleracion VA-API y Mesa nativo (`radeonsi_dri.so`).
* **FFmpeg:** Version 7.1 o superior compilada con soporte DRM y VA-API (`/usr/bin/ffmpeg`).
* **Node.js:** Version 22 LTS o superior y gestor `pnpm`.
* **Python:** Version 3.10 o superior (ejecutado con `uv`).

---

## 2. Inicio Rápido (Quickstart)

### Paso 1: Configurar el Entorno Virtual de Python
```bash
# Clonar el repositorio y acceder al directorio
git clone https://github.com/<tu-usuario>/video-pipeline.git
cd video-pipeline

# Crear y activar entorno virtual
uv venv .venv
uv pip install --python .venv/bin/python -r requirements.txt
```

### Paso 2: Instalar Dependencias de Node.js
```bash
pnpm install
```

### Paso 3: Asegurar el Navegador Headless para Renderizado
```bash
pnpm exec hyperframes browser ensure
```

### Paso 4: Validar la Salud del Sistema
```bash
pnpm exec hyperframes doctor
```

---

## 3. Comandos Principales

| Tarea | Comando | Descripcion Tecnica |
| :--- | :--- | :--- |
| **Diagnostico** | `pnpm exec hyperframes doctor` | Verifica dependencias del sistema, GPU, FFmpeg y Chrome cache. |
| **Transcripcion** | `.venv/bin/python core/transcribe.py -i <in> -o <out.json>` | Genera marcas de tiempo palabra por palabra con `faster-whisper`. |
| **Corte de Silencios** | `core/cut_silence.py -i <in> -o <out.mp4>` | Elimina pausas muertas mayores a 0.45s mediante filtros de FFmpeg. |
| **Previsualizacion** | `pnpm exec hyperframes preview` | Inicia el estudio visual interactivo en `localhost:3000`. |
| **Renderizado MP4** | `pnpm exec hyperframes render -o <out.mp4>` | Compila la escena web a video MP4 utilizando aceleracion GPU. |
| **Limpieza de Cache** | `pnpm exec hyperframes clean` | Purga fotogramas temporales acumulados en `/tmp`. |

---

## 4. Estructura del Directorio

```text
video-pipeline/
├── assets/                 # Recursos locales reutilizables
│   ├── audio/             # Efectos de sonido libres (WAV/MP3)
│   ├── fonts/             # Tipografías del sistema
│   └── icons/             # Iconos vectoriales en formato SVG
├── core/                   # Herramientas del motor compartido
│   ├── transcribe.py      # Transcripción local con timestamps (faster-whisper)
│   └── cut_silence.py     # Algoritmo de poda de silencios (FFmpeg)
├── docs/                   # Biblioteca documental técnica Docs-as-Code
│   ├── 00-indice-general.md
│   ├── 01-arquitectura-sistema.md
│   ├── 02-nucleo-procesamiento.md
│   ├── 03-motor-renderizado-hyperframes.md
│   ├── 04-formatos-de-video.md
│   └── 05-guia-operativa-y-flujos.md
├── templates/              # Plantillas base para generación por IA
│   ├── talking_head/      # Overlays, subtítulos cinéticos y lower-thirds
│   └── tech_explainer/    # Diagramas de infraestructura SVG y bloques de código
├── projects/               # Espacio de trabajo para producciones individuales
│   └── demo/              # Proyecto piloto validado funcionalmente
├── package.json           # Dependencias de HyperFrames y scripts de ejecución
├── requirements.txt       # Dependencias fijadas del runtime de Python
└── README.md              # Guía de entrada y especificación del repositorio
```

---

## 5. Documentación Técnica Detallada (Docs-as-Code)

La documentacion completa del sistema se encuentra organizada bajo taxonomia jerarquica numerica dentro de la carpeta `docs/`.

Consulta el catalogo maestro:
* [Documentación Técnica Completa](docs/00-indice-general.md)

### Indice de Modulos Documentales:
1. [01 — Arquitectura del Sistema](docs/01-arquitectura-sistema.md): Separacion en 3 capas (Debian, Nix, Workspace), filosofia de coste cero y topologia del pipeline.
2. [02 — Núcleo de Procesamiento de Medios](docs/02-nucleo-procesamiento.md): Especificacion de `faster-whisper`, esquema de `transcript.json` y filtros de corte en FFmpeg.
3. [03 — Motor de Renderizado (HyperFrames)](docs/03-motor-renderizado-hyperframes.md): Modelo temporal en segundos, Chromium Headless Shell y aceleracion por hardware GPU.
4. [04 — Formatos de Video Soportados](docs/04-formatos-de-video.md): Contratos de diseño para Talking Head y Explicaciones Tecnicas con SVG.
5. [05 — Guía Operativa y Flujos de Trabajo](docs/05-guia-operativa-y-flujos.md): Runbooks secuenciales desde la grabacion hasta la exportacion final.

---

## 6. Seguridad y Licencia

* **Gestion de Secretos:** Este entorno no almacena claves privadas ni tokens de pago. Toda la inferencia y procesamiento se ejecuta de manera local y desconectada.
* **Licencia:** El entorno se compone de herramientas de codigo abierto bajo licencias permisivas (Apache 2.0 para HyperFrames, MIT para CTranslate2/Whisper y LGPL/GPL para FFmpeg).
