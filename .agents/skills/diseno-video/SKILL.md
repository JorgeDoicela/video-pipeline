---
name: diseno-video
description: Activa esta skill para la creación, ajuste, estilización o auditoría visual de videos, composiciones HTML, subtítulos cinéticos, badges, tarjetas y motion graphics en el video-pipeline. Aplica de forma estricta los estándares estéticos limpios de Jorge (cero pastillas en palabras de subtítulos, cero cápsulas en badges e iconos SVG, cero franjas laterales asimétricas a la izquierda, cero líneas horizontales en títulos o subtítulos) y el contrato de renderizado determinista de HyperFrames.
---

# Skill de Diseño Visual y Composición de Video — video-pipeline

Esta skill establece las directrices maestras de diseño gráfico, tipografía, composición CSS y animación determinista para la producción de video programático en este repositorio. Su objetivo es garantizar una estética técnica limpia, sobria, sin ruido visual y 100% fiel a los estándares de producción de Jorge.

---

## 1. Restricciones Visuales Absolutas de Jorge (Innegociables)

Queda terminantemente prohibido implementar o reintroducir cualquiera de los siguientes patrones gráficos:

| Elemento Gráfico | Patrón Prohibido (Rechazado) | Estándar Obligatorio (Limpio) |
|---|---|---|
| **Subtítulos cinéticos** | Encerrar palabras activas en cápsulas o pastillas con fondo sólido/translúcido, bordes y padding (`background`, `border`, `padding`, `border-radius` en `.word.active`), o permitir que dos bloques consecutivos (`.caption-phrase`) se solapen temporalmente causando saltos verticales. | Tipografía pura (`minimal_clean`) en bloques estáticos de 1 a 2 líneas balanceadas (`text-wrap: balance`, `max-width: 780px` en 9:16 y `1180px` en 16:9, `words_per_group: 6` por defecto) sin solapamiento temporal (`hide_time = min(g_end + 0.15, next_start)`). La palabra activa se ilumina exclusivamente con color de texto (`var(--caption-active)` o `var(--accent-secondary)` en `.word-emphasis`), opacidad completa (`1.0`) y `text-shadow: var(--caption-shadow)`. Cero cajas envolventes. |
| **Badges y Etiquetas** | Envolver texto de categoría (`.hook-badge`, `.badge`) en pastillas redondeadas con fondos o bordes. | Tipografía limpia sin contenedor: `background: transparent; border: none; padding: 0; display: inline-flex;` en mayúsculas, tracking amplio (`0.12em - 0.15em`) y peso 700-800. |
| **Iconografía SVG** | Rodear iconos vectoriales SVG con fondos redondeados, botones o cápsulas. | Iconos SVG limpios y desnudos, alineados visualmente con el texto tipográfico sin contenedores gráficos envolventes. |
| **Tarjetas y Paneles** | Bordes de acento asimétricos gruesos en el lateral izquierdo (`border-left: 6px solid var(--accent-primary)`) en `#main-card`, `.panel` o `.lower-third`. | Bordes perimetrales simétricos y uniformes en los cuatro lados (`border: var(--border-width) solid var(--border)`). |
| **Líneas en Títulos o Subtítulos** | Filetes horizontales, líneas decorativas, subrayados o bordes (`border-top`, `border-bottom`, `text-decoration: underline`, `<hr>`) en cabeceras (`header`), títulos (`h1`-`h6`) o subtítulos. | Tipografía limpia, abierta y sin barras o líneas delimitadoras arriba o abajo del texto. |

---

## 2. Catálogo de Diseño Autorizado (Matriz 3x3x3)

Toda composición debe ensamblarse utilizando los bloques canónicos del catálogo centralizado en `core/styles.py`:

### Nivel 1: Diseños Macro
* `cinematic`: Superficie oscura profunda con curvas amplias (`--radius-lg: 28px`), desenfoque backdrop suave y bordes simétricos limpios.
* `editorial`: Formato cálido y sereno de lectura, ensayo e historia bíblica (`--radius-lg: 20px`), fondo marfil antirreflejo (`#f5f1ea`), bordes simétricos finos (`1px`), titulares estilizados de ancho contenido (`font-size: 56px`/`54px`, `font-weight: 700`, `text-transform: none`, `max-width: 780px`/`1020px`, `text-wrap: balance`) y lienzo superior limpio (oculta automáticamente `#progress-bar` y `#brand-bar`).
* `clean`: Luminoso, minimalista, tarjetas blancas o traslúcidas puras con sombras multicapa y estética moderna.

