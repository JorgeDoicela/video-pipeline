# 07 — Recursos Estáticos y Assets

Este documento especifica los activos estáticos reutilizables alojados en [`assets/`](../../assets/) para las composiciones de HyperFrames y los scripts del núcleo.

---

## 1. Efectos de Sonido Locales (`assets/audio/`)

Todos los archivos son WAV PCM estéreo a 48,000 Hz, 16 bits, sintetizados matemáticamente mediante [`core/generate_sfx.py`](../../core/generate_sfx.py) y libres de derechos (CC0 / Dominio Público).

| Archivo | Duración | Uso Recomendado en GSAP |
| :--- | :--- | :--- |
| `whoosh.wav` | `0.38s` | Transiciones de cámara, entradas de paneles o swipes rápidos. |
| `pop.wav` | `0.09s` | Aparición de badges, tags, burbujas o elementos flotantes. |
| `click.wav` | `0.03s` | Clicks táctiles de botones, toggles o selección de pestañas. |
| `chime.wav` | `0.85s` | Conclusión de procesos, transacciones exitosas o métricas clave. |
| `beep.wav` | `0.08s` | Logs de consola, llegada de paquetes de red o comandos CLI. |
| `sub_hit.wav` | `0.55s` | Impacto sub-grave para apertura de escena, títulos hook o revelaciones. |
| `glitch.wav` | `0.16s` | Alertas críticas, errores de sistema o cambios bruscos de estado. |
| `scan.wav` | `0.34s` | Barridos de radar táctico, escáneres láser HUD e inspección de rayos X. |
| `drone.wav` | `4.00s` | Cama ambiental grave armónica (ciclo exacto loopable con *ducking* automático). |
| `shutter.wav` | `0.14s` | Doble clic mecánico de obturador de cámara para capturas de pantalla (`phone_mockup`). |
| `riser.wav` | `1.10s` | Ascenso de tensión filtrado para revelaciones narrativas y cierres (`cta_card`). |
| `boom.wav` | `0.85s` | Sub-impacto cinematográfico grave para titulares, giros clave o estampado (`conveyor_factory`). |
| `keyclick.wav` | `0.045s` | Pulsación mecánica nítida de teclado (`keyboard_type`). |
| `powerdown.wav` | `0.55s` | Caída de tono tipo apagón CRT o reinicio forzado de sistema (`toggle_alert`). |
| `alarm.wav` | `0.36s` | Doble pulso táctico de advertencia o alerta de sistema (`system_alert`). |

### 1.1. Bases Musicales Instrumentales (`assets/music/`)

Pistas WAV PCM estéreo a 48,000 Hz, 16 bits, de `8.00s` perfectamente loopables (frecuencias múltiplos exactos de `0.125 Hz`), además de admitir cualquier archivo `.wav` o `.mp3` CC0 colocado en `assets/music/`:

| Preset / Archivo | Duración | Tono y Uso Recomendado |
| :--- | :--- | :--- |
| `tension_pulse.wav` | `8.00s` (loop) | Pulso oscuro a 120 BPM con sub-bajo y pad para ciberseguridad e investigación. |
| `tech_minimal.wav` | `8.00s` (loop) | Base minimalista limpia para arquitectura de software, código y tutoriales. |
| `editorial_warm.wav` | `8.00s` (loop) | Cama ambiental cálida y sobria para ensayos, historia y documentales. |

### Integración en HyperFrames / Mezcla FFmpeg (`core/audio_mix.py`)
Además de la vinculación directa como `<audio>` por evento, [`core/audio_mix.py`](../../core/audio_mix.py) invoca `ensure_sfx_assets()` y mezcla la pista de voz con todos los eventos SFX del storyboard en un único archivo maestro `audio_mix.wav` mediante `adelay`, `amix` y limitación de picos `alimiter=limit=0.95`.

```html
<!-- Pista maestra compilada por core/audio_mix.py -->
<audio id="master-audio" src="audio_mix.wav" data-start="0" data-duration="12.00" data-track-index="0" data-volume="1"></audio>
```

