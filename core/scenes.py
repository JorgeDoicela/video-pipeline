#!/usr/bin/env python3
"""
Motor Multi-Escena (Storyboard) y Librería de Componentes Narrativos Vectoriales.
Orquesta secuencias temporales de escenas SVG/HTML animadas determinísticamente con GSAP 3.15
y sincronizadas con marcas de tiempo de voz y efectos de sonido (SFX).
"""

import html
import json
import math
import re
import unicodedata
from collections.abc import Callable
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from core.audio_mix import SfxEvent

VALID_TRANSITIONS = {"snap", "zoom_in", "slide_up"}
VALID_ATMOSPHERES = {"sunburst", "grid", "clean"}


@dataclass(frozen=True)
class SceneSpec:
    """Definición declarativa de una escena dentro de un storyboard temporal."""

    id: str
    start: float
    end: float
    headline: str
    component: str
    props: dict[str, Any] = field(default_factory=dict)
    badge: str | None = None
    transition: str = "snap"
    sfx: str = "whoosh"
    sfx_volume: float = 0.35
    cue_word: str | None = None

    @property
    def duration(self) -> float:
        return max(0.1, self.end - self.start)


@dataclass(frozen=True)
class StoryboardSpec:
    """Contrato raíz de un guion visual multi-escena."""

    title: str
    duration: float
    aspect_ratio: str = "9:16"
    atmosphere: str = "sunburst"
    scenes: list[SceneSpec] = field(default_factory=list)


def _safe_id(raw: str) -> str:
    cleaned = re.sub(r"[^a-zA-Z0-9_-]", "_", raw.strip())
    return cleaned or "scene"


# =====================================================================
# COMPONENTES NARRATIVOS SVG / HTML (SIN CÁSULAS, SIN BORDES ASIMÉTRICOS)
# =====================================================================


def _render_phone_mockup(
    scene_id: str, props: dict[str, Any], start: float, dur: float
) -> tuple[str, str]:
    app_title = html.escape(str(props.get("app_title", "Archivos")), quote=False)
    items = props.get("items", [])[:4]
    if not items:
        items = [
            {"label": "Documentos", "sublabel": "24 archivos", "highlight": False},
            {"label": "Capturas", "sublabel": "Acceso restringido", "highlight": True},
        ]

    rows_html: list[str] = []
    highlight_idx = 0
    for idx, item in enumerate(items):
        is_hl = bool(item.get("highlight", False))
        if is_hl:
            highlight_idx = idx
        lbl = html.escape(str(item.get("label", f"Elemento {idx + 1}")), quote=False)
        sub = html.escape(str(item.get("sublabel", "")), quote=False)
        hl_class = " phone-row-alert" if is_hl else ""
        icon_color = "var(--accent-danger)" if is_hl else "var(--accent-primary)"
        rows_html.append(
            f'<div id="{scene_id}_row_{idx}" class="ng-phone-row{hl_class}">'
            f'  <svg class="ng-bare-icon" width="36" height="36" viewBox="0 0 24 24" fill="none" stroke="{icon_color}" stroke-width="2">'
            f'    <path d="M22 19a2 2 0 0 1-2 2H4a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h5l2 3h9a2 2 0 0 1 2 2z"/>'
            f"  </svg>"
            f'  <div class="ng-phone-meta">'
            f'    <div class="ng-phone-lbl">{lbl}</div>'
            f'    <div class="ng-phone-sub">{sub}</div>'
            f"  </div>"
            f"</div>"
        )

    markup = f"""
    <div id="{scene_id}_phone" class="ng-phone-frame">
      <div class="ng-phone-statusbar" data-layout-ignore>
        <span>08:20</span>
        <span>5G · 94%</span>
      </div>
      <div class="ng-phone-app-title">{app_title}</div>
      <div class="ng-phone-list">
        {"".join(rows_html)}
      </div>
      <div id="{scene_id}_reticle" class="ng-focus-reticle" data-layout-ignore>
        <span class="ret-c ret-tl"></span>
        <span class="ret-c ret-tr"></span>
        <span class="ret-c ret-bl"></span>
        <span class="ret-c ret-br"></span>
      </div>
    </div>"""

    t_in = start + 0.12
    t_focus = min(start + max(0.55, dur * 0.32), start + dur - 0.35)
    # Posición vertical aproximada de cada fila dentro de la lista del teléfono
    reticle_y = 148 + highlight_idx * 126
    gsap_js = "\n".join(
        [
            f'tl.fromTo("#{scene_id}_phone", {{ y: 60, opacity: 0, scale: 0.94 }}, {{ y: 0, opacity: 1, scale: 1, duration: 0.45, ease: "power3.out" }}, {t_in:.3f});',
            f'tl.fromTo("#{scene_id} .ng-phone-row", {{ x: -24, opacity: 0 }}, {{ x: 0, opacity: 1, stagger: 0.08, duration: 0.32, ease: "power2.out" }}, {t_in + 0.14:.3f});',
            f'tl.set("#{scene_id}_reticle", {{ top: {reticle_y} }}, {t_focus - 0.02:.3f});',
            f'tl.fromTo("#{scene_id}_reticle", {{ opacity: 0, scale: 1.25 }}, {{ opacity: 1, scale: 1, duration: 0.32, ease: "back.out(2.0)" }}, {t_focus:.3f});',
        ]
    )
    return markup, gsap_js