### Nivel 2: Variantes Canónicas
* **Paletas de Color (Accesibles WCAG AA):**
  * `dark_violet`: Oscuro refinado con acento primario violeta (`#a78bfa`) y secundario esmeralda (`#34d399`).
  * `paper_warm`: Pergamino marfil cálido (`#f5f1ea`) con tinta café carbón (`#2b231d`), acento primario latón dorado (`#875c22`) y acento secundario carmesí terracota (`#8c2d19`).
  * `clean_light`: Base blanca/gris perla (`#f8fafc`) con texto negro azulado y acento azul (`#0369a1`).
* **Layouts Estructurales:**
  * `standard`: Centrado armónico para explicación técnica directa.
  * `asymmetric_focus`: Columna gráfica dominante con panel de apoyo.
  * `stacked`: Disposición vertical apilada para pantallas densas.
* **Perfiles de Movimiento (GSAP):**
  * `smooth`: Curvas suaves `power2.out` / `power3.out` para tono documental y editorial.
  * `snappy`: Transiciones enérgicas `power4.out` / `back.out(2.0)` para Shorts y Reels.
  * `minimal`: Aparición sobria `power1.out` con mínima traslación para lectura tranquila.
* **Estilo de Subtítulos:**
  * `minimal_clean`: Estándar único oficial sin cápsulas ni artefactos de caja.

---

## 3. Contrato de Renderizado Determinista HyperFrames

Cualquier template o proyecto HTML debe acatar rigurosamente las reglas del motor HyperFrames:

1. **Raíz del Lienzo:**
   * El contenedor raíz debe poseer: `data-composition-id="main"`, `data-start="0"`, `data-duration="<segundos>"`, `data-width="<ancho>"` y `data-height="<alto>"`.
   * Prohibido ubicar elementos hermanos gráficos fuera de `#root` dentro del `<body>`.
2. **Animaciones con GSAP:**
   * La línea de tiempo maestra debe crearse pausada:
     ```javascript
     const tl = gsap.timeline({ paused: true });
     window.__timelines["main"] = tl;
     tl.seek(0);
     ```
   * **Prohibición Total de Transiciones CSS:** Nunca emplear `transition:` en CSS. Las transiciones CSS dependen del reloj de pared del navegador y rompen el paralelismo determinista de HyperFrames. Toda animación de propiedades debe orquestarse en la línea de tiempo de GSAP.
3. **Contraste y Legibilidad (WCAG AA):**
   * Ratio de contraste mínimo de 4.5:1 para texto normal y 3:1 para texto grande.
   * Texto legible con tamaño mínimo de 28px en composiciones 1080p, o etiquetado con `data-layout-ignore` si es meramente decorativo.
4. **Reglas de Precisión Geométrica en SVG + GSAP:**
   * Al rotar o escalar elementos `<g>`, `<path>` o `<circle>` dentro de un `<svg viewBox="...">` en GSAP, utiliza siempre coordenadas absolutas dentro del `viewBox` y define explícitamente `svgOrigin: "<cx> <cy>"` en el tween (nunca dependas de `transform="translate(cx, cy)"` en el atributo SVG si GSAP va a animar `rotation` o `scale`, ya que GSAP sobrescribe la matriz de transformación).
   * Cuando utilices `yoyo: true, repeat: 1` en una animación secundaria, **no incluyas `opacity: 0`** en el `fromVars` de ese mismo `fromTo`, pues al hacer *yoyo* el elemento volverá a `opacity: 0`. Separa la entrada de opacidad en un tween previo o anima únicamente posición/escala en el ciclo `yoyo`.
