# Directorio de Recursos Estáticos (Assets)

Este directorio almacena activos estáticos reutilizables para las composiciones de HyperFrames y los scripts del pipeline de video.

---

## 1. Efectos de Sonido Locales (`assets/audio/`)

Todos los archivos son archivos WAV PCM estéreo a 48,000 Hz, 16 bits, sintetizados matemáticamente y 100% libres de derechos (CC0 / Dominio Público).

| Archivo | Duración | Uso Recomendado en GSAP |
| :--- | :--- | :--- |
| `whoosh.wav` | `0.38s` | Transiciones de cámara, entradas de paneles o swipes rápidos. |
| `pop.wav` | `0.09s` | Aparición de badges, tags, burbujas o elementos flotantes. |
| `click.wav` | `0.03s` | Clicks táctiles de botones, toggles o selección de pestañas. |
| `chime.wav` | `0.85s` | Conclusión de procesos, transacciones exitosas o métricas clave. |
| `beep.wav` | `0.08s` | Logs de terminal, llegada de paquetes de red o comandos CLI. |

### Integración en HyperFrames / GSAP
```html
<!-- En el HTML del proyecto (con data-start para renderizado determinista) -->
<audio id="sfx-pop" src="../../assets/audio/pop.wav" data-start="1.5" data-duration="0.09"></audio>
```

Para regenerar o ajustar los efectos de sonido:
```bash
python3 core/generate_sfx.py
```

---

## 2. Iconografía Técnica Vectorial (`assets/icons/`)

Iconos SVG monocromáticos con `viewBox="0 0 24 24"`, diseñados con `stroke="currentColor"` para adoptar dinámicamente el color del texto o acento CSS circundante.

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
