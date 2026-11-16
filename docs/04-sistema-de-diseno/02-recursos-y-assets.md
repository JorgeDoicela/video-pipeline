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
| `beep.wav` | `0.08s` | Logs de terminal, llegada de paquetes de red o comandos CLI. |
| `sub_hit.wav` | `0.55s` | Impacto sub-grave para apertura de escena, títulos hook o revelaciones. |
| `glitch.wav` | `0.16s` | Alertas críticas, errores de terminal o cambios bruscos de estado. |

### Integración en HyperFrames / Mezcla FFmpeg (`core/audio_mix.py`)
Además de la vinculación directa como `<audio>` por evento, [`core/audio_mix.py`](../../core/audio_mix.py) invoca `ensure_sfx_assets()` y mezcla la pista de voz con todos los eventos SFX del storyboard en un único archivo maestro `audio_mix.wav` mediante `adelay`, `amix` y limitación de picos `alimiter=limit=0.95`.

```html
<!-- Pista maestra compilada por core/audio_mix.py -->
<audio id="master-audio" src="audio_mix.wav" data-start="0" data-duration="12.00" data-track-index="0" data-volume="1"></audio>
```

Para regenerar o ajustar los efectos de sonido:
```bash
python3 core/generate_sfx.py
```

---

## 2. Iconografía Técnica Vectorial (`assets/icons/`)

Iconos SVG monocromáticos con `viewBox="0 0 24 24"`, diseñados con `stroke="currentColor"` mediante [`core/generate_icons.py`](../../core/generate_icons.py) para adoptar dinámicamente el color del texto o acento CSS circundante.

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

### Uso en HTML
```html
<!-- Carga directa como imagen vectorial -->
<img src="../../assets/icons/docker.svg" width="32" height="32" style="filter: drop-shadow(0 0 8px #38bdf8);" alt="Docker" />
```

Para regenerar los iconos vectoriales:
```bash
python3 core/generate_icons.py
```

---

## 3. Tipografías (`assets/fonts/`)

Directorio destinado a fuentes tipográficas locales en formato WOFF2 o TTF cuando se requiera operar de forma totalmente aislada de la red. Por defecto, HyperFrames cachea Google Fonts localmente en `~/.cache/hyperframes/fonts/`.

---

## 4. Enlaces Relacionados

* Volver al índice general de la documentación en [00-indice-general.md](../00-indice-general.md).
* Consultar la guía rápida en el [README.md de la raíz](../../README.md).