5. **Reglas de Renderizado 3D Determinista (`Three.js` + Blender `.glb`) y Cámara 2D / Trazos SVG:**
   * En `scene_3d`, nunca utilices `requestAnimationFrame`. Todo render WebGL (`renderer.render(scene, camera)`) debe invocarse dentro del `onUpdate` de un tween sobre `window.__timelines["main"]`, inicializando `THREE.WebGLRenderer` con `preserveDrawingBuffer: true`.
   * Los modelos orgánicos creados en **Blender** deben exportarse como `glTF Binary (.glb)` (`+Y Up`, transformaciones aplicadas), registrarse en `assets/models/` mediante `uv run python core/pipeline.py assets model <slug> --file <ruta.glb>` y consumirse con `"component": "scene_3d"`.
   * Para recorridos conceptuales sin cortes bruscos utiliza `infinite_canvas` (cámara 2D `x`, `y`, `scale` + conectores Bezier + `zoom_out_end`), y para diagramas que se dibujan mientras habla el narrador utiliza `svg_draw` (`stroke-dashoffset` + `MotionPathPlugin`).

---

## 4. Arquitectura Multi-Escena Faceless (`core/scenes.py` y `core/audio_mix.py`)

Para videos explicativos donde solo habla la voz del narrador (`explainer_scenes_9_16` y `explainer_scenes_16_9`), el diseño visual y sonoro se gobierna mediante `storyboard.json`:

### 4.1. Opciones de Nivel Raíz en `storyboard.json`
* `caption_position`:
  * `"hero_top"` (recomendado para Shorts/Reels/TikTok de alto impacto): coloca los subtítulos cinéticos palabra por palabra en el tercio superior a `68px` en mayúsculas con `text-shadow` luminoso, dejando libre el escenario central para la animación (las escenas pueden llevar `"headline": ""` para no duplicar texto arriba).
  * `"bottom"`: coloca los subtítulos en la zona inferior segura cuando cada escena muestra su propio `badge` + `headline` en la parte superior.
* `brand` y `category`: firma tipográfica superior opcional (ej. `"brand": "jorge.dev"`, `"category": "CIBERSEGURIDAD"`), renderizada sin cápsulas ni bordes.
* `atmosphere`: atmósfera base (`"sunburst"`, `"grid"`, `"clean"`), que además puede conmutarse dinámicamente escena por escena.
* `ambient_bed`: `true` activa la cama sintética grave loopable (`drone.wav`) mezclada con *ducking* dinámico (`sidechaincompress`) bajo la voz.
* `music`: preset musical procedural local (`"tension_pulse"`, `"tech_minimal"`, `"editorial_warm"`) o ruta a archivo `.wav`/`.mp3`, mezclado automáticamente con *ducking*.
* `camera_motion`: `true` (defecto) aplica un movimiento de cámara virtual lento y determinista (`scale: 1.0 -> 1.028`) sobre `#scenes-stage` sin mover los subtítulos.
* `film_grain`: `true` activa viñeta radial profunda y textura cinematográfica determinista (`data-film-grain="true"`).
* `voice_polish`: `true` aplica limpieza vocal de estudio en FFmpeg (`highpass=f=80`, `afftdn=nf=-25`, `acompressor` y `loudnorm=-14 LUFS`) antes del *ducking* (también activable por CLI con `--voice-polish`).
* `words_per_group` y `emphasis_words`: configuran el número máximo de palabras por bloque de subtítulo (`6` por defecto para formar 1 a 2 líneas balanceadas con `text-wrap: balance`, respetando además cortes en puntuación fuerte y comas sin solapamiento temporal entre bloques consecutivos) y las palabras clave que se iluminan con `.word-emphasis` (color secundario `var(--accent-secondary)` + `var(--caption-shadow)`, cero cajas o pastillas).

