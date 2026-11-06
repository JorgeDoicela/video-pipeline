# Directorio de Recursos Estáticos (Assets)

Este directorio almacena activos estáticos reutilizables para las composiciones de HyperFrames y los scripts del pipeline de video.

## Estructura de Subdirectorios

- `audio/`: Efectos de sonido (SFX en formato WAV o MP3 a 44.1/48kHz estéreo: whoosh, clicks, pops, transiciones y pistas de fondo).
- `fonts/`: Archivos de fuentes locales en formato WOFF2/TTF cuando se requieran familias tipográficas offline que no deban depender de Google Fonts o CDN externa.
- `icons/`: Iconografía vectorial en formato SVG (logos de tecnologías, marcas de nube, flechas, insignias y elementos gráficos).

## Uso en Composiciones HyperFrames

Para referenciar un recurso estático dentro de un proyecto:
1. Enlaces relativos a nivel de proyecto: los archivos colocados en `projects/<nombre>/assets/` o vinculados simbólicamente desde el directorio global `assets/`.
2. En HTML:
   ```html
   <!-- Icono SVG en línea o referenciado -->
   <img src="../../assets/icons/logo.svg" alt="Logo" />

   <!-- Efecto de sonido HTML5 vinculado a la línea de tiempo de GSAP -->
   <audio id="sfx-whoosh" src="../../assets/audio/whoosh.mp3" preload="auto"></audio>
   ```
3. Reglas de compatibilidad para el renderizador:
   - Todo archivo de medios referenciado debe existir en disco para evitar errores `404` durante la validación con `hyperframes check`.
   - Preferir SVG puros vectoriales con estilos CSS en línea sobre imágenes de mapa de bits (PNG/JPEG) para garantizar nitidez matemática a 1080p, 4K y pantallas Retina.