def _render_network_graph(
    scene_id: str, props: dict[str, Any], start: float, dur: float
) -> tuple[str, str]:
    nodes = props.get("nodes", [])
    if not nodes:
        nodes = [
            {"id": "1", "label": "Nodo 1", "x": 160, "y": 130, "alert": False},
            {"id": "2", "label": "Nodo 2", "x": 450, "y": 240, "alert": False},
            {"id": "3", "label": "Nodo 3", "x": 720, "y": 130, "alert": False},
            {"id": "4", "label": "Origen", "x": 650, "y": 460, "alert": True},
            {"id": "5", "label": "Objetivo", "x": 240, "y": 480, "alert": True},
        ]
    edges = props.get("edges", [])
    if not edges and len(nodes) >= 2:
        edges = [
            {"from": nodes[i]["id"], "to": nodes[i + 1]["id"], "alert": i >= len(nodes) - 2}
            for i in range(len(nodes) - 1)
        ]

    node_map = {str(n["id"]): n for n in nodes}
    svg_edges: list[str] = []
    gsap_edges: list[str] = []

    for e_idx, edge in enumerate(edges):
        src = node_map.get(str(edge.get("from")))
        dst = node_map.get(str(edge.get("to")))
        if not src or not dst:
            continue
        x1, y1 = float(src.get("x", 150)), float(src.get("y", 150))
        x2, y2 = float(dst.get("x", 650)), float(dst.get("y", 450))
        length = max(10.0, math.hypot(x2 - x1, y2 - y1))
        is_alert = bool(edge.get("alert", False))
        stroke_col = "var(--accent-danger)" if is_alert else "var(--text-muted)"
        stroke_w = "5" if is_alert else "3"
        dash_attr = "" if is_alert else 'stroke-dasharray="10 10"'
        edge_id = f"{scene_id}_edge_{e_idx}"

        if is_alert:
            svg_edges.append(
                f'<line id="{edge_id}" x1="{x1}" y1="{y1}" x2="{x2}" y2="{y2}" '
                f'stroke="{stroke_col}" stroke-width="{stroke_w}" stroke-linecap="round" '
                f'stroke-dasharray="{length:.1f}" stroke-dashoffset="{length:.1f}" />'
            )
            t_edge = start + 0.35 + e_idx * 0.22
            gsap_edges.append(
                f'tl.to("#{edge_id}", {{ strokeDashoffset: 0, duration: 0.45, ease: "power2.out" }}, {t_edge:.3f});'
            )
        else:
            svg_edges.append(
                f'<line id="{edge_id}" x1="{x1}" y1="{y1}" x2="{x2}" y2="{y2}" '
                f'stroke="{stroke_col}" stroke-width="{stroke_w}" {dash_attr} opacity="0" />'
            )
            t_edge = start + 0.2 + e_idx * 0.14
            gsap_edges.append(
                f'tl.to("#{edge_id}", {{ opacity: 0.65, duration: 0.3 }}, {t_edge:.3f});'
            )

    svg_nodes: list[str] = []
    for n_idx, node in enumerate(nodes):
        nx, ny = float(node.get("x", 440)), float(node.get("y", 300))
        nid_txt = html.escape(str(node.get("id", n_idx + 1)), quote=False)
        nlbl = html.escape(str(node.get("label", "")), quote=False)
        is_alert = bool(node.get("alert", False))
        fill_col = "var(--accent-danger)" if is_alert else "var(--accent-primary)"
        n_gid = f"{scene_id}_node_{n_idx}"
        svg_nodes.append(
            f'<g id="{n_gid}" transform="translate({nx}, {ny})" opacity="0">'
            f'  <circle cx="0" cy="-16" r="22" fill="{fill_col}" />'
            f'  <path d="M -36 38 C -36 14, 36 14, 36 38 Z" fill="{fill_col}" />'
            f'  <text x="44" y="-26" fill="var(--text-primary)" font-size="28" font-weight="800">{nid_txt}</text>'
            f'  <text x="0" y="72" text-anchor="middle" fill="var(--text-primary)" font-size="28" font-weight="700">{nlbl}</text>'
            f"</g>"
        )

    center_label = html.escape(str(props.get("center_label", "")), quote=False)
    center_svg = (
        f'<text x="440" y="635" text-anchor="middle" fill="var(--accent-danger)" font-size="32" font-weight="900">{center_label}</text>'
        if center_label
        else ""
    )

    markup = f"""
    <div id="{scene_id}_graph_wrap" class="ng-graph-wrap">
      <svg class="ng-graph-svg" viewBox="0 0 880 680" width="880" height="680">
        {"".join(svg_edges)}
        {"".join(svg_nodes)}
        {center_svg}
      </svg>
    </div>"""

    t_in = start + 0.1
    gsap_lines = [
        f'tl.to("#{scene_id} g[id^=\\"{scene_id}_node_\\"]", {{ opacity: 1, stagger: 0.1, duration: 0.35, ease: "power2.out" }}, {t_in:.3f});',
        *gsap_edges,
    ]
    return markup, "\n".join(gsap_lines)