Para regenerar o ajustar los efectos de sonido:
```bash
uv run python core/generate_sfx.py
```

---

## 2. Iconografía Técnica Vectorial (`assets/icons/`)

Iconos SVG monocromáticos con `viewBox="0 0 24 24"`, diseñados con `stroke="currentColor"` y gestionados mediante [`core/fetch_assets.py`](../../core/fetch_assets.py) (`ensure_base_icons` y descarga desde Iconify) para adoptar dinámicamente el color del texto o acento CSS circundante.

| Icono | Archivo | Concepto Técnico |
| :--- | :--- | :--- |
| **Server** | `server.svg` | Nodos de cómputo, microservicios, racks de servidores. |
| **Database** | `database.svg` | Bases de datos relacionales, almacenamiento persistente. |
| **Cloud** | `cloud.svg` | Servicios en la nube, infraestructura abstracta. |
| **Docker** | `docker.svg` | Contenedores, imágenes y empaquetado OCI. |
| **Kubernetes** | `kubernetes.svg` | Orquestación de clústeres, pods y servicios K8s. |
| **Kafka** | `kafka.svg` | Event streaming, tópicos distribuidos, colas pub/sub. |
| **Redis** | `redis.svg` | Caché en memoria, almacenes clave-valor ultrarrápidos. |
| **Git** | `git.svg` | Control de versiones, branches, pipelines de CI/CD. |
| **CPU** | `cpu.svg` | Procesamiento por hardware, métricas de carga, núcleos. |
| **Terminal** | `terminal.svg` | Comandos CLI, shell de Linux, logs de sistema. |
| **Shield** | `shield.svg` | Seguridad, defensa perimetral, protección del sistema. |
| **Lock** | `lock.svg` | Cifrado, control de acceso, bloqueo de credenciales. |
| **Eye** | `eye.svg` | Vigilancia, monitoreo, telemetría, auditoría visual. |
| **Globe** | `globe.svg` | Red global, DNS, tráfico internacional, geopolítica. |
| **Smartphone** | `smartphone.svg` | Dispositivos móviles, endpoints de usuario, apps. |
| **Alert** | `alert.svg` | Advertencias críticas, vulnerabilidades, incidentes. |
| **Key** | `key.svg` | Llaves criptográficas, tokens de autenticación, SSH. |
| **Radar** | `radar.svg` | Escaneo activo, detección de amenazas, rastreo. |

---

## 2.1. Mapas Geográficos Vectoriales (`assets/maps/`)

Siluetas geográficas SVG con `viewBox="0 0 880 680"` integradas con los tokens CSS del sistema (`var(--accent-primary-soft)`, `var(--scene-accent)`, `var(--border-strong)`), cargadas automáticamente por el componente `radar_map` mediante `map_preset`:

| Preset (`map_preset`) | Archivo | Regiones Incluidas |
| :--- | :--- | :--- |
| `korea` | `korea.svg` | Península coreana (Corea del Norte destacada, Corea del Sur, Jeju y línea DMZ). |
| `world` | `world.svg` | Mapa mundi continental (Norteamérica, Sudamérica, Europa, África, Asia, Oceanía). |
| `europe` | `europe.svg` | Europa continental, Escandinavia y Reino Unido/Irlanda. |
| `americas` | `americas.svg` | Norteamérica, Centroamérica y Sudamérica. |
| `asia` | `asia.svg` | Asia continental, Península Coreana destacada y archipiélago de Japón. |

### Uso en HTML
```html
<!-- Carga directa como imagen vectorial -->
<img src="../../assets/icons/docker.svg" width="32" height="32" style="filter: drop-shadow(0 0 8px #38bdf8);" alt="Docker" />
```

Para regenerar o restaurar los 18 iconos vectoriales semilla:
```bash
uv run python core/pipeline.py assets seed-icons
```

---

## 3. Tipografías (`assets/fonts/`)

