# Sistema de Diseño y Estilos Componibles en 3 Niveles

Este documento especifica la arquitectura del motor de sistemas de diseño y temas visuales implementado en [`core/styles.py`](../../core/styles.py). El motor permite alternar de manera no destructiva entre diseños estructuralmente distintos, configurar opciones internas de cada diseño y aplicar ajustes granulares por proyecto sin alterar el contenido HTML, los activos multimedia ni las marcas de tiempo de transcripción.

---

## 1. Arquitectura Jerárquica de 3 Niveles

El sistema desacopla la presentación visual del contenido semántico mediante tres niveles de composición ortogonales:

```mermaid
flowchart TD
    subgraph N1 ["Nivel 1: Diseños Macro (--design)"]
        D1["cinematic (Oscuro Premium)"]
        D2["editorial (Cálido / Pergamino)"]
        D3["clean (Claro Minimalista)"]
        D4["terminal (Brutalismo Técnico TUI)"]
    end

    subgraph N2 ["Nivel 2: Opciones Internas del Diseño"]
        S["Paleta Cromática (--style): 4 Temas WCAG AA"]
        L["Distribución (--layout): 3 Layouts"]
        C["Marco de Ventana (--chrome): 4 Variantes"]
        M["Coreografía GSAP (--motion): 3 Perfiles"]
        K["Subtítulos (--caption-style): 2 Estilos"]
    end

    subgraph N3 ["Nivel 3: Overrides Granulares (--set clave=valor)"]
        O1["Geometría: radius_lg, stage_gap, panel_padding"]
        O2["Bordes/Sombras: border_width, shadow"]
        O3["Tokens de Color: bg, surface, accent_primary, text_primary"]
    end

    N1 -->|"Define valores por defecto"| N2
    N2 -->|"Refina sub-dimensiones"| N3
    N3 -->|"Inyección idempotente"| HTML["projects/<slug>/index.html + package.json"]
```

### Principios de Ingeniería del Motor
1. **Conmutación No Destructiva:** Los bloques CSS y atributos de datos se inyectan dentro de delimitadores explícitos (`/* @theme:start */`, `/* @design-system:start */`, `/* @caption-style:start */`). El árbol DOM del usuario, los textos y las etiquetas `<video>` permanecen intactos.
2. **Persistencia Declarativa (`videoDesign`):** La configuración activa de los 3 niveles se almacena en el archivo `package.json` del proyecto. Esto permite modificar una sola dimensión en el futuro (por ejemplo, cambiar únicamente `--layout` o `--set`) conservando el Diseño Macro y las demás opciones elegidas previamente.
3. **Cumplimiento Estricto WCAG AA:** Todos los temas oscuros y claros calibran sus colores de texto primario, secundario, atenuado (`--text-muted`) y acentos para garantizar un ratio de contraste mínimo de `4.5:1` en texto normal y `3.0:1` en texto grande, verificable con `pnpm exec hyperframes check`.

---

## 2. Nivel 1: Catálogo de Diseños Macro (`--design` / `-d`)

| Identificador (`-d`) | Nombre Técnico | Geometría y Superficie | Tema Nativo | Chrome / Motion / Captions Nativo | Caso de Uso Principal |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `cinematic` *(Defecto)* | Cinematic (Oscuro Premium) | Curvas amplias (`28px`), desenfoque suave (`blur(24px)`), sombra ambiental y bordes simétricos limpios. | `dark_violet` | `hidden` / `smooth` / `minimal_clean` | Videos verticales TikTok/Reels, tecnología, reflexiones de alto impacto y presentador. |
| `editorial` | Editorial (Cálido / Pergamino) | Estética clásica de lectura con esquinas sobrias (`4px`), bordes sólidos (`2px`), tipografía limpia sin filetes y cero desenfoque. | `paper_warm` | `hidden` / `minimal` / `minimal_clean` | Versículos bíblicos, citas, historia, filosofía y ensayos reflexivos. |
| `clean` | Clean (Claro Minimalista) | Canvas blanco neutro con tarjetas elevadas (`24px`), sombras suaves multicapa y bordes sutiles. | `clean_light` | `hidden` / `smooth` / `minimal_clean` | Explicaciones corporativas, tutoriales claros y presentaciones limpias. |
| `terminal` | Terminal (Brutalismo Técnico TUI) | Esquinas a 90 grados (`0px`), bordes sólidos de `2px` en color de acento y sombra dura desplazada (`8px 8px 0px`). | `terminal_green` | `terminal_bar` / `snappy` / `minimal_clean` | Linux, DevOps, ciberseguridad, CLI y tutoriales de consola. |

---

## 3. Nivel 2: Opciones Internas dentro de un Diseño

### 3.1. Temas Cromáticos (`--style` / `-s`)

| Identificador (`-s`) | Nombre | Fondo Principal (`--bg`) | Acento Primario (`--accent-primary`) | Acento Secundario (`--accent-secondary`) | Naturaleza Cromática |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `dark_violet` *(Defecto)* | Dark Violet (Obsidiana y Cristal) | `#09090b` | `#a78bfa` (Violeta) | `#34d399` (Esmeralda) | Oscuro atmosférico de alto contraste |
| `paper_warm` | Paper Warm (Pergamino Cálido) | `#fdf6e3` | `#0369a1` (Cobalto) | `#047857` (Esmeralda) | Claro cálido antirreflejo para lectura |
| `clean_light` | Clean Light (Blanco Neutro) | `#f8fafc` | `#0369a1` (Azul) | `#047857` (Verde) | Claro limpio calibrado WCAG AA |
| `terminal_green` | Terminal Green (Consola CRT) | `#050a06` | `#22c55e` (Verde CRT) | `#f59e0b` (Ámbar) | Oscuro monocromático de consola |