def _render_terminal_grid(
    scene_id: str, props: dict[str, Any], start: float, dur: float
) -> tuple[str, str]:
    screens = props.get("screens", [])[:6]
    if not screens:
        screens = [
            {
                "id": f"PC-0{i}",
                "lines": ["> arranque", "> kernel ok", "> estado: activo"],
                "status": "glitch" if i == 6 else "ok",
            }
            for i in range(1, 7)
        ]

    cards: list[str] = []
    glitch_ids: list[str] = []
    for idx, scr in enumerate(screens):
        sid = html.escape(str(scr.get("id", f"PC-0{idx + 1}")), quote=False)
        status = str(scr.get("status", "ok")).lower()
        lines = scr.get("lines", ["> ok"])[:3]
        lines_html = "".join(
            f'<div class="ng-term-line">{html.escape(str(ln), quote=False)}</div>' for ln in lines
        )
        card_id = f"{scene_id}_term_{idx}"
        alert_cls = " ng-term-alert" if status in {"alert", "glitch"} else ""
        if status in {"alert", "glitch"}:
            glitch_ids.append(card_id)
        cards.append(
            f'<div id="{card_id}" class="ng-term-card{alert_cls}">'
            f'  <div class="ng-term-body">{lines_html}</div>'
            f'  <div class="ng-term-foot"><span>{sid}</span><span class="ng-term-led"></span></div>'
            f"</div>"
        )

    markup = f'<div id="{scene_id}_grid" class="ng-term-grid">{"".join(cards)}</div>'
    t_in = start + 0.1
    t_glitch = min(start + max(0.6, dur * 0.45), start + dur - 0.3)
    gsap_lines = [
        f'tl.fromTo("#{scene_id} .ng-term-card", {{ opacity: 0, y: 24, scale: 0.94 }}, {{ opacity: 1, y: 0, scale: 1, stagger: 0.07, duration: 0.3, ease: "power2.out" }}, {t_in:.3f});',
    ]
    for gid in glitch_ids:
        gsap_lines.append(
            f'tl.to("#{gid}", {{ x: -8, duration: 0.05, repeat: 5, yoyo: true, ease: "none" }}, {t_glitch:.3f});'
        )
    return markup, "\n".join(gsap_lines)


def _render_connector_flow(
    scene_id: str, props: dict[str, Any], start: float, dur: float
) -> tuple[str, str]:
    left_label = html.escape(str(props.get("left_label", "HOST 2.0")), quote=False)
    right_label = html.escape(str(props.get("right_label", "DISPOSITIVO")), quote=False)
    status_text = html.escape(str(props.get("status_text", "CONEXIÓN ACTIVA")), quote=False)

    markup = f"""
    <div id="{scene_id}_flow" class="ng-flow-wrap">
      <div class="ng-flow-host">
        <div class="ng-flow-vents" data-layout-ignore>
          <span></span><span></span><span></span><span></span>
        </div>
        <div class="ng-flow-port" data-layout-ignore></div>
        <div class="ng-flow-label">{left_label}</div>
      </div>
      <div id="{scene_id}_plug" class="ng-flow-device">
        <div class="ng-flow-tip" data-layout-ignore></div>
        <div class="ng-flow-body">
          <div class="ng-flow-dev-title">{right_label}</div>
          <div id="{scene_id}_status" class="ng-flow-status">{status_text}</div>
        </div>
      </div>
    </div>"""

    t_in = start + 0.12
    t_connect = min(start + max(0.45, dur * 0.35), start + dur - 0.3)
    gsap_js = "\n".join(
        [
            f'tl.fromTo("#{scene_id}_flow .ng-flow-host", {{ x: -40, opacity: 0 }}, {{ x: 0, opacity: 1, duration: 0.35, ease: "power2.out" }}, {t_in:.3f});',
            f'tl.fromTo("#{scene_id}_plug", {{ x: 140, opacity: 0 }}, {{ x: 0, opacity: 1, duration: 0.45, ease: "power3.out" }}, {t_connect:.3f});',
            f'tl.fromTo("#{scene_id}_status", {{ opacity: 0 }}, {{ opacity: 1, duration: 0.25 }}, {t_connect + 0.35:.3f});',
        ]
    )
    return markup, gsap_js