### 4.2. Catálogo de 30 Componentes Narrativos (`COMPONENT_REGISTRY`)
1. `phone_mockup`: soporta `mode: "list"` (carpetas con retícula de enfoque y cursor animado opcional `show_cursor: true`) y `mode: "app_grid"` (pantalla móvil con reloj gigante, cuadrícula `4x4` de apps, etiqueta superior, arco HUD radial y flash de obturador opcional `capture_flash: true`, `capture_count: 5`).
2. `radar_map`: mapa vectorial y radar táctico con barrido cónico 360° (`svgOrigin: "440 340"`), presets geográficos reales en `assets/maps/` (`map_preset: "korea" | "world" | "europe" | "americas" | "asia"`), ruta animada opcional (`route: true`) y objetivos geolocalizados (`targets`).
3. `xray_scanner`: marco HUD con 4 esquinas, láser horizontal en vivo y tarjetas laterales (`callouts`).
4. `padlock_denied`: candado vectorial encadenado con sello `ACCESO DENEGADO` (`stamp`, `detail`).
5. `keyboard_type`: teclado QWERTY interactivo con teclas activas resaltadas (`active_keys`), caja de texto (`typed_text`) y barra de sugerencias (`suggestions`).
6. `system_alert`: modal de advertencia del sistema con revelado tipo máquina de escribir (`typewriter`) y cursor en GSAP.
7. `hex_inspector`: volcado de memoria hexadecimal con fila activa resaltada, puntero inline (`tag`) y tarjeta de hallazgo (`finding`).
8. `desktop_monitor`: monitor panorámico de sistema operativo con iconos de escritorio, barra de tareas y emblema central.
9. `file_cards`: tarjetas de archivos (`FOTO.JPG`, `VIDEO.AVI`, `DOC.DOCX`) marcadas con código de serie (`serial_code`) y huella.
10. `network_graph`: grafo de nodos y aristas con trazado progresivo de rutas de alerta.
11. `terminal_grid`: matriz de 6 consolas en paralelo con LEDs de estado y vibración de alerta.
12. `connector_flow`: animación de conexión física/lógica entre puerto host y dispositivo externo.
13. `stat_callout`: cifra protagonista (`value` / `primary_text`), subtítulo (`label` / `secondary_text`) y barras comparativas opcionales.
14. `timeline_steps`: pasos secuenciales numerados con ítem destacado.
15. `comparison_split`: comparativa simétrica en dos columnas (`left`, `right`).
16. `quote_focus`: cita, tesis o principio central con autor y contexto.
17. `bar_chart`: gráfico de barras horizontales proporcionales.
18. `code_spotlight`: bloque de código o CLI con numeración y línea activa resaltada.
19. `icon_spotlight`: icono vectorial desnudo de `assets/icons/` (o descargado automáticamente desde Iconify al especificar `"icon": "lucide:shield-alert"` o `"simple-icons:wireshark"`) dentro de anillo de progreso radial.
20. `toggle_alert`: monitor/panel de sistema con interruptor interactivo (`label`, `state_on`, `state_off`), alerta de integridad (`alert_title`, `alert_detail`) y apagón CRT determinista (`crt_reboot: true`).
21. `conveyor_factory`: línea de producción industrial con prensa estampadora, emblema central y dispositivos en cinta (`caption`, `device_tag`).
22. `cta_card`: cierre interactivo con botón de llamada a la acción (`cta_text`), marco móvil (`clock`) y mutación de candado seguro (`before_label`) a ojo/alerta (`after_label`).
23. `canvas_fx`: primitiva Canvas 2D 100% determinista conducida por proxy numérico en GSAP (`onUpdate`, cero `requestAnimationFrame`), con modos `effect: "particles" | "matrix" | "radar_waves" | "noise_field"`, `title`, `subtitle` y `color`.
24. `image_cutout`: presenta una imagen procesada o recorte transparente (`assets/images/<archivo>.png`/`.webp`) con entrada elástica, flotación determinista opcional (`float_motion: true`), `title` y `subtitle`.
25. `infinite_canvas`: cámara virtual 2D sobre un lienzo continuo (`world_width`, `world_height`) que conecta nodos mediante curvas Bezier SVG (`stroke-dashoffset` + `MotionPathPlugin`) y viaja entre ellos en GSAP (`x`, `y`, `scale`), con `zoom_out_end: true` para revelar el mapa completo al final.
26. `svg_draw`: trazos SVG vectoriales progresivos sincronizados con timestamps relativos (`at`, `duration`, `dashed`, `label`), etiquetas cronometradas (`labels`), tachado animado (`strike_through`) y punta luminosa (`writing_head: true`) conducida por `MotionPathPlugin`.
27. `scene_3d`: motor WebGL 3D 100% determinista sobre Three.js (`onUpdate` de GSAP, cero `requestAnimationFrame`, `preserveDrawingBuffer: true`) con 9 primitivos procedurales (`cross`, `altar`, `scales`, `gavel`, `bars`, `columns`, `cube`, `torus`, `sphere`), carga de modelos `.glb`/`.gltf` compilados con **Blender** (`assets/models/`, incluidos 6 modelos semilla: `shield_3d.glb`, `gear_3d.glb`, `crown_3d.glb`, `open_book_3d.glb`, `lock_3d.glb`, `globe_3d.glb`), modos `edges` | `wireframe` | `solid`, grilla de puntos 3D (`dot_grid`) y órbita de cámara (`camera_orbit`).
28. `video_clip`: componente híbrido para alternar o incrustar clips de video reales (presentador a cámara `cut.mp4`, screencast o B-roll en `assets/videos/`) dentro de un storyboard multi-escena con `layout_mode: "card" | "full" | "pip"`, cumpliendo el contrato `data-start` y `data-duration` de HyperFrames.
29. `manim_clip`: componente de primera clase para animaciones matemáticas, algorítmicas y geométricas renderizadas con **Manim Community** (`core/manim_tools.py`). Acepta un clip pre-renderizado (`src`) o un script (`script` relativo al proyecto, repo o `assets/manim/` + `scene_class` opcional) compilado automáticamente bajo demanda con el tema y overrides del proyecto (`package.json`), caché inteligente (invalida si cambia el `.py` o `package.json`), modos `card | full | pip` y soporte `transparent: true` (`.webm` con canal alfa).
30. `custom_scene`: **primitiva abierta de máxima flexibilidad** que recibe `html` (con marcador `{scene_id}`) y `gsap` (con `{scene_id}` y `{start}`) para construir metáforas visuales SVG/GSAP hechas a la medida exacta de cualquier frase del guion sin modificar `core/`.

