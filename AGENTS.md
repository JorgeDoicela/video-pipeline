# Directrices de Ingeniería y Comportamiento del Agente — video-pipeline

Este archivo define las reglas obligatorias de comportamiento, estándares de calidad y principios de ingeniería para cualquier agente que opere en este repositorio.

---

## 1. Misión y Filosofía del Repositorio

* **Propósito:** Pipeline 100% local, soberano y de coste marginal cero para la producción programática de video técnico y educativo mediante IA.
* **Stack Tecnológico:**
  * **Transcripción:** `faster-whisper` (CTranslate2, modelo int8, marcas de tiempo palabra por palabra).
  * **Procesamiento de Audio/Video:** FFmpeg con aceleración nativa VA-API (Mesa/Radeon ACO).
  * **Renderizado y Motion Graphics:** HyperFrames (Chrome Headless Shell con `BeginFrame` determinista) + GSAP 3.12.
* **Política de Cero Costes en la Nube:** Queda prohibida la dependencia de APIs externas de pago (ElevenLabs, fal.ai, HeyGen SaaS, OpenAI Audio). Todo cómputo debe ejecutarse localmente.

---

## 2. Estándares de Ingeniería y Calidad Profesional

* **Perfil Senior:** Opera siempre como un ingeniero de software senior (+10 años en producción). Cero parches, hacks o apaños temporales.
* **Tono Sobrio y Libre de Emojis:**
  * Queda estrictamente prohibido el uso de emojis en documentación, código fuente, commits y mensajes.
  * Prohibido el uso de lenguaje publicitario o inflado. Toda explicación debe ser fáctica, medible y técnicamente rigurosa.
* **Separación de Capas del Sistema (Arquitectura de 3 Capas):**
  * **Capa 1 (Debian Host):** FFmpeg nativo (`/usr/bin/ffmpeg`) para soporte directo de drivers gráficos AMD (`radeonsi_dri.so`).
  * **Capa 2 (Nix Flakes / Home Manager):** Gestores de paquetes (`uv`, `nodejs_22`, `pnpm`, `git`, `gh`).
  * **Capa 3 (Espacio de Trabajo):** Entorno virtual local Python (`.venv`) y módulos de Node.js (`node_modules`).

---

## 3. Contrato de Renderizado HyperFrames

Toda composición HTML dentro de `templates/` o `projects/` debe cumplir estrictamente las reglas del motor HyperFrames:

1. **Elemento Raíz de la Composición:**
   * El elemento contenedor raíz debe incluir los atributos:
     * `data-composition-id="main"`
     * `data-start="0"`
     * `data-duration="<segundos>"`
     * `data-width="<ancho>"` y `data-height="<alto>"`
   * No debe haber elementos hermanos gráficos fuera del contenedor raíz dentro de `<body>`.
2. **Animaciones Deterministas con GSAP:**
   * La línea de tiempo de GSAP debe inicializarse siempre pausada: `const tl = gsap.timeline({ paused: true });`.
   * Debe registrarse obligatoriamente en el objeto global: `window.__timelines["main"] = tl;`.
   * Debe posicionarse en el inicio: `tl.seek(0);`.
   * **Prohibición de Transiciones CSS:** Nunca utilices `transition:` en CSS para animar propiedades visuales. Las transiciones CSS dependen del reloj del navegador y rompen el renderizado determinista fotograma a fotograma en paralelo. Toda animación debe residir en la línea de tiempo de GSAP.
3. **Medios y Video:**
   * Todo elemento `<video>` o `<audio>` debe contar con `data-start="<tiempo>"` y `data-duration="<duración>"`.
   * Los archivos referenciados en `src` deben existir físicamente en disco.
4. **Accesibilidad Visual (WCAG AA):**
   * El contraste de texto sobre fondo debe cumplir un ratio mínimo de 4.5:1 para texto normal y 3:1 para texto grande.
   * La escala de fuentes para texto legible debe ser de al menos 28px en paneles 1080p, o marcarse con `data-layout-ignore` si se trata de textura gráfica puramente decorativa.

---

## 4. Estructura del Proyecto y Convenciones de Directorios

```text
video-pipeline/
├── core/              # Scripts CLI de procesamiento (transcripción, recorte, scaffolding)
│   ├── cut_silence.py
│   ├── transcribe.py
│   └── create_project.py
├── templates/         # Plantillas reutilizables por formato y caso de uso
│   ├── landscape_16_9/  # YouTube widescreen (1920x1080)
│   ├── portrait_9_16/   # Shorts/Reels/TikTok (1080x1920)
│   ├── square_1_1/      # Feeds LinkedIn/Instagram (1080x1080)
│   ├── talking_head/    # Video de presentador con lower-third y subtítulos
│   └── tech_explainer/  # Diagramas de arquitectura SVG interactivos
├── projects/          # Proyectos de video concretos generados a partir de templates
├── assets/            # Recursos estáticos globales (audio SFX, fuentes, iconos SVG)
├── docs/              # Documentación modular Docs-as-Code (00- a 05-)
├── package.json       # Dependencias de HyperFrames y scripts de ejecución
├── pyproject.toml     # Configuración declarativa de Python y Ruff
└── requirements.txt   # Dependencias de Python fijadas
```

---

## 5. Protocolo Operativo y Verificación Obligatoria

Antes de dar por concluida cualquier modificación o creación de proyecto:

1. **Creación de Proyecto:**
   ```bash
   python3 core/create_project.py <nombre_proyecto> --template <nombre_plantilla>
   ```
2. **Validación de Estándares HyperFrames:**
   ```bash
   pnpm exec hyperframes check projects/<nombre_proyecto>
   ```
   No se permiten errores de contraste, layout o media faltante.
3. **Auditoría de Código Python:**
   ```bash
   ruff check core
   ```
4. **Renderizado de Producción:**
   ```bash
   pnpm exec hyperframes render projects/<nombre_proyecto> -o projects/<nombre_proyecto>/video.mp4
   ```