def _render_stat_callout(
    scene_id: str, props: dict[str, Any], start: float, dur: float
) -> tuple[str, str]:
    primary = html.escape(str(props.get("primary_text", "100%")), quote=False)
    secondary = html.escape(str(props.get("secondary_text", "")), quote=False)
    bars = props.get("bars", [])[:4]

    bars_html: list[str] = []
    for idx, bar in enumerate(bars):
        lbl = html.escape(str(bar.get("label", f"Item {idx + 1}")), quote=False)
        val = html.escape(str(bar.get("value", "")), quote=False)
        pct = max(5, min(100, int(bar.get("pct", 50))))
        hl_col = "var(--accent-danger)" if bar.get("highlight") else "var(--accent-primary)"
        bars_html.append(
            f'<div class="ng-stat-bar-row">'
            f'  <div class="ng-stat-bar-head"><span>{lbl}</span><span>{val}</span></div>'
            f'  <div class="ng-stat-track"><div id="{scene_id}_bar_{idx}" class="ng-stat-fill" style="width: {pct}%; background: {hl_col}; transform-origin: left center;"></div></div>'
            f"</div>"
        )

    bars_block = f'<div class="ng-stat-bars">{"".join(bars_html)}</div>' if bars_html else ""
    sec_block = f'<div class="ng-stat-secondary">{secondary}</div>' if secondary else ""

    markup = f"""
    <div id="{scene_id}_stat" class="ng-stat-wrap">
      <div class="ng-stat-primary">{primary}</div>
      {sec_block}
      {bars_block}
    </div>"""

    t_in = start + 0.1
    gsap_lines = [
        f'tl.fromTo("#{scene_id}_stat .ng-stat-primary", {{ scale: 0.78, opacity: 0 }}, {{ scale: 1, opacity: 1, duration: 0.4, ease: "back.out(1.7)" }}, {t_in:.3f});',
    ]
    if secondary:
        gsap_lines.append(
            f'tl.fromTo("#{scene_id}_stat .ng-stat-secondary", {{ y: 18, opacity: 0 }}, {{ y: 0, opacity: 1, duration: 0.35, ease: "power2.out" }}, {t_in + 0.16:.3f});'
        )
    if bars_html:
        gsap_lines.append(
            f'tl.fromTo("#{scene_id} .ng-stat-fill", {{ scaleX: 0 }}, {{ scaleX: 1, stagger: 0.1, duration: 0.45, ease: "power3.out" }}, {t_in + 0.25:.3f});'
        )
    return markup, "\n".join(gsap_lines)


def _render_timeline_steps(
    scene_id: str, props: dict[str, Any], start: float, dur: float
) -> tuple[str, str]:
    """Línea de tiempo secuencial para procesos, historia o pasos ordenados."""
    steps = props.get("steps") or [
        {"tag": "01", "title": "Contexto inicial", "detail": "Punto de partida del análisis"},
        {
            "tag": "02",
            "title": "Punto de inflexión",
            "detail": "Evento o cambio estructural",
            "highlight": True,
        },
        {"tag": "03", "title": "Resultado medible", "detail": "Impacto verificable en el sistema"},
    ]
    rows_html: list[str] = []
    for i, step in enumerate(steps[:4]):
        tag = html.escape(str(step.get("tag", f"0{i + 1}")), quote=False)
        title = html.escape(str(step.get("title", "")), quote=False)
        detail = html.escape(str(step.get("detail", "")), quote=False)
        hl_cls = " ng-tl-highlight" if step.get("highlight") else ""
        rows_html.append(
            f'<div id="{scene_id}_step_{i}" class="ng-tl-item{hl_cls}">'
            f'<div class="ng-tl-marker">{tag}</div>'
            f'<div class="ng-tl-content">'
            f'<div class="ng-tl-title">{title}</div>'
            f'<div class="ng-tl-detail">{detail}</div>'
            f"</div></div>"
        )
    markup = f'<div id="{scene_id}_timeline" class="ng-timeline">{"".join(rows_html)}</div>'
    gsap = "\n".join(
        [
            f'tl.fromTo("#{scene_id} .ng-tl-item", {{ opacity: 0, x: -28 }}, {{ opacity: 1, x: 0, stagger: 0.14, duration: 0.36, ease: "power2.out" }}, {start + 0.12:.3f});',
        ]
    )
    return markup, gsap


