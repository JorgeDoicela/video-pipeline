# Indice General de Documentacion Tecnica — Video Pipeline

Este documento constituye el catalogo maestro de la biblioteca documental Docs-as-Code para el entorno local de produccion de video programatico gobernado por agentes de inteligencia artificial.

---

## 1. Mapeo de Modulos Tecnicos

La documentacion esta estructurada bajo taxonomia jerarquica numerica para garantizar un orden de lectura logico, modular y desacoplado:

| Modulo | Archivo | Descripcion Tecnica |
| :--- | :--- | :--- |
| **01** | [01-arquitectura-sistema.md](./01-arquitectura-sistema.md) | Vision general del sistema, principio de separacion en 3 capas (Debian, Nix, Workspace), modelo de coste cero y diagrama de flujo end-to-end. |
| **02** | [02-nucleo-procesamiento.md](./02-nucleo-procesamiento.md) | Especificacion tecnica del motor de ingesta y audio: transcripcion con marcas temporales palabra por palabra (`faster-whisper`) y algoritmo de corte de silencios con `FFmpeg`. |
| **03** | [03-motor-renderizado-hyperframes.md](./03-motor-renderizado-hyperframes.md) | Especificacion del motor de composicion visual: arquitectura web sin empaquetadores (HTML5/GSAP), gestion temporal en segundos y renderizado headless con aceleracion GPU AMD. |
| **04** | [04-formatos-de-video.md](./04-formatos-de-video.md) | Definicion de contratos de diseño para Formato 1 (Talking Head / grabacion de pantalla con overlays) y Formato 2 (Explicador tecnico abstracto con diagramas SVG y bloques de codigo). |
| **05** | [05-guia-operativa-y-flujos.md](./05-guia-operativa-y-flujos.md) | Runbooks paso a paso: captura de medios, ejecucion de scripts de linea de comandos, integracion con agentes LLM y compilacion determinista a MP4. |

---

## 2. Punteros de Retorno y Navegacion

* Para volver a la guia rapida de instalacion y uso basico del proyecto, consulta el [README.md de la raiz](../README.md).