Directorio destinado a fuentes tipográficas locales en formato WOFF2 o TTF cuando se requiera operar de forma totalmente aislada de la red. Por defecto, HyperFrames cachea Google Fonts localmente en `~/.cache/hyperframes/fonts/`.

---

## 3.5. Gestor y Descargador de Assets Abiertos (`core/fetch_assets.py` / `pipeline.py assets`)

El módulo [`core/fetch_assets.py`](../../core/fetch_assets.py) (integrado como subcomando `pipeline.py assets`) conecta el pipeline con catálogos abiertos CC0/MIT para descargar, normalizar y cachear activos en `assets/` manteniendo el renderizado 100% local:

1. **Iconos y Logos SVG desde Iconify (Lucide, Tabler, Simple Icons — MIT/CC0, sin API Key):**
   ```bash
   # Descargar icono de Lucide o Tabler a assets/icons/<slug>.svg
   uv run python core/pipeline.py assets icon lucide:shield-alert
   uv run python core/pipeline.py assets icon tabler:radar-2 -n radar_tactico

   # Descargar logo oficial de Simple Icons
   uv run python core/pipeline.py assets icon simple-icons:wireshark
   ```
   Además, el componente `icon_spotlight` resuelve y descarga automáticamente en `assets/icons/` cualquier especificación con prefijo `coleccion:nombre` declarada en `storyboard.json`.

2. **Mapas Geográficos Reales desde Natural Earth GeoJSON (Dominio Público CC0, sin API Key):**
   Proyecta las fronteras reales de cualquier país o región al sistema `viewBox="0 0 880 680"` de `radar_map` con los tokens CSS del sistema:
   ```bash
   uv run python core/pipeline.py assets map PRK -c KOR,JPN -n korea_real
   uv run python core/pipeline.py assets map "USA,CAN,MEX" -n north_america
   ```

3. **SFX y Música CC0 (URL Directa o Freesound API v2 con filtro CC0):**
   Descarga cualquier muestra CC0 y la convierte automáticamente con FFmpeg a `WAV PCM 48,000 Hz 16-bit` estéreo con limitador de picos (`alimiter=limit=0.92`):
   ```bash
   # Desde URL directa CC0
   uv run python core/pipeline.py assets audio mech_key --url https://ejemplo.org/key_cc0.ogg --type sfx

   # Desde Freesound API v2 (requiere FREESOUND_API_KEY en entorno; filtra estrictamente licencia CC0)
   uv run python core/pipeline.py assets audio shutter_org --freesound "camera shutter mechanical" --type sfx
   ```

4. **Modelos 3D Abiertos glTF/GLB (`assets/models/`) — Flujo Oficial con Blender:**
   Valida la cabecera glTF 2.0 (bytes mágicos `glTF` en `.glb` o JSON `asset` en `.gltf`) y guarda modelos 3D en `assets/models/` para ser consumidos de forma 100% offline por el componente `scene_3d` mediante `GLTFLoader` (copiados automáticamente al proyecto junto con el runtime ESM local de Three.js):
   ```bash
   # Generar los 6 modelos 3D universales semilla (.glb) con Blender headless:
   # shield_3d.glb, gear_3d.glb, crown_3d.glb, open_book_3d.glb, lock_3d.glb, globe_3d.glb
   uv run python core/pipeline.py assets seed-models

   # Compilar un modelo 3D propio ejecutando un script Python (bpy) en Blender headless
   uv run python core/pipeline.py assets model mi_escultura --blender-script ./crear_malla.py

   # Convertir/normalizar cualquier archivo .blend, .obj, .fbx o .stl a .glb con simplificación opcional
   uv run python core/pipeline.py assets model cordero --file ./export_blender/cordero.blend --decimate 0.5

   # Descargar modelo abierto desde URL directa CC0
   uv run python core/pipeline.py assets model olive_branch --url https://ejemplo.org/olive_branch.glb
   ```
   **Estándar de exportación desde Blender hacia `video-pipeline`:**
   * **Formato:** `glTF Binary (.glb)` (un solo archivo autocontenido sin texturas externas sueltas).
   * **Orientación y Escala:** Activar `+Y Up` y aplicar transformaciones previas (`Ctrl+A` $\rightarrow$ *All Transforms*). `scene_3d` normaliza y centra automáticamente el *bounding box* (`Box3`) del modelo en cámara.
   * **Topología para modos `edges` y `wireframe`:** Mantener mallas limpias (bajo/medio poligonaje, sin subdivisión excesiva) para que `EdgesGeometry` dibuje contornos nítidos en GPU.
   * **Materiales:** Para `render_style: "edges"` o `"wireframe"`, no se requieren texturas pesadas; el color se gobierna dinámicamente desde el token CSS del tema activo (`--accent-primary` o `props.color`). Para `render_style: "solid"`, el material estándar recibe iluminación direccional y ambiental de Three.js.

