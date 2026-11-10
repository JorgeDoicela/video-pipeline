# Indice General de Documentacion Tecnica — Video Pipeline

Este documento constituye el catalogo maestro de la biblioteca documental Docs-as-Code para el entorno local de produccion de video programatico gobernado por agentes de inteligencia artificial.

---

## 1. Mapeo de Modulos Tecnicos

La documentacion esta estructurada bajo taxonomia jerarquica numerica para garantizar un orden de lectura logico, modular y desacoplado:

| Modulo | Archivo | Descripcion Tecnica |
| :--- | :--- | :--- |
| **01** | [01-arquitectura-sistema.md](./01-arquitectura-sistema.md) | Vision general del sistema, principio de separacion en 3 capas (Debian, Nix, Workspace), modelo de coste cero y diagrama de flujo end-to-end. |
| **02** | [02-nucleo-procesamiento.md](./02-nucleo-procesamiento.md) | Especificacion tecnica del nucleo: transcripcion palabra por palabra (`faster-whisper`), corte de silencios (`FFmpeg`), motor de temas visuales y Design Tokens (`styles.py`), scaffolding de plantillas (`create_project.py`), motor de subtitulos cineticos (`sync_captions.py`) y orquestador maestro end-to-end (`pipeline.py`). |
| **03** | [03-motor-renderizado-hyperframes.md](./03-motor-renderizado-hyperframes.md) | Especificacion del motor de composicion visual: arquitectura web sin empaquetadores (HTML5/GSAP), gestion temporal en segundos y renderizado headless con aceleracion GPU AMD. |
| **04** | [04-formatos-de-video.md](./04-formatos-de-video.md) | Definicion de contratos de diseño y catalogo completo de las 9 plantillas de video: Talking Head (16:9 y 9:16), Explicador Tecnico SVG, Walkthrough de Codigo IDE, Benchmark de Rendimiento y formatos sociales (16:9, 9:16, 1:1 y 4:5). |
| **05** | [05-guia-operativa-y-flujos.md](./05-guia-operativa-y-flujos.md) | Runbooks paso a paso: captura de medios, ejecucion de scripts de linea de comandos, conmutacion de diseños en 3 niveles, integracion con agentes LLM y compilacion determinista a MP4. |
| **06** | [06-sistema-de-diseno-y-estilos.md](./06-sistema-de-diseno-y-estilos.md) | Especificacion exhaustiva de la arquitectura de diseño componible en 3 niveles: 6 Diseños Macro (`--design`), 8 Temas WCAG AA (`--style`), Layouts, Chrome, Motion, 6 Estilos de Subtitulos y Overrides (`--set`). |

---

## 2. Punteros de Retorno y Navegacion

* Para volver a la guia rapida de instalacion y uso basico del proyecto, consulta el [README.md de la raiz](../README.md).