def _render_comparison_split(
    scene_id: str, props: dict[str, Any], start: float, dur: float
) -> tuple[str, str]:
    """Comparativa en dos columnas simétricas (Antes/Después, A vs B, Mito/Realidad)."""
    left = props.get("left") or {
        "title": "Enfoque tradicional",
        "items": ["Proceso manual lento", "Sin trazabilidad", "Propenso a errores"],
    }
    right = props.get("right") or {
        "title": "Enfoque automatizado",
        "items": ["Ejecución determinista", "Auditoría completa", "Cero intervención manual"],
        "highlight": True,
    }

    def _col(col_data: dict[str, Any], side: str) -> str:
        title = html.escape(str(col_data.get("title", "")), quote=False)
        items = col_data.get("items") or []
        cls = " ng-cmp-accent" if col_data.get("highlight") else ""
        lis = "".join(f"<li>{html.escape(str(it), quote=False)}</li>" for it in items[:4])
        return (
            f'<div id="{scene_id}_{side}" class="ng-cmp-col{cls}">'
            f'<div class="ng-cmp-title">{title}</div>'
            f'<ul class="ng-cmp-list">{lis}</ul>'
            f"</div>"
        )

    markup = f'<div id="{scene_id}_compare" class="ng-compare">{_col(left, "left")}{_col(right, "right")}</div>'
    gsap = "\n".join(
        [
            f'tl.fromTo("#{scene_id}_left", {{ opacity: 0, x: -32 }}, {{ opacity: 1, x: 0, duration: 0.36, ease: "power2.out" }}, {start + 0.10:.3f});',
            f'tl.fromTo("#{scene_id}_right", {{ opacity: 0, x: 32 }}, {{ opacity: 1, x: 0, duration: 0.36, ease: "power2.out" }}, {start + 0.28:.3f});',
        ]
    )
    return markup, gsap


def _render_quote_focus(
    scene_id: str, props: dict[str, Any], start: float, dur: float
) -> tuple[str, str]:
    """Cita, versículo, ley o tesis central con atribución limpia."""
    quote = html.escape(
        str(props.get("quote", "La claridad estructural multiplica la retención del mensaje.")),
        quote=False,
    )
    author = html.escape(str(props.get("author", "Principio de diseño")), quote=False)
    context = html.escape(str(props.get("context", "")), quote=False)
    ctx_html = f'<div class="ng-quote-ctx">{context}</div>' if context else ""
    markup = (
        f'<div id="{scene_id}_quote_card" class="ng-quote-card">'
        f'<div class="ng-quote-mark" data-layout-ignore>&ldquo;</div>'
        f'<blockquote class="ng-quote-text">{quote}</blockquote>'
        f'<div class="ng-quote-author">{author}</div>'
        f"{ctx_html}"
        f"</div>"
    )
    gsap = "\n".join(
        [
            f'tl.fromTo("#{scene_id}_quote_card", {{ opacity: 0, y: 28, scale: 0.96 }}, {{ opacity: 1, y: 0, scale: 1, duration: 0.42, ease: "power3.out" }}, {start + 0.10:.3f});',
            f'tl.fromTo("#{scene_id} .ng-quote-author", {{ opacity: 0 }}, {{ opacity: 1, duration: 0.30 }}, {start + 0.45:.3f});',
        ]
    )
    return markup, gsap


def _render_bar_chart(
    scene_id: str, props: dict[str, Any], start: float, dur: float
) -> tuple[str, str]:
    """Gráfica de barras proporcionales animadas para métricas o comparativas."""
    bars = props.get("bars") or [
        {"label": "Manual", "value": 28, "display": "28%"},
        {"label": "Híbrido", "value": 56, "display": "56%"},
        {"label": "Pipeline", "value": 94, "display": "94%", "highlight": True},
    ]
    max_val = max((float(b.get("value", 1)) for b in bars), default=100.0) or 100.0
    rows_html: list[str] = []
    for i, bar in enumerate(bars[:5]):
        lbl = html.escape(str(bar.get("label", "")), quote=False)
        val = float(bar.get("value", 0))
        pct = max(6.0, min(100.0, (val / max_val) * 100.0))
        disp = html.escape(str(bar.get("display", f"{val:g}")), quote=False)
        hl_cls = " ng-bar-highlight" if bar.get("highlight") else ""
        rows_html.append(
            f'<div class="ng-bar-row{hl_cls}">'
            f'<div class="ng-bar-head"><span>{lbl}</span><span>{disp}</span></div>'
            f'<div class="ng-bar-track"><div id="{scene_id}_bar_{i}" class="ng-bar-fill" style="width: {pct:.1f}%; transform-origin: left center;"></div></div>'
            f"</div>"
        )
    markup = f'<div id="{scene_id}_bars" class="ng-bars">{"".join(rows_html)}</div>'
    gsap = "\n".join(
        [
            f'tl.fromTo("#{scene_id} .ng-bar-row", {{ opacity: 0, y: 16 }}, {{ opacity: 1, y: 0, stagger: 0.1, duration: 0.3, ease: "power2.out" }}, {start + 0.08:.3f});',
            f'tl.fromTo("#{scene_id} .ng-bar-fill", {{ scaleX: 0 }}, {{ scaleX: 1, stagger: 0.12, duration: 0.5, ease: "power3.out" }}, {start + 0.22:.3f});',
        ]
    )
    return markup, gsap