### 4.2.1. Estándar Obligatorio para Escenas Manim (`core/manim_tools.py`)
Toda escena Manim creada para el pipeline debe seguir estas 3 reglas:
* **Paleta sincronizada:** Importar siempre `get_pipeline_palette`, `apply_pipeline_background` e `is_vertical_aspect` desde `core.manim_tools` para heredar exactamente `bg`, `surface`, `text_primary`, `accent_primary` y `accent_secondary` del tema activo (`dark_violet`, `paper_warm`, `clean_light`) y sus overrides `--set`.
* **Fondo seguro para transparencia:** Nunca asignar `self.camera.background_color = ...` directamente; usar siempre `apply_pipeline_background(self, p)` para no anular el canal alfa cuando se renderiza con `--transparent`.
* **Encuadre adaptativo `9:16`:** Consultar `is_vertical_aspect()` (`frame_width` útil `4.5` en `9:16` vs `14.22` en `16:9`) para reencuadrar ejes, escalas de texto y apilar bloques verticalmente (`arrange(DOWN)`) en Shorts/Reels.
* **Comandos CLI oficiales:**
  ```bash
  uv run python core/pipeline.py manim doctor
  uv run python core/pipeline.py manim new <slug> --preset math_proof|algorithm_flow|vector_field -s dark_violet
  uv run python core/pipeline.py manim render assets/manim/<slug>.py --aspect 16:9|9:16 --quality prod -s dark_violet [--transparent] [-p <proyecto>]
  ```

### 4.3. Sincronización por Voz (`cue_word`) y Cambio de Mood por Escena
* Cada escena puede declarar `"cue_word": "<palabra>"` para que `align_storyboard_to_transcript` ajuste su `start` al instante exacto en que Whisper detectó esa palabra.
* Cada escena puede declarar `"accent": "danger" | "warning" | "secondary" | "tertiary" | "primary"` y `"atmosphere": "sunburst" | "grid" | "clean"` para variar el color y el fondo entre escenas.

### 4.4. Gestor de Assets Abiertos y Procesador de Imágenes (`core/fetch_assets.py` y `core/image_tools.py`)
Para incorporar nuevos iconos vectoriales, mapas geográficos reales, muestras de audio CC0 o recortes de imágenes sin fondo (cutouts) directamente en `assets/`:
* **Iconos y logos SVG (Iconify — Lucide, Tabler, Simple Icons):**
  `uv run python core/pipeline.py assets icon simple-icons:wireshark`
* **Mapas geopolíticos reales (Natural Earth GeoJSON CC0 -> `assets/maps/<name>.svg`):**
  `uv run python core/pipeline.py assets map PRK -c KOR,JPN -n korea_real`