### 3.2. Variantes de Distribución (`--layout`)

| Identificador (`--layout`) | Descripción Estructural |
| :--- | :--- |
| `standard` *(Defecto)* | Distribución equilibrada: columnas simétricas `1fr 1fr` en `split-stage`, tarjeta lower-third alineada a la izquierda (`left: 80px`). |
| `asymmetric_focus` | Foco asimétrico: columna principal `1.35fr` y secundaria `0.85fr`; tarjeta lower-third alineada a la derecha (`right: 80px`). |
| `stacked` | Disposición vertical apilada (`grid-template-columns: 1fr`) y cabecera centrada. |

### 3.3. Variantes de Marco de Ventana (`--chrome`)

| Identificador (`--chrome`) | Descripción Visual |
| :--- | :--- |
| `auto` *(Defecto)* | Adopta automáticamente el marco nativo del Diseño Macro seleccionado en el Nivel 1. |
| `hidden` | Oculta por completo la barra superior (`.window-header`, `.win-bar`, `.code-header`) para tarjetas limpias. |
| `minimal_line` | Oculta los botones circulares y deja únicamente una línea divisoria limpia con el título del bloque. |
| `terminal_bar` | Controles cuadrados angulares tipo terminal técnica con borde inferior marcado. |

### 3.4. Perfiles de Coreografía GSAP (`--motion`)

| Identificador (`--motion`) | Curva de Entrada (`ease`) | Duración Base | Comportamiento Visual |
| :--- | :--- | :--- | :--- |
| `smooth` *(Defecto)* | `power2.out` / `power3.out` | `0.95s` | Desaceleración progresiva y fluida de estilo editorial/cinematográfico. |
| `snappy` | `power4.out` / `back.out(2.0)` | `0.45s` | Transición rápida y enérgica ideal para Shorts, Reels y estilo terminal. |
| `minimal` | `power1.out` | `0.35s` | Aparición sobria y discreta para lectura tranquila. |

### 3.5. Estilos de Subtítulos Cinéticos (`--caption-style`)

| Identificador (`--caption-style`) | Efecto sobre la Palabra Activa (`.word.active`) | Opacidad Inactiva |
| :--- | :--- | :--- |
| `minimal_clean` *(Estándar Único)* | Lectura limpia sobria sin cajas ni cápsulas; resalta mediante opacidad `1.0`, color de acento y sombra sutil. | `0.40` |

---

## 4. Nivel 3: Overrides Granulares por Proyecto (`--set clave=valor`)

El Nivel 3 permite ajustar tokens geométricos o cromáticos específicos en un único proyecto sin modificar el catálogo global ni perder la capacidad de cambiar de Diseño Macro posteriormente.

| Categoría | Propiedad (`--set`) | Variable CSS / Efecto Destino | Ejemplo de Uso |
| :--- | :--- | :--- | :--- |
| **Geometría** | `radius_lg`, `radius_md`, `radius_sm`, `border_width` | `--radius-lg`, `--radius-md`, `--radius-sm`, `--border-width` | `--set radius_lg=0px` |
| **Espaciado / Layout** | `stage_padding`, `stage_gap`, `split_columns`, `header_align`, `lower_third_side` | `--stage-padding`, `--stage-gap`, `--split-columns`, posición lower-third | `--set stage_gap=56px` |
| **Subtítulos** | `caption_bottom`, `caption_size`, `caption_bg`, `caption_text`, `caption_active` | Variables de subtítulos en `:root` | `--set caption_size=48px` |
| **Tipografía y Color** | `font_sans`, `font_mono`, `bg`, `surface`, `accent_primary`, `text_primary`, etc. | Tokens semánticos en `:root` | `--set accent_primary=#f43f5e` |

---

## 5. Ejemplos Prácticos de Composición y Conmutación

```bash
# Consultar el catálogo completo o en JSON
python3 core/pipeline.py style --list
python3 core/pipeline.py style --list --json

# Cambiar a Diseño Macro editorial (cálido pergamino) o terminal
python3 core/pipeline.py style mi-proyecto -d editorial
python3 core/pipeline.py style mi-proyecto -d terminal

# Combinar diseño editorial con paleta limpia y foco asimétrico
python3 core/pipeline.py style mi-proyecto -d editorial -s clean_light --layout asymmetric_focus

# Ajustar un token puntual e inspeccionar estado
python3 core/pipeline.py style mi-proyecto --set accent_primary=#ff5500 --set stage_gap=60px
python3 core/pipeline.py style mi-proyecto --inspect
python3 core/pipeline.py style mi-proyecto --reset-overrides
```

---

## 6. Enlaces Relacionados

* Ver el catálogo de las 7 plantillas esenciales en [02-formatos-de-video.md](../03-renderizado-y-formatos/02-formatos-de-video.md).
* Consultar los flujos de trabajo paso a paso en [01-guia-operativa-y-flujos.md](../05-operacion-y-flujos/01-guia-operativa-y-flujos.md).
* Volver al índice maestro en [00-indice-general.md](../00-indice-general.md).
