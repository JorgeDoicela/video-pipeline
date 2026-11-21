# Indice General de Documentacion Tecnica — Video Pipeline

Este documento constituye el catalogo maestro de la biblioteca documental Docs-as-Code para el entorno local de produccion de video programatico gobernado por agentes de inteligencia artificial.

---

## 1. Mapeo de Modulos Tecnicos

La documentacion esta estructurada bajo taxonomia jerarquica numerica para garantizar un orden de lectura logico, modular y desacoplado:

| Modulo | Ruta | Descripcion Tecnica |
| :--- | :--- | :--- |
| **01** | [01-arquitectura/01-arquitectura-sistema.md](./01-arquitectura/01-arquitectura-sistema.md) | Vision general del sistema, principio de separacion en 3 capas (Debian, Nix, Workspace), modelo de coste cero y diagrama de flujo end-to-end. |
| **02** | [02-nucleo-y-cli/01-nucleo-procesamiento.md](./02-nucleo-y-cli/01-nucleo-procesamiento.md) | Especificacion tecnica del nucleo: transcripcion palabra por palabra (`faster-whisper`), corte de silencios (`FFmpeg`), motor de temas visuales y Design Tokens (`styles.py`), motor multi-escena (`scenes.py`), mezclador de SFX (`audio_mix.py`), scaffolding de plantillas (`create_project.py`), motor de subtitulos cineticos (`sync_captions.py`) y orquestador maestro end-to-end (`pipeline.py`). |
| **03** | [03-renderizado-y-formatos/01-motor-renderizado-hyperframes.md](./03-renderizado-y-formatos/01-motor-renderizado-hyperframes.md) | Especificacion del motor de composicion visual: arquitectura web sin empaquetadores (HTML5/GSAP), gestion temporal en segundos y renderizado headless con aceleracion GPU AMD. |
| **03.2** | [03-renderizado-y-formatos/02-formatos-de-video.md](./03-renderizado-y-formatos/02-formatos-de-video.md) | Definicion de contratos de diseño y catalogo completo de las 7 plantillas esenciales de video (9:16 y 16:9), incluyendo `explainer_scenes_9_16` y `explainer_scenes_16_9` con sus 25 componentes narrativos. |
| **04** | [04-sistema-de-diseno/01-sistema-de-diseno-y-estilos.md](./04-sistema-de-diseno/01-sistema-de-diseno-y-estilos.md) | Especificacion exhaustiva de la arquitectura de diseño componible en 3 niveles: 3 Diseños Macro (`--design`), 3 Temas WCAG AA (`--style`), 3 Layouts, 3 Perfiles Motion, subtítulos `minimal_clean` y Overrides (`--set`). |
| **04.2** | [04-sistema-de-diseno/02-recursos-y-assets.md](./04-sistema-de-diseno/02-recursos-y-assets.md) | Especificacion de 15 efectos de sonido WAV (`assets/audio/`), 3 bases musicales loopables (`assets/music/`), 5 mapas geográficos SVG (`assets/maps/`), 18 iconos técnicos vectoriales SVG (`assets/icons/`), recortes de imágenes (`assets/images/` con `core/image_tools.py`) y tipografias locales (`assets/fonts/`). |
| **05** | [05-operacion-y-flujos/01-guia-operativa-y-flujos.md](./05-operacion-y-flujos/01-guia-operativa-y-flujos.md) | Runbooks paso a paso: captura de medios, ejecucion de scripts de linea de comandos, conmutacion de diseños en 3 niveles, integracion con agentes LLM y compilacion determinista a MP4. |

---

## 2. Punteros de Retorno y Navegacion

* Para volver a la guia rapida de instalacion y uso basico del proyecto, consulta el [README.md de la raiz](../README.md).