def _render_code_spotlight(
    scene_id: str, props: dict[str, Any], start: float, dur: float
) -> tuple[str, str]:
    """Bloque de código, comando o fórmula con línea destacada."""
    lang = html.escape(str(props.get("language", "bash")), quote=False)
    lines = props.get("lines") or [
        "$ pipeline produce -i voz.wav -p demo",
        "  transcribing with faster-whisper...",
        "  mixing 6 SFX events -> audio_mix.wav",
        "  rendered: video_demo.mp4 (100%)",
    ]
    hl_idx = int(props.get("highlight_line", len(lines) - 1))
    lines_html: list[str] = []
    for i, line in enumerate(lines[:8]):
        cls = " ng-code-line-active" if i == hl_idx else ""
        lines_html.append(
            f'<div id="{scene_id}_line_{i}" class="ng-code-line{cls}">'
            f'<span class="ng-code-num">{i + 1}</span>'
            f"<code>{html.escape(str(line), quote=False)}</code>"
            f"</div>"
        )
    markup = (
        f'<div id="{scene_id}_code" class="ng-code-card">'
        f'<div class="ng-code-lang">{lang}</div>'
        f'<div class="ng-code-body">{"".join(lines_html)}</div>'
        f"</div>"
    )
    gsap = "\n".join(
        [
            f'tl.fromTo("#{scene_id}_code", {{ opacity: 0, y: 24 }}, {{ opacity: 1, y: 0, duration: 0.36, ease: "power2.out" }}, {start + 0.08:.3f});',
            f'tl.fromTo("#{scene_id} .ng-code-line", {{ opacity: 0, x: -16 }}, {{ opacity: 1, x: 0, stagger: 0.08, duration: 0.28, ease: "power2.out" }}, {start + 0.18:.3f});',
        ]
    )
    return markup, gsap


ComponentRenderer = Callable[[str, dict[str, Any], float, float], tuple[str, str]]

COMPONENT_REGISTRY: dict[str, ComponentRenderer] = {
    "phone_mockup": _render_phone_mockup,
    "network_graph": _render_network_graph,
    "terminal_grid": _render_terminal_grid,
    "connector_flow": _render_connector_flow,
    "stat_callout": _render_stat_callout,
    "timeline_steps": _render_timeline_steps,
    "comparison_split": _render_comparison_split,
    "quote_focus": _render_quote_focus,
    "bar_chart": _render_bar_chart,
    "code_spotlight": _render_code_spotlight,
}


def load_storyboard(path: Path) -> StoryboardSpec:
    """Carga y valida estrictamente un archivo storyboard.json."""
    if not path.exists():
        raise FileNotFoundError(f"No se encontró el storyboard: {path}")

    raw = json.loads(path.read_text(encoding="utf-8"))
    raw_scenes = raw.get("scenes", [])
    if not raw_scenes:
        raise ValueError("El storyboard debe contener al menos una escena en 'scenes'.")

    scenes: list[SceneSpec] = []
    max_end = 0.0
    for idx, item in enumerate(raw_scenes, start=1):
        comp = str(item.get("component", "")).strip()
        if comp not in COMPONENT_REGISTRY:
            valid = ", ".join(sorted(COMPONENT_REGISTRY.keys()))
            raise ValueError(f"Componente desconocido '{comp}' en escena {idx}. Válidos: {valid}")

        start = float(item.get("start", 0.0))
        end = float(item.get("end", start + 3.0))
        if end <= start:
            raise ValueError(f"La escena {idx} tiene end ({end}) <= start ({start}).")
        max_end = max(max_end, end)

        transition = str(item.get("transition", "snap"))
        if transition not in VALID_TRANSITIONS:
            transition = "snap"

        scenes.append(
            SceneSpec(
                id=_safe_id(str(item.get("id", f"scene_{idx}"))),
                start=start,
                end=end,
                headline=str(item.get("headline", "")),
                component=comp,
                props=dict(item.get("props", {})),
                badge=item.get("badge"),
                transition=transition,
                sfx=str(item.get("sfx", "whoosh")),
                sfx_volume=float(item.get("sfx_volume", 0.35)),
                cue_word=str(item["cue_word"]).strip() if item.get("cue_word") else None,
            )
        )

    duration = float(raw.get("duration", max_end))
    if duration < max_end:
        duration = max_end

    atmosphere = str(raw.get("atmosphere", "sunburst"))
    if atmosphere not in VALID_ATMOSPHERES:
        atmosphere = "sunburst"

    return StoryboardSpec(
        title=str(raw.get("title", "Storyboard")),
        duration=duration,
        aspect_ratio=str(raw.get("aspect_ratio", "9:16")),
        atmosphere=atmosphere,
        scenes=scenes,
    )