5. **Inventario Local de Assets:**
   ```bash
   uv run python core/pipeline.py assets list
   ```

---

## 3.6. Herramientas de Procesamiento de Imágenes y Recortes Transparentes (`core/image_tools.py` / `pipeline.py image`)

El módulo [`core/image_tools.py`](../../core/image_tools.py) (integrado como subcomando `pipeline.py image`) procesa imágenes estáticas, capturas y fotografías de manera 100% local hacia `assets/images/` para utilizarlas en el componente narrativo `image_cutout` o en plantillas HTML:

1. **Eliminación de Fondo (`rembg`) — IA Local ONNX (`isnet-general-use.onnx`, 1024x1024) o Extracción Cromática (`color`):**
   * `--method ai` *(Defecto)*: Ejecuta el modelo de estudio **DIS IS-Net (`isnet-general-use.onnx`, `1024x1024`)** sobre `onnxruntime` en local (descarga y cachea el modelo una sola vez en `.cache/models/isnet-general-use.onnx`), garantizando nitidez en bordes finos, cabello, hardware y capturas de alta definición 1080p.
   * `--method color`: Extracción cromática determinista con suavizado de bordes (`--feather`), detectando automáticamente el color de fondo en las 4 esquinas o usando `--color "#ffffff"`, ideal para logos planos, diagramas o capturas con fondo sólido.
   * **Acabado de estudio (Sticker / Cutout):** Soporta `--trim` (ajuste automático al sujeto), `--outline <px>` (borde perimetral uniforme mediante dilatación morfológica) y `--shadow <px>` (sombra paralela difuminada).
   ```bash
   # Quitar fondo con IA de estudio (IS-Net 1024x1024 por defecto), recortar márgenes y añadir borde + sombra
   uv run python core/pipeline.py image rembg -i foto.jpg -o assets/images/sujeto.png --trim --outline 6 --shadow 10

   # Quitar fondo sólido de un logo o captura y generar sticker limpio
   uv run python core/pipeline.py image rembg -i logo.png -o assets/images/logo_cutout.png -m color --trim --outline 4
   ```

2. **Recorte Inteligente y Encuadre (`crop`):**
   * Recorte por coordenadas exactas (`--box x,y,w,h`), por relación de aspecto centrada (`--aspect 9:16 | 16:9 | 1:1 | 4:5 | 4:3`) o recorte automático de bordes vacíos/sólidos (`--trim`).
   ```bash
   uv run python core/pipeline.py image crop -i captura.png -o assets/images/captura_9_16.webp --aspect 9:16 --width 1080 --height 1920
   ```

3. **Conversión de Formatos y Redimensionado Lanczos (`convert`):**
   * Convierte entre `PNG`, `WEBP`, `JPG` e `ICO` con modos `cover`, `contain` o `stretch`.
   ```bash
   uv run python core/pipeline.py image convert -i raw.png -o assets/images/optimizada.webp --width 840 --quality 92
   ```

---

## 4. Enlaces Relacionados

* Volver al índice general de la documentación en [00-indice-general.md](../00-indice-general.md).
* Consultar la guía rápida en el [README.md de la raíz](../../README.md).