* **SFX y música CC0 normalizados a WAV 48kHz 16-bit (URL directa o Freesound API v2 CC0):**
  `uv run python core/pipeline.py assets audio shutter_org --freesound "camera shutter" --type sfx`
* **Eliminación de fondo (IA local ONNX IS-Net 1024x1024 de estudio o color), recorte y conversión de imágenes (`assets/images/`):**
  ```bash
  uv run python core/pipeline.py image rembg -i foto.jpg -o assets/images/sujeto.png --trim --outline 6 --shadow 10
  uv run python core/pipeline.py image crop -i captura.png -o assets/images/captura.webp --aspect 9:16 --width 1080 --height 1920
  uv run python core/pipeline.py image convert -i raw.png -o assets/images/opt.webp --width 840 --quality 92
  ```
* **Modelos 3D compilados o convertidos con Blender headless (`assets/models/*.glb`):**
  ```bash
  uv run python core/pipeline.py assets seed-models
  uv run python core/pipeline.py assets model mi_modelo --blender-script script_bpy.py
  uv run python core/pipeline.py assets model cordero --file ruta/al/cordero.blend --decimate 0.5
  ```
* **Inventario de assets locales:**
  `uv run python core/pipeline.py assets list`

---

## 5. Flujo de Trabajo y Comandos de Ejecución

Para producir, estilizar, validar y renderizar proyectos:

1. **Producir Video Multi-Escena Completo desde Voz (o usando Perfil de Canal):**
   ```bash
   # Explícito por flags
   uv run python core/pipeline.py produce \
     -i mi_voz.wav \
     -p mi-video \
     -t explainer_scenes_9_16 \
     -d cinematic \
     -s dark_violet \
     --storyboard guion.json \
     --replace lidis=Redis \
     --ambient-bed \
     --auto-render

   # Con perfil de canal/cliente (profiles/*.json), prefijo de fecha e historial en catalog.jsonl
   uv run python core/pipeline.py profiles list
   uv run python core/pipeline.py produce -i mi_voz.wav -p mi-video --profile tech_short --dated --auto-render
   uv run python core/pipeline.py history
   ```

2. **Aplicar o Cambiar Estilo (Sin Perder Escenas ni Subtítulos):**
   ```bash
   # Aplicar diseño macro y paleta
   uv run python core/pipeline.py style projects/<nombre_proyecto> -d editorial -s paper_warm

   # Ajustar layout o motion
   uv run python core/pipeline.py style projects/<nombre_proyecto> --layout standard --motion minimal
   ```

3. **Auditoría Automatizada HyperFrames (Obligatoria):**
   ```bash
   pnpm exec hyperframes check projects/<nombre_proyecto>
   ```
   No se permiten errores de contraste, overlap, layout ni recursos multimedia huérfanos.

4. **Verificación de la Suite de Pruebas y Linter:**
   ```bash
   uv run ruff check core tests
   uv run ruff format --check core tests
   uv run pytest tests
   ```

5. **Renderizado de Producción:**
   ```bash
   pnpm exec hyperframes render projects/<nombre_proyecto> -o projects/<nombre_proyecto>/video_<nombre_proyecto>.mp4
   ```

---

## 6. Lista de Verificación Pre-Entrega (Checklist Visual)

Antes de dar por concluida cualquier composición de video, verifica:

- [ ] ¿Los subtítulos utilizan tipografía limpia sin cajas, pastillas o fondos envolventes alrededor de cada palabra?
- [ ] ¿Los badges (`.hook-badge`, `.badge`) son texto tipográfico puro sin cajas contenedoras ni bordes redondeados?
- [ ] ¿Los iconos SVG vectoriales están limpios y sin píldoras o fondos redondeados envolventes?
- [ ] ¿Los títulos y subtítulos están libres de líneas horizontales decorativas (border-top, border-bottom, subrayados o filetes)?
- [ ] ¿Las tarjetas, paneles y ventanas tienen bordes simétricos y uniformes en los cuatro lados (sin `border-left` grueso asimétrico)?
- [ ] ¿Se eliminó cualquier uso de `transition:` en CSS?
- [ ] ¿La línea de tiempo de GSAP está pausada y registrada en `window.__timelines["main"]`?
- [ ] ¿`hyperframes check` reporta 0 errores y 0 advertencias?