def _norm_token(text: str) -> str:
    decomposed = unicodedata.normalize("NFKD", text.lower())
    ascii_only = "".join(ch for ch in decomposed if not unicodedata.combining(ch))
    return re.sub(r"[^a-z0-9]", "", ascii_only)


def align_storyboard_to_transcript(
    storyboard: StoryboardSpec,
    transcript: dict[str, Any],
    total_duration: float | None = None,
) -> StoryboardSpec:
    """
    Sincroniza los tiempos de inicio de escenas que definen 'cue_word' contra
    las marcas de tiempo palabra por palabra de Whisper y ajusta la duración total.
    """
    words: list[tuple[str, float]] = []
    for seg in transcript.get("segments", []):
        for w in seg.get("words", []):
            norm = _norm_token(str(w.get("word", "")))
            if norm:
                words.append((norm, float(w.get("start", 0.0))))

    adjusted: list[SceneSpec] = [
        SceneSpec(
            id=s.id,
            start=s.start,
            end=s.end,
            headline=s.headline,
            component=s.component,
            props=s.props,
            badge=s.badge,
            transition=s.transition,
            sfx=s.sfx,
            sfx_volume=s.sfx_volume,
            cue_word=s.cue_word,
        )
        for s in storyboard.scenes
    ]

    last_t = 0.0
    for idx, scene in enumerate(adjusted):
        if scene.cue_word:
            target = _norm_token(scene.cue_word)
            min_t = 0.0 if idx == 0 else adjusted[idx - 1].start + 0.4
            matched_t = next((t for tok, t in words if tok == target and t >= min_t), None)
            if matched_t is not None:
                matched_t = round(matched_t, 3)
                if idx > 0:
                    prev = adjusted[idx - 1]
                    adjusted[idx - 1] = SceneSpec(
                        **{**prev.__dict__, "end": max(prev.start + 0.3, matched_t)}
                    )
                new_end = max(matched_t + 0.5, scene.end)
                adjusted[idx] = SceneSpec(**{**scene.__dict__, "start": matched_t, "end": new_end})
                last_t = matched_t
                continue
        last_t = max(last_t, scene.start)

    final_dur = (
        float(total_duration)
        if total_duration and total_duration > 0
        else max(storyboard.duration, adjusted[-1].end)
    )
    if adjusted:
        last_scene = adjusted[-1]
        if final_dur > last_scene.start + 0.2:
            adjusted[-1] = SceneSpec(**{**last_scene.__dict__, "end": round(final_dur, 3)})

    return StoryboardSpec(
        title=storyboard.title,
        duration=round(final_dur, 3),
        aspect_ratio=storyboard.aspect_ratio,
        atmosphere=storyboard.atmosphere,
        scenes=adjusted,
    )


def extract_sfx_events(storyboard: StoryboardSpec) -> list[SfxEvent]:
    """Extrae los eventos de SFX sincronizados con el inicio de cada escena."""
    events: list[SfxEvent] = []
    for scene in storyboard.scenes:
        if scene.sfx and scene.sfx.lower() != "none":
            events.append(SfxEvent(sfx=scene.sfx, time_sec=scene.start, volume=scene.sfx_volume))
    return events


def build_storyboard_html_and_gsap(storyboard: StoryboardSpec) -> tuple[str, str]:
    """Genera el marcado HTML de todas las escenas y el timeline maestro GSAP determinista."""
    html_parts: list[str] = ["<!-- @scenes:start -->", '<div id="scenes-stage">']
    gsap_parts: list[str] = [
        "// @scenes-gsap:start",
        f'tl.fromTo("#progress-bar", {{ scaleX: 0 }}, {{ scaleX: 1, duration: {storyboard.duration:.3f}, ease: "none" }}, 0);',
    ]

    if storyboard.atmosphere == "sunburst":
        gsap_parts.append(
            f'if (document.getElementById("atmosphere-rays")) {{ tl.to("#atmosphere-rays", {{ rotation: 36, duration: {storyboard.duration:.3f}, ease: "none" }}, 0); }}'
        )

    for idx, scene in enumerate(storyboard.scenes):
        renderer = COMPONENT_REGISTRY[scene.component]
        comp_html, comp_gsap = renderer(scene.id, scene.props, scene.start, scene.duration)

        badge_html = (
            f'<div class="hook-badge" data-layout-ignore>{html.escape(scene.badge, quote=False)}</div>'
            if scene.badge
            else ""
        )
        headline_html = (
            f'<h2 class="scene-headline">{html.escape(scene.headline, quote=False)}</h2>'
            if scene.headline
            else ""
        )

        html_parts.append(
            f'<section id="{scene.id}" class="scene-node" style="opacity: 0; display: none;">'
            f'  <div class="scene-header">{badge_html}{headline_html}</div>'
            f'  <div class="scene-body">{comp_html}</div>'
            f"</section>"
        )

        # Entrada determinista según transición
        if scene.transition == "zoom_in":
            entry_from = "{ opacity: 0, scale: 0.90 }"
            entry_to = '{ opacity: 1, scale: 1, duration: 0.28, ease: "power3.out" }'
        elif scene.transition == "slide_up":
            entry_from = "{ opacity: 0, y: 40 }"
            entry_to = '{ opacity: 1, y: 0, duration: 0.28, ease: "power3.out" }'
        else:
            entry_from = "{ opacity: 0 }"
            entry_to = '{ opacity: 1, duration: 0.18, ease: "power2.out" }'

        gsap_parts.append(f'tl.set("#{scene.id}", {{ display: "flex" }}, {scene.start:.3f});')
        gsap_parts.append(f'tl.fromTo("#{scene.id}", {entry_from}, {entry_to}, {scene.start:.3f});')
        gsap_parts.append(comp_gsap)

        # Salida limpia al finalizar la escena (salvo la última si llega justo al final)
        if idx < len(storyboard.scenes) - 1:
            t_out = max(scene.start + 0.25, scene.end - 0.18)
            gsap_parts.append(
                f'tl.to("#{scene.id}", {{ opacity: 0, duration: 0.16, ease: "power2.in" }}, {t_out:.3f});'
            )
            gsap_parts.append(f'tl.set("#{scene.id}", {{ display: "none" }}, {scene.end:.3f});')

    html_parts.append("</div>")
    html_parts.append("<!-- @scenes:end -->")
    gsap_parts.append("// @scenes-gsap:end")
    return "\n".join(html_parts), "\n".join(gsap_parts)


def inject_storyboard_into_html(html_path: Path, storyboard: StoryboardSpec) -> None:
    """Inyecta de forma idempotente escenas HTML y coreografía GSAP en index.html."""
    if not html_path.exists():
        raise FileNotFoundError(f"No se encontró el archivo HTML: {html_path}")

    scenes_html, scenes_gsap = build_storyboard_html_and_gsap(storyboard)
    content = html_path.read_text(encoding="utf-8")

    # 1. Reemplazo idempotente del bloque HTML de escenas
    html_pattern = r"<!-- @scenes:start -->.*?<!-- @scenes:end -->"
    if re.search(html_pattern, content, flags=re.DOTALL):
        content = re.sub(html_pattern, lambda _: scenes_html, content, count=1, flags=re.DOTALL)
    else:
        raise ValueError(
            "El archivo HTML no contiene los marcadores <!-- @scenes:start/end --> compatibles con multi-escena."
        )

    # 2. Reemplazo idempotente del bloque GSAP de escenas
    gsap_pattern = r"// @scenes-gsap:start.*?// @scenes-gsap:end"
    if re.search(gsap_pattern, content, flags=re.DOTALL):
        content = re.sub(gsap_pattern, lambda _: scenes_gsap, content, count=1, flags=re.DOTALL)
    else:
        raise ValueError(
            "El archivo HTML no contiene los marcadores // @scenes-gsap:start/end compatibles con multi-escena."
        )

    # 3. Actualizar data-duration en #root
    content = re.sub(
        r'data-duration="[^"]*"',
        f'data-duration="{storyboard.duration:.2f}"',
        content,
        count=1,
    )

    html_path.write_text(content, encoding="utf-8")


def attach_audio_track_to_html(html_path: Path, audio_filename: str, duration: float) -> None:
    """Inserta o actualiza la etiqueta <audio> determinista de HyperFrames dentro de #root."""
    if not html_path.exists():
        raise FileNotFoundError(f"No se encontró el archivo HTML: {html_path}")

    content = html_path.read_text(encoding="utf-8")
    audio_tag = (
        f'<audio id="master-audio" src="{html.escape(audio_filename, quote=True)}" '
        f'data-start="0" data-duration="{duration:.2f}" data-track-index="0" data-volume="1"></audio>'
    )
    pattern = r'<audio id="master-audio"[^>]*></audio>'
    if re.search(pattern, content):
        content = re.sub(pattern, lambda _: audio_tag, content, count=1)
    elif re.search(r'<div[^>]*data-composition-id="main"[^>]*>', content):
        content = re.sub(
            r'(<div[^>]*data-composition-id="main"[^>]*>)',
            lambda m: f"{m.group(1)}\n      {audio_tag}",
            content,
            count=1,
        )
    elif re.search(r'<div id="root"[^>]*>', content):
        content = re.sub(
            r'(<div id="root"[^>]*>)',
            lambda m: f"{m.group(1)}\n      {audio_tag}",
            content,
            count=1,
        )
    else:
        raise ValueError(
            "El archivo HTML no contiene un contenedor raíz con data-composition-id='main' ni id='root'."
        )
    html_path.write_text(content, encoding="utf-8")
