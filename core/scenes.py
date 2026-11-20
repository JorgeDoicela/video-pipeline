#!/usr/bin/env python3
"""
Motor Multi-Escena (Storyboard) y Librería de 25 Componentes Narrativos Vectoriales / Canvas / Cutouts.
Orquesta secuencias temporales de escenas SVG/HTML/Canvas animadas determinísticamente con GSAP 3.15,
cambios de atmósfera/acento por escena, subtítulos Hero-Top o inferiores, y sincronización
con marcas de tiempo de voz y efectos de sonido (SFX primarios e intra-escena).
"""

import html
import json
import math
import re
from collections.abc import Callable
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from core._runtime import normalize_token
from core._styles_renderer import upsert_marked_css_block
from core.audio_mix import SfxEvent

VALID_TRANSITIONS = {"snap", "zoom_in", "slide_up"}
VALID_ATMOSPHERES = {"sunburst", "grid", "clean"}
VALID_CAPTION_POSITIONS = {"bottom", "hero_top"}

ACCENT_TOKEN_MAP = {
    "primary": "var(--accent-primary)",
    "secondary": "var(--accent-secondary)",
    "tertiary": "var(--accent-tertiary)",
    "warning": "var(--accent-warning)",
    "danger": "var(--accent-danger)",
}


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
    accent: str | None = None
    atmosphere: str | None = None

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
    caption_position: str = "bottom"
    brand: str | None = None
    category: str | None = None
    ambient_bed: bool = False
    music: str | None = None
    camera_motion: bool = True
    film_grain: bool = False
    words_per_group: int | None = None
    emphasis_words: list[str] = field(default_factory=list)
    scenes: list[SceneSpec] = field(default_factory=list)


def _safe_id(raw: str) -> str:
    cleaned = re.sub(r"[^a-zA-Z0-9_-]", "_", raw.strip())
    return cleaned or "scene"


def _resolve_accent_css(accent: str | None) -> str | None:
    if not accent:
        return None
    key = accent.strip().lower()
    if key in ACCENT_TOKEN_MAP:
        return ACCENT_TOKEN_MAP[key]
    return accent.strip()


# =====================================================================
# 25 COMPONENTES NARRATIVOS SVG / HTML / CANVAS (100% ESTÁNDAR LIMPIO DE JORGE)
# =====================================================================


def _render_phone_mockup(
    scene_id: str, props: dict[str, Any], start: float, dur: float
) -> tuple[str, str]:
    mode = str(props.get("mode", "list")).lower()
    raw_title = props.get("app_title") or props.get("app") or "Archivos"
    app_title = html.escape(str(raw_title), quote=False)

    if mode == "app_grid":
        clock_start = html.escape(str(props.get("clock_start", "08:00")), quote=False)
        clock_end = html.escape(str(props.get("clock_end", "08:20")), quote=False)
        alert_text = html.escape(
            str(props.get("alert_text", "PRÓXIMA CAPTURA 00:02")),
            quote=False,
        )
        palette = [
            "var(--accent-danger)",
            "var(--accent-primary)",
            "var(--accent-secondary)",
            "var(--accent-warning)",
            "var(--accent-tertiary)",
            "var(--accent-warning)",
            "var(--accent-secondary)",
            "var(--accent-primary)",
            "var(--accent-primary)",
            "var(--accent-danger)",
            "var(--text-muted)",
            "var(--accent-warning)",
            "var(--accent-danger)",
            "var(--accent-primary)",
            "var(--accent-secondary)",
            "var(--accent-warning)",
        ]
        cells_html = "".join(
            f'<div class="ng-app-tile" style="border-color: {col};">'
            f'<span class="ng-app-glyph" style="border-color: {col};"></span></div>'
            for col in palette
        )
        circumference = 2.0 * math.pi * 390.0
        capture_flash = bool(props.get("capture_flash", False))
        capture_count = int(props.get("capture_count", 5))
        flash_html = (
            f'<div id="{scene_id}_flash" class="ng-phone-flash" data-layout-ignore></div>'
            if capture_flash
            else ""
        )
        counter_html = (
            f'<div id="{scene_id}_cap_badge" class="ng-capture-counter" data-layout-ignore>'
            f'  <svg class="ng-bare-icon" width="38" height="38" viewBox="0 0 24 24" fill="none" '
            f'    stroke="var(--scene-accent, var(--accent-danger))" stroke-width="2.2">'
            f'    <path d="M22 19a2 2 0 0 1-2 2H4a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h5l2 3h9a2 2 0 0 1 2 2z"/>'
            f"  </svg>"
            f"  <span>{capture_count}</span>"
            f"</div>"
            if capture_flash
            else ""
        )
        markup = (
            f'<div id="{scene_id}_phone_hud" class="ng-phone-hud-wrap">'
            f'  <div id="{scene_id}_alert_tag" class="ng-hud-floating-tag">{alert_text}</div>'
            f'  <svg class="ng-phone-hud-ring" viewBox="0 0 860 860" width="820" height="820" data-layout-ignore>'
            f'    <circle cx="430" cy="430" r="390" fill="none" stroke="var(--divider)" stroke-width="3" stroke-dasharray="6 18" />'
            f'    <circle id="{scene_id}_hud_arc" cx="430" cy="430" r="390" fill="none" '
            f'      stroke="var(--scene-accent, var(--accent-danger))" stroke-width="6" stroke-linecap="round" '
            f'      stroke-dasharray="{circumference:.1f}" stroke-dashoffset="{circumference * 0.65:.1f}" '
            f'      transform="rotate(-90 430 430)" />'
            f"  </svg>"
            f'  <div id="{scene_id}_phone" class="ng-phone-frame ng-phone-grid-mode">'
            f"    {flash_html}"
            f'    <div class="ng-phone-statusbar" data-layout-ignore>'
            f"      <span>{clock_start}</span>"
            f'      <span class="ng-phone-island"></span>'
            f"      <span>5G · 98%</span>"
            f"    </div>"
            f'    <div id="{scene_id}_clock" class="ng-phone-big-clock">{clock_end}</div>'
            f'    <div class="ng-app-grid" data-layout-ignore>{cells_html}</div>'
            f'    <div class="ng-phone-dock" data-layout-ignore></div>'
            f"  </div>"
            f"  {counter_html}"
            f"</div>"
        )
        t_in = start + 0.10
        gsap_lines = [
            f'tl.fromTo("#{scene_id}_phone", {{ y: 50, opacity: 0, scale: 0.92 }}, {{ y: 0, opacity: 1, scale: 1, duration: 0.42, ease: "power3.out" }}, {t_in:.3f});',
            f'tl.fromTo("#{scene_id}_alert_tag", {{ opacity: 0, y: -16 }}, {{ opacity: 1, y: 0, duration: 0.30, ease: "power2.out" }}, {t_in + 0.12:.3f});',
            f'tl.fromTo("#{scene_id} .ng-app-tile", {{ scale: 0.6, opacity: 0 }}, {{ scale: 1, opacity: 1, stagger: 0.02, duration: 0.24, ease: "back.out(1.7)" }}, {t_in + 0.16:.3f});',
            f'tl.to("#{scene_id}_hud_arc", {{ strokeDashoffset: 0, rotation: 90, transformOrigin: "50% 50%", duration: {max(0.6, dur - 0.3):.3f}, ease: "power1.inOut" }}, {t_in:.3f});',
        ]
        if capture_flash and dur >= 1.4:
            t_fl1 = round(start + dur * 0.42, 3)
            t_fl2 = round(start + dur * 0.72, 3)
            gsap_lines.extend(
                [
                    f'tl.fromTo("#{scene_id}_flash", {{ opacity: 0.85 }}, {{ opacity: 0, duration: 0.28, ease: "power2.out", immediateRender: false }}, {t_fl1:.3f});',
                    f'tl.fromTo("#{scene_id}_flash", {{ opacity: 0.85 }}, {{ opacity: 0, duration: 0.28, ease: "power2.out", immediateRender: false }}, {t_fl2:.3f});',
                    f'tl.fromTo("#{scene_id}_cap_badge", {{ opacity: 0, scale: 0.7, y: 18 }}, {{ opacity: 1, scale: 1, y: 0, duration: 0.32, ease: "back.out(1.8)", immediateRender: false }}, {t_fl1 + 0.06:.3f});',
                ]
            )
        return markup, "\n".join(gsap_lines)

    items = props.get("items", [])[:4]
    if not items:
        if props.get("status") or props.get("detail"):
            items = [
                {
                    "label": str(props.get("status", "ACTIVO")),
                    "sublabel": str(props.get("detail", "Monitoreo en curso")),
                    "highlight": True,
                },
                {"label": "Registros", "sublabel": "Trazabilidad activa", "highlight": False},
            ]
        else:
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
        icon_color = (
            "var(--accent-danger)" if is_hl else "var(--scene-accent, var(--accent-primary))"
        )
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

    show_cursor = bool(props.get("show_cursor", False))
    cursor_html = (
        f'<svg id="{scene_id}_cursor" class="ng-phone-cursor" width="54" height="54" viewBox="0 0 24 24" '
        f'fill="var(--text-primary)" stroke="var(--bg)" stroke-width="1.6" data-layout-ignore>'
        f'<path d="M5 3l14 9-6.5 1.8L9 20.5 5 3z"/></svg>'
        if show_cursor
        else ""
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
      {cursor_html}
    </div>"""

    t_in = start + 0.12
    t_focus = min(start + max(0.55, dur * 0.32), start + dur - 0.35)
    reticle_y = 148 + highlight_idx * 126
    gsap_lines = [
        f'tl.fromTo("#{scene_id}_phone", {{ y: 60, opacity: 0, scale: 0.94 }}, {{ y: 0, opacity: 1, scale: 1, duration: 0.45, ease: "power3.out" }}, {t_in:.3f});',
        f'tl.fromTo("#{scene_id} .ng-phone-row", {{ x: -24, opacity: 0 }}, {{ x: 0, opacity: 1, stagger: 0.08, duration: 0.32, ease: "power2.out" }}, {t_in + 0.14:.3f});',
        f'tl.set("#{scene_id}_reticle", {{ top: {reticle_y} }}, {t_focus - 0.02:.3f});',
        f'tl.fromTo("#{scene_id}_reticle", {{ opacity: 0, scale: 1.25 }}, {{ opacity: 1, scale: 1, duration: 0.32, ease: "back.out(2.0)" }}, {t_focus:.3f});',
    ]
    if show_cursor:
        cursor_y = reticle_y + 42
        gsap_lines.extend(
            [
                f'tl.fromTo("#{scene_id}_cursor", {{ opacity: 0, x: 180, y: {cursor_y + 110} }}, {{ opacity: 1, x: 40, y: {cursor_y}, duration: 0.42, ease: "power3.out" }}, {t_focus + 0.06:.3f});',
                f'tl.to("#{scene_id}_cursor", {{ scale: 0.82, duration: 0.10, yoyo: true, repeat: 1, ease: "power2.inOut" }}, {t_focus + 0.50:.3f});',
            ]
        )
    return markup, "\n".join(gsap_lines)


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
        fill_col = (
            "var(--accent-danger)" if is_alert else "var(--scene-accent, var(--accent-primary))"
        )
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
    raw_primary = props.get("primary_text") or props.get("value") or "100%"
    raw_secondary = props.get("secondary_text") or props.get("label") or props.get("note") or ""
    raw_note = props.get("note") if props.get("label") and props.get("note") else ""
    primary = html.escape(str(raw_primary), quote=False)
    secondary = html.escape(str(raw_secondary), quote=False)
    note_txt = html.escape(str(raw_note), quote=False)
    bars = props.get("bars", [])[:4]

    bars_html: list[str] = []
    for idx, bar in enumerate(bars):
        lbl = html.escape(str(bar.get("label", f"Item {idx + 1}")), quote=False)
        val = html.escape(str(bar.get("value", "")), quote=False)
        pct = max(5, min(100, int(bar.get("pct", 50))))
        hl_col = (
            "var(--accent-danger)"
            if bar.get("highlight")
            else "var(--scene-accent, var(--accent-primary))"
        )
        bars_html.append(
            f'<div class="ng-stat-bar-row">'
            f'  <div class="ng-stat-bar-head"><span>{lbl}</span><span>{val}</span></div>'
            f'  <div class="ng-stat-track"><div id="{scene_id}_bar_{idx}" class="ng-stat-fill" style="width: {pct}%; background: {hl_col}; transform-origin: left center;"></div></div>'
            f"</div>"
        )

    bars_block = f'<div class="ng-stat-bars">{"".join(bars_html)}</div>' if bars_html else ""
    sec_block = f'<div class="ng-stat-secondary">{secondary}</div>' if secondary else ""
    note_block = f'<div class="ng-spot-sub">{note_txt}</div>' if note_txt else ""

    markup = f"""
    <div id="{scene_id}_stat" class="ng-stat-wrap">
      <div class="ng-stat-primary">{primary}</div>
      {sec_block}
      {note_block}
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


def _render_icon_spotlight(
    scene_id: str, props: dict[str, Any], start: float, dur: float
) -> tuple[str, str]:
    """Foco visual con icono SVG limpio (sin cápsula) y anillo de progreso radial."""
    label = html.escape(str(props.get("label", "Concepto clave")), quote=False)
    sublabel = html.escape(str(props.get("sublabel", "")), quote=False)
    icon_name = str(props.get("icon", "shield")).strip()
    ring_progress = float(props.get("ring_progress", 0.75))
    ring_progress = max(0.0, min(1.0, ring_progress))

    icon_svg = (
        '<svg class="ng-bare-icon" width="120" height="120" viewBox="0 0 24 24" fill="none" '
        'stroke="var(--scene-accent, var(--accent-primary))" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round">'
        '<path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z"/></svg>'
    )
    icons_dir = Path(__file__).resolve().parent.parent / "assets" / "icons"
    local_slug = icon_name.split(":", 1)[-1].split("/", 1)[-1]
    candidate = icons_dir / f"{local_slug}.svg"
    if not candidate.exists() and (":" in icon_name or "/" in icon_name):
        try:
            from core.fetch_assets import fetch_icon

            candidate = fetch_icon(icon_name, name=local_slug, icons_dir=icons_dir)
        except Exception:
            candidate = icons_dir / f"{local_slug}.svg"
    if candidate.exists():
        from core.fetch_assets import normalize_iconify_svg

        raw_svg = normalize_iconify_svg(candidate.read_text(encoding="utf-8")).strip()
        icon_svg = raw_svg.replace("<svg", '<svg class="ng-bare-icon" width="120" height="120"', 1)

    radius = 128.0
    circumference = 2.0 * math.pi * radius
    target_offset = circumference * (1.0 - ring_progress)
    sub_html = f'<div class="ng-spot-sub">{sublabel}</div>' if sublabel else ""

    markup = (
        f'<div id="{scene_id}_spotlight" class="ng-spotlight">'
        f'  <div class="ng-spot-ring">'
        f'    <svg class="ng-ring-svg" width="300" height="300" viewBox="0 0 300 300">'
        f'      <circle cx="150" cy="150" r="{radius:.0f}" fill="none" stroke="var(--border)" stroke-width="6" />'
        f'      <circle id="{scene_id}_ring_arc" cx="150" cy="150" r="{radius:.0f}" fill="none" '
        f'        stroke="var(--scene-accent, var(--accent-primary))" stroke-width="8" stroke-linecap="round" '
        f'        stroke-dasharray="{circumference:.1f}" stroke-dashoffset="{circumference:.1f}" '
        f'        transform="rotate(-90 150 150)" />'
        f"    </svg>"
        f'    <div class="ng-spot-icon">{icon_svg}</div>'
        f"  </div>"
        f'  <div class="ng-spot-label">{label}</div>'
        f"  {sub_html}"
        f"</div>"
    )
    gsap = "\n".join(
        [
            f'tl.fromTo("#{scene_id}_spotlight", {{ opacity: 0, scale: 0.92 }}, {{ opacity: 1, scale: 1, duration: 0.38, ease: "power3.out" }}, {start + 0.08:.3f});',
            f'tl.to("#{scene_id}_ring_arc", {{ strokeDashoffset: {target_offset:.1f}, duration: 0.85, ease: "power2.out" }}, {start + 0.18:.3f});',
        ]
    )
    return markup, gsap


def _render_radar_map(
    scene_id: str, props: dict[str, Any], start: float, dur: float
) -> tuple[str, str]:
    """Radar táctico y mapa vectorial con barrido angular, presets geográficos en assets/maps/ y ruta animada."""
    region_title = html.escape(str(props.get("region", "ZONA DE ANÁLISIS")), quote=False)
    targets = props.get("targets") or [
        {"label": "ORIGEN", "sublabel": "NODO CENTRAL", "x": 380, "y": 290, "alert": True},
        {"label": "SEÚL · RELAY", "sublabel": "ENLACE EXTERNO", "x": 510, "y": 470, "alert": False},
    ]
    map_preset = str(props.get("map_preset", "")).strip().lower()
    show_route = bool(props.get("route", False))

    zone_svg = (
        f'<polygon id="{scene_id}_zone" points="350,170 470,150 510,250 465,370 370,395 310,295" '
        f'fill="var(--accent-primary-soft)" stroke="var(--scene-accent, var(--accent-danger))" stroke-width="4" opacity="0" />'
    )
    if map_preset:
        custom_map_file = (
            Path(__file__).resolve().parent.parent / "assets" / "maps" / f"{map_preset}.svg"
        )
        if custom_map_file.exists():
            raw_map = custom_map_file.read_text(encoding="utf-8")
            inner_match = re.search(
                r"<svg[^>]*>(.*)</svg>", raw_map, flags=re.DOTALL | re.IGNORECASE
            )
            if inner_match:
                zone_svg = f'<g id="{scene_id}_zone" opacity="0">{inner_match.group(1)}</g>'

    route_svg = ""
    route_gsap = ""
    if show_route and len(targets) >= 2:
        x1, y1 = float(targets[0].get("x", 380)), float(targets[0].get("y", 290))
        x2, y2 = float(targets[1].get("x", 510)), float(targets[1].get("y", 470))
        cx = min(x1, x2) - 130
        cy = (y1 + y2) / 2.0 + 35
        route_len = round(math.hypot(x2 - x1, y2 - y1) * 1.65, 1)
        route_svg = (
            f'<path id="{scene_id}_route" d="M {x1} {y1} Q {cx} {cy} {x2} {y2}" '
            f'fill="none" stroke="var(--accent-warning)" stroke-width="5" stroke-linecap="round" '
            f'stroke-dasharray="{route_len}" stroke-dashoffset="{route_len}" />'
        )
        route_gsap = (
            f'tl.to("#{scene_id}_route", {{ strokeDashoffset: 0, duration: {min(1.4, max(0.5, dur * 0.42)):.3f}, '
            f'ease: "power2.inOut" }}, {start + 0.45:.3f});'
        )

    targets_svg: list[str] = []
    for idx, tgt in enumerate(targets[:4]):
        tx = float(tgt.get("x", 420))
        ty = float(tgt.get("y", 340))
        lbl = html.escape(str(tgt.get("label", f"OBJ-{idx + 1}")), quote=False)
        sub = html.escape(str(tgt.get("sublabel", "")), quote=False)
        is_alert = bool(tgt.get("alert", idx == 0))
        col = "var(--accent-danger)" if is_alert else "var(--accent-secondary)"
        tid = f"{scene_id}_tgt_{idx}"
        sub_svg = (
            f'<text x="34" y="28" fill="var(--text-muted)" font-size="28" font-weight="600">{sub}</text>'
            if sub
            else ""
        )
        targets_svg.append(
            f'<g id="{tid}" transform="translate({tx}, {ty})" opacity="0">'
            f'  <circle cx="0" cy="0" r="24" fill="none" stroke="{col}" stroke-width="2.5" opacity="0.65" />'
            f'  <circle cx="0" cy="0" r="9" fill="{col}" />'
            f'  <text x="34" y="-2" fill="var(--text-primary)" font-size="28" font-weight="800">{lbl}</text>'
            f"  {sub_svg}"
            f"</g>"
        )

    markup = f"""
    <div id="{scene_id}_radar" class="ng-radar-wrap">
      <svg class="ng-radar-svg" viewBox="0 0 880 680" width="880" height="680">
        <circle cx="440" cy="340" r="280" fill="none" stroke="var(--divider)" stroke-width="2" />
        <circle cx="440" cy="340" r="190" fill="none" stroke="var(--divider)" stroke-width="2" stroke-dasharray="8 12" />
        <circle cx="440" cy="340" r="100" fill="none" stroke="var(--divider)" stroke-width="2" />
        <line x1="140" y1="340" x2="740" y2="340" stroke="var(--divider)" stroke-width="1.5" />
        <line x1="440" y1="40" x2="440" y2="640" stroke="var(--divider)" stroke-width="1.5" />
        {zone_svg}
        <g id="{scene_id}_sweep" data-layout-ignore>
          <circle cx="440" cy="340" r="280" fill="none" stroke="none" />
          <path d="M 440 340 L 680 200 A 280 280 0 0 1 720 340 Z" fill="var(--accent-primary-soft)" opacity="0.55" />
          <line x1="440" y1="340" x2="720" y2="340" stroke="var(--scene-accent, var(--accent-primary))" stroke-width="3" />
        </g>
        {route_svg}
        {"".join(targets_svg)}
        <text x="440" y="648" text-anchor="middle" fill="var(--text-secondary)" font-size="28" font-weight="800">{region_title}</text>
      </svg>
    </div>"""

    t_in = start + 0.08
    gsap_lines = [
        f'tl.fromTo("#{scene_id}_zone", {{ opacity: 0, scale: 0.88, svgOrigin: "440 340" }}, {{ opacity: 1, scale: 1, svgOrigin: "440 340", duration: 0.4, ease: "power2.out" }}, {t_in:.3f});',
        f'tl.fromTo("#{scene_id}_sweep", {{ rotation: 0, svgOrigin: "440 340" }}, {{ rotation: 360, svgOrigin: "440 340", duration: {max(0.8, dur - 0.15):.3f}, ease: "none" }}, {start:.3f});',
        f'tl.to("#{scene_id} g[id^=\\"{scene_id}_tgt_\\"]", {{ opacity: 1, stagger: 0.18, duration: 0.32, ease: "power2.out" }}, {t_in + 0.18:.3f});',
    ]
    if route_gsap:
        gsap_lines.append(route_gsap)
    return markup, "\n".join(gsap_lines)


def _render_xray_scanner(
    scene_id: str, props: dict[str, Any], start: float, dur: float
) -> tuple[str, str]:
    """Inspección HUD con barrido láser horizontal y tarjetas de hallazgos laterales."""
    subject = html.escape(str(props.get("subject", "AUDITORÍA DE SISTEMA")), quote=False)
    callouts = props.get("callouts") or [
        {"title": "CAPTURAS", "detail": "Cada 5 min", "side": "left"},
        {"title": "TECLADO", "detail": "Monitoreado", "side": "right"},
    ]
    footer_tag = html.escape(str(props.get("footer_tag", "INSPECCIÓN PROFUNDA")), quote=False)

    cards_html: list[str] = []
    for idx, c in enumerate(callouts[:4]):
        c_title = html.escape(str(c.get("title", "")), quote=False)
        c_detail = html.escape(str(c.get("detail", "")), quote=False)
        side = "right" if str(c.get("side", "")).lower() == "right" or idx % 2 == 1 else "left"
        cards_html.append(
            f'<div id="{scene_id}_call_{idx}" class="ng-xray-callout ng-xray-{side}">'
            f'  <div class="ng-xray-call-title">{c_title}</div>'
            f'  <div class="ng-xray-call-detail">{c_detail}</div>'
            f"</div>"
        )

    mini_cells = "".join('<div class="ng-xray-cell"></div>' for _ in range(12))
    markup = f"""
    <div id="{scene_id}_xray" class="ng-xray-stage">
      <div class="ng-xray-core">
        <span class="ret-c ret-tl" data-layout-ignore></span>
        <span class="ret-c ret-tr" data-layout-ignore></span>
        <span class="ret-c ret-bl" data-layout-ignore></span>
        <span class="ret-c ret-br" data-layout-ignore></span>
        <div class="ng-xray-subject">{subject}</div>
        <div class="ng-xray-matrix" data-layout-ignore>{mini_cells}</div>
        <div id="{scene_id}_laser" class="ng-xray-laser" data-layout-ignore></div>
        <div class="ng-xray-footer">{footer_tag}</div>
      </div>
      <div class="ng-xray-callouts">
        {"".join(cards_html)}
      </div>
    </div>"""

    t_in = start + 0.08
    gsap = "\n".join(
        [
            f'tl.fromTo("#{scene_id}_xray .ng-xray-core", {{ opacity: 0, scale: 0.92 }}, {{ opacity: 1, scale: 1, duration: 0.35, ease: "power3.out" }}, {t_in:.3f});',
            f'tl.fromTo("#{scene_id}_laser", {{ y: 0, opacity: 0.95 }}, {{ y: 380, duration: {max(0.6, dur * 0.65):.3f}, repeat: 1, yoyo: true, ease: "power1.inOut" }}, {t_in + 0.05:.3f});',
            f'tl.fromTo("#{scene_id} .ng-xray-callout", {{ opacity: 0, y: 20 }}, {{ opacity: 1, y: 0, stagger: 0.14, duration: 0.32, ease: "power2.out" }}, {t_in + 0.22:.3f});',
        ]
    )
    return markup, gsap


def _render_system_alert(
    scene_id: str, props: dict[str, Any], start: float, dur: float
) -> tuple[str, str]:
    """Ventana modal de alerta del sistema con efecto máquina de escribir determinista."""
    title = html.escape(str(props.get("title", "AVISO DEL SISTEMA")), quote=False)
    message = str(
        props.get("message", "Esta operación está restringida por política de seguridad.")
    )
    subtext = html.escape(str(props.get("subtext", "")), quote=False)

    words = [w for w in message.split() if w]
    spans_html = " ".join(
        f'<span id="{scene_id}_tw_{i}" class="ng-tw-word" style="opacity: 0;">{html.escape(w, quote=False)}</span>'
        for i, w in enumerate(words[:18])
    )
    sub_block = f'<div class="ng-alert-sub">{subtext}</div>' if subtext else ""

    markup = f"""
    <div id="{scene_id}_modal" class="ng-alert-modal">
      <div class="ng-alert-head">
        <svg class="ng-bare-icon" width="38" height="38" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.4" stroke-linecap="round" stroke-linejoin="round">
          <path d="M10.29 3.86L1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0z"/>
          <line x1="12" y1="9" x2="12" y2="13"/>
          <line x1="12" y1="17" x2="12.01" y2="17"/>
        </svg>
        <span>{title}</span>
      </div>
      <div class="ng-alert-body">
        <div class="ng-alert-msg">{spans_html}<span class="ng-tw-cursor" data-layout-ignore>|</span></div>
        {sub_block}
      </div>
    </div>"""

    t_in = start + 0.08
    step = min(0.11, max(0.04, (dur - 0.5) / max(1, len(words))))
    gsap = "\n".join(
        [
            f'tl.fromTo("#{scene_id}_modal", {{ opacity: 0, scale: 0.90, y: 24 }}, {{ opacity: 1, scale: 1, y: 0, duration: 0.34, ease: "back.out(1.6)" }}, {t_in:.3f});',
            f'tl.to("#{scene_id} .ng-tw-word", {{ opacity: 1, stagger: {step:.3f}, duration: 0.06, ease: "none" }}, {t_in + 0.22:.3f});',
        ]
    )
    return markup, gsap


def _render_hex_inspector(
    scene_id: str, props: dict[str, Any], start: float, dur: float
) -> tuple[str, str]:
    """Inspector de volcado hexadecimal con fila resaltada y etiqueta de módulo descubierto."""
    target_addr = html.escape(str(props.get("target_addr", "0040A1D0")), quote=False)
    tag = html.escape(str(props.get("tag", "opprc")), quote=False)
    finding = html.escape(str(props.get("finding", f"MÓDULO OCULTO: {tag}")), quote=False)

    default_rows = [
        ("0040A1A0", "2E 2A 3B 12 28 95 42 0C D5 66", False),
        ("0040A1B0", "5F 8C B1 0F 24 DD 2A E8 72 B8", False),
        ("0040A1C0", "DA F6 CC 12 4F FE 95 D9 04 AD", True),
        (target_addr, "EA B9 8A 5E 10 1B 2E AF 0B 19", True),
        ("0040A1E0", "93 9C 07 D7 19 D9 13 3C B5 00", True),
        ("0040A1F0", "06 A2 87 7D C2 3B DD A0 07 75", False),
        ("0040A200", "E2 2D 1B B7 80 26 F6 9B 27 7B", False),
    ]
    rows_html: list[str] = []
    for addr, hex_bytes, is_hl in default_rows:
        hl_cls = " ng-hex-row-active" if is_hl else ""
        tag_html = f'<span class="ng-hex-tag">&larr; {tag}</span>' if addr == target_addr else ""
        rows_html.append(
            f'<div class="ng-hex-row{hl_cls}">'
            f'  <span class="ng-hex-addr">{addr}</span>'
            f'  <span class="ng-hex-bytes">{hex_bytes}</span>'
            f"  {tag_html}"
            f"</div>"
        )

    markup = f"""
    <div id="{scene_id}_hex" class="ng-hex-card">
      <div class="ng-hex-stream">
        {"".join(rows_html)}
      </div>
      <div id="{scene_id}_finding" class="ng-hex-finding">{finding}</div>
    </div>"""

    t_in = start + 0.08
    t_find = min(start + max(0.45, dur * 0.35), start + dur - 0.25)
    gsap = "\n".join(
        [
            f'tl.fromTo("#{scene_id} .ng-hex-row", {{ opacity: 0, x: -18 }}, {{ opacity: 1, x: 0, stagger: 0.05, duration: 0.24, ease: "power2.out" }}, {t_in:.3f});',
            f'tl.fromTo("#{scene_id}_finding", {{ opacity: 0, scale: 0.90, y: 16 }}, {{ opacity: 1, scale: 1, y: 0, duration: 0.32, ease: "back.out(1.8)" }}, {t_find:.3f});',
        ]
    )
    return markup, gsap


def _render_desktop_monitor(
    scene_id: str, props: dict[str, Any], start: float, dur: float
) -> tuple[str, str]:
    """Mockup de monitor panorámico de sistema operativo con barra de tareas y emblema central."""
    os_name = html.escape(str(props.get("os_name", "RED STAR OS")), quote=False)
    subtitle = html.escape(str(props.get("subtitle", "SISTEMA OPERATIVO AUDITADO")), quote=False)

    markup = f"""
    <div id="{scene_id}_desktop" class="ng-monitor-wrap">
      <div class="ng-monitor-screen">
        <div class="ng-monitor-icons" data-layout-ignore>
          <span></span><span></span><span></span><span></span>
        </div>
        <div id="{scene_id}_emblem" class="ng-monitor-center">
          <svg class="ng-bare-icon" width="140" height="140" viewBox="0 0 100 100">
            <polygon points="50,6 63,36 95,39 70,60 78,92 50,74 22,92 30,60 5,39 37,36"
              fill="var(--accent-primary-soft)" stroke="var(--scene-accent, var(--accent-danger))" stroke-width="4" stroke-linejoin="round" />
          </svg>
          <div class="ng-monitor-title">{os_name}</div>
          <div class="ng-monitor-sub">{subtitle}</div>
        </div>
        <div class="ng-monitor-taskbar" data-layout-ignore>
          <span class="ng-task-dot"></span>
          <span class="ng-task-slot"></span>
          <span class="ng-task-slot"></span>
        </div>
      </div>
      <div class="ng-monitor-neck" data-layout-ignore></div>
      <div class="ng-monitor-base" data-layout-ignore></div>
    </div>"""

    t_in = start + 0.08
    gsap = "\n".join(
        [
            f'tl.fromTo("#{scene_id}_desktop", {{ opacity: 0, y: 36, scale: 0.94 }}, {{ opacity: 1, y: 0, scale: 1, duration: 0.40, ease: "power3.out" }}, {t_in:.3f});',
            f'tl.fromTo("#{scene_id}_emblem", {{ scale: 0.82, opacity: 0 }}, {{ scale: 1, opacity: 1, duration: 0.45, ease: "back.out(1.7)" }}, {t_in + 0.16:.3f});',
        ]
    )
    return markup, gsap


def _render_keyboard_type(
    scene_id: str, props: dict[str, Any], start: float, dur: float
) -> tuple[str, str]:
    """Teclado interactivo + caja de escritura con teclas iluminadas y sugerencias."""
    typed_text = html.escape(str(props.get("typed_text", "corea del norte")), quote=False)
    active_keys = {str(k).upper() for k in props.get("active_keys", ["C", "O", "R", "E", "A"])}
    suggestions = props.get("suggestions") or ["oppa", "camarada", "sistema"]

    rows = [
        ["Q", "W", "E", "R", "T", "Y", "U", "I", "O", "P"],
        ["A", "S", "D", "F", "G", "H", "J", "K", "L", "Ñ"],
        ["Z", "X", "C", "V", "B", "N", "M"],
    ]
    kb_rows_html: list[str] = []
    for r in rows:
        keys_html = "".join(
            f'<span class="ng-kb-key{" ng-kb-key-active" if k in active_keys else ""}">{k}</span>'
            for k in r
        )
        kb_rows_html.append(f'<div class="ng-kb-row" data-layout-ignore>{keys_html}</div>')

    sug_html = "".join(
        f'<span class="ng-kb-sug{" ng-kb-sug-hl" if i == 1 else ""}">{html.escape(str(s), quote=False)}</span>'
        for i, s in enumerate(suggestions[:3])
    )

    markup = f"""
    <div id="{scene_id}_kb" class="ng-kb-wrap">
      <div class="ng-kb-input">
        <span id="{scene_id}_kb_txt">{typed_text}</span><span class="ng-tw-cursor" data-layout-ignore>|</span>
      </div>
      <div class="ng-kb-sug-bar">{sug_html}</div>
      <div class="ng-kb-board">
        {"".join(kb_rows_html)}
        <div class="ng-kb-space" data-layout-ignore></div>
      </div>
    </div>"""

    t_in = start + 0.08
    gsap = "\n".join(
        [
            f'tl.fromTo("#{scene_id}_kb", {{ opacity: 0, y: 36 }}, {{ opacity: 1, y: 0, duration: 0.36, ease: "power3.out" }}, {t_in:.3f});',
            f'tl.fromTo("#{scene_id} .ng-kb-key-active", {{ scale: 0.82 }}, {{ scale: 1.08, stagger: 0.07, duration: 0.18, yoyo: true, repeat: 1, ease: "power2.out" }}, {t_in + 0.18:.3f});',
        ]
    )
    return markup, gsap


def _render_padlock_denied(
    scene_id: str, props: dict[str, Any], start: float, dur: float
) -> tuple[str, str]:
    """Candado vectorial de seguridad con sello de bloqueo / acceso denegado."""
    stamp = html.escape(str(props.get("stamp", "ACCESO DENEGADO")), quote=False)
    detail = html.escape(str(props.get("detail", "ARCHIVO PROTEGIDO POR EL SISTEMA")), quote=False)

    markup = f"""
    <div id="{scene_id}_lock" class="ng-lock-wrap">
      <svg class="ng-bare-icon" width="240" height="240" viewBox="0 0 120 120">
        <line x1="8" y1="20" x2="112" y2="104" stroke="var(--text-muted)" stroke-width="5" stroke-dasharray="10 6" opacity="0.6" />
        <line x1="112" y1="20" x2="8" y2="104" stroke="var(--text-muted)" stroke-width="5" stroke-dasharray="10 6" opacity="0.6" />
        <path d="M 38 54 V 38 A 22 22 0 0 1 82 38 V 54" fill="none" stroke="var(--text-primary)" stroke-width="7" stroke-linecap="round" />
        <rect x="28" y="54" width="64" height="50" rx="10" fill="var(--surface)" stroke="var(--scene-accent, var(--accent-danger))" stroke-width="6" />
        <circle cx="60" cy="76" r="7" fill="var(--scene-accent, var(--accent-danger))" />
      </svg>
      <div id="{scene_id}_stamp" class="ng-lock-stamp">{stamp}</div>
      <div class="ng-spot-sub">{detail}</div>
    </div>"""

    t_in = start + 0.08
    t_stamp = min(start + max(0.24, dur * 0.16), start + dur - 0.25)
    gsap = "\n".join(
        [
            f'tl.fromTo("#{scene_id}_lock", {{ opacity: 0, scale: 0.90 }}, {{ opacity: 1, scale: 1, duration: 0.34, ease: "power3.out" }}, {t_in:.3f});',
            f'tl.fromTo("#{scene_id}_stamp", {{ opacity: 0, scale: 1.45, rotation: -6 }}, {{ opacity: 1, scale: 1, rotation: -4, duration: 0.28, ease: "back.out(2.2)" }}, {t_stamp:.3f});',
        ]
    )
    return markup, gsap


def _render_file_cards(
    scene_id: str, props: dict[str, Any], start: float, dur: float
) -> tuple[str, str]:
    """Tarjetas de archivos marcados con código de serie / huella criptográfica."""
    serial_code = html.escape(str(props.get("serial_code", "I2 · 278D · C274")), quote=False)
    caption = html.escape(str(props.get("caption", "TRAZABILIDAD DE ARCHIVOS ACTIVA")), quote=False)
    files = props.get("files") or ["FOTO.JPG", "VIDEO.AVI", "DOC.DOCX"]

    cards_html = "".join(
        f'<div class="ng-fcard">'
        f'  <div class="ng-fcard-name">{html.escape(str(f), quote=False)}</div>'
        f'  <div class="ng-fcard-hash" data-layout-ignore>ID: 4F7A-91C2</div>'
        f"</div>"
        for f in files[:3]
    )

    markup = f"""
    <div id="{scene_id}_files" class="ng-fcards-wrap">
      <div id="{scene_id}_serial" class="ng-fcards-serial">{serial_code}</div>
      <div class="ng-fcards-grid">{cards_html}</div>
      <div class="ng-spot-sub">{caption}</div>
    </div>"""

    t_in = start + 0.08
    gsap = "\n".join(
        [
            f'tl.fromTo("#{scene_id}_serial", {{ opacity: 0, y: -18 }}, {{ opacity: 1, y: 0, duration: 0.30, ease: "power2.out" }}, {t_in:.3f});',
            f'tl.fromTo("#{scene_id} .ng-fcard", {{ opacity: 0, y: 26, scale: 0.92 }}, {{ opacity: 1, y: 0, scale: 1, stagger: 0.12, duration: 0.34, ease: "back.out(1.6)" }}, {t_in + 0.14:.3f});',
        ]
    )
    return markup, gsap


def _render_custom_scene(
    scene_id: str, props: dict[str, Any], start: float, dur: float
) -> tuple[str, str]:
    """
    Escena abierta para inyectar cualquier composición SVG/HTML y coreografía GSAP a medida
    sin tocar el código del núcleo. Permite reemplazar el marcador {scene_id} y {start}.
    """
    raw_html = str(
        props.get(
            "html",
            '<div class="ng-spot-label">ESCENA PERSONALIZADA</div>',
        )
    )
    raw_gsap = str(props.get("gsap", ""))
    rendered_html = raw_html.replace("{scene_id}", scene_id)
    rendered_gsap = raw_gsap.replace("{scene_id}", scene_id).replace("{start}", f"{start:.3f}")
    if not rendered_gsap.strip():
        rendered_gsap = (
            f'tl.fromTo("#{scene_id}_custom", {{ opacity: 0, y: 20 }}, '
            f'{{ opacity: 1, y: 0, duration: 0.35, ease: "power2.out" }}, {start + 0.08:.3f});'
        )
    return (
        f'<div id="{scene_id}_custom" class="ng-custom-stage">{rendered_html}</div>',
        rendered_gsap,
    )


def _render_toggle_alert(
    scene_id: str, props: dict[str, Any], start: float, dur: float
) -> tuple[str, str]:
    """Panel de sistema con switch interactivo, detección de integridad y apagón CRT determinista."""
    label = html.escape(str(props.get("label", "PROTECCIÓN DEL SISTEMA")), quote=False)
    state_on = html.escape(str(props.get("state_on", "ACTIVO")), quote=False)
    state_off = html.escape(str(props.get("state_off", "DESACTIVADO")), quote=False)
    alert_title = html.escape(str(props.get("alert_title", "CAMBIO DETECTADO")), quote=False)
    alert_detail = html.escape(str(props.get("alert_detail", "INTEGRIDAD ALTERADA")), quote=False)
    crt_reboot = bool(props.get("crt_reboot", True))

    markup = f"""
    <div id="{scene_id}_toggle_wrap" class="ng-custom-stage">
      <svg viewBox="0 0 880 680" width="860" height="660">
        <rect x="80" y="90" width="720" height="440" rx="28" fill="var(--surface)" stroke="var(--border-strong)" stroke-width="8" />
        <rect x="405" y="530" width="70" height="72" fill="var(--border-strong)" />
        <rect x="310" y="598" width="260" height="20" rx="10" fill="var(--border-strong)" />
        <g id="{scene_id}_tg_ui">
          <text x="440" y="210" text-anchor="middle" fill="var(--text-primary)" font-size="42" font-weight="900">{label}</text>
          <rect id="{scene_id}_tg_track" x="330" y="255" width="220" height="110" rx="55" fill="#22c55e" />
          <circle id="{scene_id}_tg_knob" cx="495" cy="310" r="44" fill="#ffffff" />
          <text id="{scene_id}_tg_on" x="440" y="425" text-anchor="middle" fill="var(--text-muted)" font-size="30" font-weight="800">{state_on}</text>
          <text id="{scene_id}_tg_off" x="440" y="425" text-anchor="middle" fill="var(--accent-danger)" font-size="30" font-weight="800" opacity="0">{state_off}</text>
        </g>
        <g id="{scene_id}_tg_warn" opacity="0">
          <rect x="190" y="195" width="500" height="100" rx="16" fill="var(--accent-danger)" />
          <text x="440" y="260" text-anchor="middle" fill="#ffffff" font-size="40" font-weight="900">{alert_title}</text>
          <text x="440" y="365" text-anchor="middle" fill="var(--text-secondary)" font-size="30" font-weight="800">{alert_detail}</text>
        </g>
        <rect id="{scene_id}_tg_crt" x="130" y="306" width="620" height="8" rx="4" fill="#ffffff" opacity="0" />
      </svg>
    </div>"""

    t_flip = round(start + dur * 0.22, 3)
    t_warn = round(start + dur * 0.48, 3)
    t_crt = round(start + dur * 0.78, 3)
    gsap_lines = [
        f'tl.to("#{scene_id}_tg_knob", {{ attr: {{ cx: 385 }}, duration: 0.34, ease: "power2.inOut" }}, {t_flip:.3f});',
        f'tl.to("#{scene_id}_tg_track", {{ attr: {{ fill: "#334155" }}, duration: 0.34 }}, {t_flip:.3f});',
        f'tl.to("#{scene_id}_tg_on", {{ opacity: 0, duration: 0.14 }}, {t_flip + 0.08:.3f});',
        f'tl.to("#{scene_id}_tg_off", {{ opacity: 1, duration: 0.18 }}, {t_flip + 0.14:.3f});',
        f'tl.to("#{scene_id}_tg_ui", {{ opacity: 0, duration: 0.18 }}, {t_warn - 0.06:.3f});',
        f'tl.fromTo("#{scene_id}_tg_warn", {{ opacity: 0, scale: 0.9, svgOrigin: "440 280" }}, {{ opacity: 1, scale: 1, svgOrigin: "440 280", duration: 0.28, ease: "back.out(1.8)", immediateRender: false }}, {t_warn:.3f});',
    ]
    if crt_reboot:
        gsap_lines.extend(
            [
                f'tl.to("#{scene_id}_tg_warn", {{ opacity: 0, duration: 0.14 }}, {t_crt - 0.05:.3f});',
                f'tl.fromTo("#{scene_id}_tg_crt", {{ opacity: 0, scaleX: 1, svgOrigin: "440 310" }}, {{ opacity: 1, duration: 0.12, immediateRender: false }}, {t_crt:.3f});',
                f'tl.to("#{scene_id}_tg_crt", {{ scaleX: 0.02, opacity: 0, svgOrigin: "440 310", duration: 0.38, ease: "power3.in" }}, {t_crt + 0.20:.3f});',
            ]
        )
    return markup, "\n".join(gsap_lines)


def _render_conveyor_factory(
    scene_id: str, props: dict[str, Any], start: float, dur: float
) -> tuple[str, str]:
    """Línea de producción animada con prensa estampadora y dispositivos en cinta."""
    caption = html.escape(str(props.get("caption", "PREINSTALADO DE FÁBRICA")), quote=False)
    device_tag = html.escape(str(props.get("device_tag", "08:00")), quote=False)

    markup = f"""
    <div id="{scene_id}_factory" class="ng-custom-stage">
      <svg viewBox="0 0 880 700" width="860" height="680">
        <rect x="424" y="10" width="32" height="175" fill="var(--text-muted)" />
        <g id="{scene_id}_press">
          <rect x="340" y="168" width="200" height="122" rx="16" fill="var(--surface)" stroke="var(--accent-warning)" stroke-width="5" />
          <polygon points="440,190 452,224 488,226 460,248 470,280 440,260 410,280 420,248 392,226 428,224"
            fill="var(--accent-danger)" stroke="var(--accent-warning)" stroke-width="3" />
        </g>
        <g id="{scene_id}_belt">
          <rect x="105" y="330" width="170" height="245" rx="24" fill="var(--surface)" stroke="var(--border-strong)" stroke-width="5" />
          <path d="M 140 452 Q 190 412 240 452 Q 190 492 140 452 Z" fill="none" stroke="var(--accent-danger)" stroke-width="4" />
          <circle cx="190" cy="452" r="13" fill="var(--accent-danger)" />
          <rect x="355" y="330" width="170" height="245" rx="24" fill="var(--surface)" stroke="var(--scene-accent, var(--accent-danger))" stroke-width="5" />
          <path d="M 390 452 Q 440 412 490 452 Q 440 492 390 452 Z" fill="none" stroke="var(--accent-danger)" stroke-width="4" />
          <circle cx="440" cy="452" r="13" fill="var(--accent-danger)" />
          <rect x="605" y="330" width="170" height="245" rx="24" fill="var(--surface)" stroke="var(--border-strong)" stroke-width="5" />
          <text x="690" y="395" text-anchor="middle" fill="var(--text-primary)" font-size="30" font-weight="800">{device_tag}</text>
        </g>
        <rect x="40" y="580" width="800" height="40" rx="20" fill="var(--surface-elevated)" stroke="var(--border-strong)" stroke-width="4" />
        <text x="440" y="672" text-anchor="middle" fill="var(--accent-warning)" font-size="32" font-weight="900">{caption}</text>
      </svg>
    </div>"""

    gsap = "\n".join(
        [
            f'tl.fromTo("#{scene_id}_belt", {{ x: -110, opacity: 0 }}, {{ x: 0, opacity: 1, duration: 0.52, ease: "power2.out" }}, {start + 0.06:.3f});',
            f'tl.to("#{scene_id}_press", {{ y: 42, duration: 0.24, yoyo: true, repeat: 1, ease: "power3.inOut" }}, {start + min(0.55, dur * 0.35):.3f});',
        ]
    )
    return markup, gsap


def _render_cta_card(
    scene_id: str, props: dict[str, Any], start: float, dur: float
) -> tuple[str, str]:
    """Cierre interactivo de alto impacto con CTA y mutación de estado seguro a alerta."""
    cta_text = html.escape(str(props.get("cta_text", "COMPARTIR")), quote=False)
    clock = html.escape(str(props.get("clock", "08:20")), quote=False)
    before_label = html.escape(str(props.get("before_label", "SOLO MÍO")), quote=False)
    after_label = html.escape(str(props.get("after_label", "NO ES SOLO TUYO")), quote=False)

    markup = f"""
    <div id="{scene_id}_cta_wrap" class="ng-custom-stage">
      <svg viewBox="0 0 880 760" width="860" height="740">
        <g id="{scene_id}_cta_btn">
          <rect x="245" y="34" width="390" height="96" rx="48" fill="var(--scene-accent, var(--accent-danger))" />
          <text x="440" y="96" text-anchor="middle" fill="#ffffff" font-size="40" font-weight="900">{cta_text}</text>
        </g>
        <rect x="270" y="180" width="340" height="545" rx="42" fill="var(--surface)" stroke="var(--border-strong)" stroke-width="8" />
        <text x="440" y="290" text-anchor="middle" fill="var(--text-primary)" font-size="62" font-weight="900">{clock}</text>
        <g id="{scene_id}_cta_safe">
          <path d="M 405 430 V 405 A 35 35 0 0 1 475 405 V 430" fill="none" stroke="#22c55e" stroke-width="10" stroke-linecap="round" />
          <rect x="390" y="430" width="100" height="82" rx="14" fill="#22c55e" />
          <text x="440" y="575" text-anchor="middle" fill="#86efac" font-size="30" font-weight="800">{before_label}</text>
        </g>
        <g id="{scene_id}_cta_alert" opacity="0">
          <path d="M 335 465 Q 440 390 545 465 Q 440 540 335 465 Z" fill="rgba(255,59,92,0.22)" stroke="var(--accent-danger)" stroke-width="6" />
          <circle cx="440" cy="465" r="32" fill="var(--accent-danger)" />
          <circle cx="440" cy="465" r="13" fill="var(--bg)" />
          <text x="440" y="580" text-anchor="middle" fill="var(--accent-danger)" font-size="30" font-weight="900">{after_label}</text>
        </g>
      </svg>
    </div>"""

    t_btn = round(start + min(0.45, dur * 0.16), 3)
    t_morph = round(start + dur * 0.52, 3)
    gsap = "\n".join(
        [
            f'tl.fromTo("#{scene_id}_cta_btn", {{ opacity: 0, scale: 0.82, svgOrigin: "440 82" }}, {{ opacity: 1, scale: 1, svgOrigin: "440 82", duration: 0.36, ease: "back.out(1.8)" }}, {t_btn:.3f});',
            f'tl.to("#{scene_id}_cta_safe", {{ opacity: 0, duration: 0.24 }}, {t_morph - 0.08:.3f});',
            f'tl.fromTo("#{scene_id}_cta_alert", {{ opacity: 0, scale: 0.82, svgOrigin: "440 465" }}, {{ opacity: 1, scale: 1, svgOrigin: "440 465", duration: 0.38, ease: "back.out(1.8)", immediateRender: false }}, {t_morph:.3f});',
        ]
    )
    return markup, gsap


def _render_canvas_fx(
    scene_id: str, props: dict[str, Any], start: float, dur: float
) -> tuple[str, str]:
    """
    Primitiva Canvas 2D 100% determinista sincronizada con GSAP (sin requestAnimationFrame).
    Soporta efectos: 'particles', 'matrix', 'radar_waves', 'noise_field'.
    """
    effect = str(props.get("effect", "particles")).strip().lower()
    if effect not in {"particles", "matrix", "radar_waves", "noise_field"}:
        effect = "particles"
    title = html.escape(str(props.get("title", "")), quote=False)
    subtitle = html.escape(str(props.get("subtitle", "")), quote=False)
    accent_hex = html.escape(str(props.get("color", "#38bdf8")), quote=False)

    title_html = f'<div class="ng-canvas-title">{title}</div>' if title else ""
    sub_html = f'<div class="ng-spot-sub">{subtitle}</div>' if subtitle else ""

    markup = f"""
    <div id="{scene_id}_canvas_wrap" class="ng-canvas-wrap">
      <canvas id="{scene_id}_canvas" class="ng-canvas-el" width="840" height="620" data-layout-ignore></canvas>
      {title_html}
      {sub_html}
    </div>"""

    # Coreografía determinista conducida por proxy numérico en el timeline de GSAP
    gsap = (
        f"(function() {{\n"
        f'  const cvs = document.getElementById("{scene_id}_canvas");\n'
        f"  if (!cvs) return;\n"
        f'  const ctx = cvs.getContext("2d");\n'
        f"  const W = cvs.width, H = cvs.height;\n"
        f'  const mode = "{effect}";\n'
        f'  const col = "{accent_hex}";\n'
        f"  const proxy = {{ p: 0 }};\n"
        f"  const draw = (p) => {{\n"
        f"    ctx.clearRect(0, 0, W, H);\n"
        f'    if (mode === "radar_waves") {{\n'
        f"      for (let k = 0; k < 5; k++) {{\n"
        f"        const r = ((p * 260 + k * 64) % 290) + 18;\n"
        f"        ctx.beginPath();\n"
        f"        ctx.arc(W / 2, H / 2, r, 0, Math.PI * 2);\n"
        f"        ctx.strokeStyle = col;\n"
        f"        ctx.globalAlpha = Math.max(0.05, 1 - r / 310);\n"
        f"        ctx.lineWidth = 3;\n"
        f"        ctx.stroke();\n"
        f"      }}\n"
        f'    }} else if (mode === "matrix") {{\n'
        f'      ctx.font = "700 22px monospace";\n'
        f"      ctx.fillStyle = col;\n"
        f"      for (let c = 0; c < 24; c++) {{\n"
        f"        const x = 24 + c * 34;\n"
        f"        const base = ((c * 97) % 100) / 100;\n"
        f"        const headY = ((p * 1.4 + base) % 1.0) * H;\n"
        f"        for (let r = 0; r < 10; r++) {{\n"
        f"          const y = headY - r * 26;\n"
        f"          if (y < 0 || y > H) continue;\n"
        f"          ctx.globalAlpha = Math.max(0.08, 1 - r * 0.1);\n"
        f'          ctx.fillText(((c + r) % 2 === 0) ? "1" : "0", x, y);\n'
        f"        }}\n"
        f"      }}\n"
        f'    }} else if (mode === "noise_field") {{\n'
        f"      ctx.strokeStyle = col;\n"
        f"      ctx.lineWidth = 2.5;\n"
        f"      for (let row = 0; row < 12; row++) {{\n"
        f"        ctx.beginPath();\n"
        f"        ctx.globalAlpha = 0.25 + (row / 20);\n"
        f"        for (let x = 20; x <= W - 20; x += 20) {{\n"
        f"          const y = 70 + row * 42 + Math.sin(x * 0.018 + p * Math.PI * 4 + row * 0.6) * 18;\n"
        f"          if (x === 20) ctx.moveTo(x, y); else ctx.lineTo(x, y);\n"
        f"        }}\n"
        f"        ctx.stroke();\n"
        f"      }}\n"
        f"    }} else {{\n"
        f"      for (let i = 0; i < 42; i++) {{\n"
        f"        const angle = (i * 2.39996) + p * Math.PI * 1.5;\n"
        f"        const dist = 40 + ((i * 19 + p * 180) % 260);\n"
        f"        const x = W / 2 + Math.cos(angle) * dist * 1.3;\n"
        f"        const y = H / 2 + Math.sin(angle) * dist * 0.85;\n"
        f"        ctx.beginPath();\n"
        f"        ctx.arc(x, y, 4 + (i % 4), 0, Math.PI * 2);\n"
        f"        ctx.fillStyle = col;\n"
        f"        ctx.globalAlpha = 0.25 + 0.65 * Math.sin(p * Math.PI + i);\n"
        f"        ctx.fill();\n"
        f"      }}\n"
        f"    }}\n"
        f"    ctx.globalAlpha = 1;\n"
        f"  }};\n"
        f"  draw(0);\n"
        f'  tl.to(proxy, {{ p: 1, duration: {dur:.3f}, ease: "none", onUpdate: () => draw(proxy.p) }}, {start:.3f});\n'
        f"}})();"
    )
    return markup, gsap


def _render_image_cutout(
    scene_id: str, props: dict[str, Any], start: float, dur: float
) -> tuple[str, str]:
    """
    Muestra una imagen procesada o recorte transparente (cutout PNG/WEBP de assets/images/)
    con animación de entrada determinista, flotación sutil y título/etiqueta tipográfica limpia.
    """
    src_raw = str(props.get("src", "")).strip()
    if not src_raw:
        src_raw = "assets/images/cutout.png"
    elif src_raw.startswith("../../assets/"):
        src_raw = src_raw.removeprefix("../../")
    elif "/" not in src_raw and "\\" not in src_raw:
        src_raw = f"assets/images/{src_raw}"
    src_attr = html.escape(src_raw, quote=True)

    title = html.escape(str(props.get("title", "")), quote=False)
    subtitle = html.escape(str(props.get("subtitle", "")), quote=False)
    max_width = int(props.get("max_width", 720))
    float_motion = bool(props.get("float_motion", True))

    title_html = f'<div class="ng-cutout-title">{title}</div>' if title else ""
    sub_html = f'<div class="ng-spot-sub">{subtitle}</div>' if subtitle else ""

    markup = f"""
    <div id="{scene_id}_cutout_wrap" class="ng-cutout-wrap">
      <div id="{scene_id}_cutout_stage" class="ng-cutout-stage">
        <img id="{scene_id}_cutout_img" class="ng-cutout-img" src="{src_attr}"
          style="max-width: {max_width}px;" alt="{title}" data-layout-ignore />
      </div>
      {title_html}
      {sub_html}
    </div>"""

    t_in = start + 0.08
    gsap_lines = [
        f'tl.fromTo("#{scene_id}_cutout_img", {{ opacity: 0, y: 42, scale: 0.90 }}, {{ opacity: 1, y: 0, scale: 1, duration: 0.45, ease: "back.out(1.6)" }}, {t_in:.3f});',
    ]
    if float_motion and dur >= 1.4:
        float_dur = round(max(0.5, (dur - 0.55) / 2.0), 3)
        gsap_lines.append(
            f'tl.to("#{scene_id}_cutout_stage", {{ y: -14, duration: {float_dur:.3f}, yoyo: true, repeat: 1, ease: "sine.inOut" }}, {t_in + 0.45:.3f});'
        )
    if title:
        gsap_lines.append(
            f'tl.fromTo("#{scene_id}_cutout_wrap .ng-cutout-title", {{ opacity: 0, y: 18 }}, {{ opacity: 1, y: 0, duration: 0.32, ease: "power2.out" }}, {t_in + 0.16:.3f});'
        )
    return markup, "\n".join(gsap_lines)


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
    "icon_spotlight": _render_icon_spotlight,
    "radar_map": _render_radar_map,
    "xray_scanner": _render_xray_scanner,
    "system_alert": _render_system_alert,
    "hex_inspector": _render_hex_inspector,
    "desktop_monitor": _render_desktop_monitor,
    "keyboard_type": _render_keyboard_type,
    "padlock_denied": _render_padlock_denied,
    "file_cards": _render_file_cards,
    "toggle_alert": _render_toggle_alert,
    "conveyor_factory": _render_conveyor_factory,
    "cta_card": _render_cta_card,
    "canvas_fx": _render_canvas_fx,
    "image_cutout": _render_image_cutout,
    "custom_scene": _render_custom_scene,
}


_SCENES_BASE_CSS = """      #brand-bar {
        position: absolute;
        top: 42px;
        left: 72px;
        right: 72px;
        display: flex;
        align-items: center;
        justify-content: space-between;
        z-index: 35;
        pointer-events: none;
      }
      .brand-id {
        font-family: var(--font-mono);
        font-size: 30px;
        font-weight: 800;
        color: var(--text-primary);
        letter-spacing: 0.02em;
      }
      .brand-category {
        font-family: var(--font-mono);
        font-size: 28px;
        font-weight: 700;
        color: var(--text-muted);
        letter-spacing: 0.14em;
        text-transform: uppercase;
      }
      #root[data-caption-pos="hero_top"] #caption-zone {
        top: 118px;
        bottom: auto;
        min-height: 220px;
      }
      #root[data-caption-pos="hero_top"] .caption-bar {
        font-size: 68px;
        font-weight: 900;
        text-transform: uppercase;
        letter-spacing: -0.02em;
        line-height: 1.08;
      }
      #root[data-caption-pos="hero_top"] .word.active {
        text-shadow: 0 0 32px var(--accent-primary-glow), 0 4px 16px rgba(0, 0, 0, 0.72);
      }
      #root[data-caption-pos="hero_top"] #scenes-stage {
        top: 380px;
        height: 1360px;
      }
      .ng-bare-icon {
        background: transparent;
        border: none;
        padding: 0;
        flex-shrink: 0;
      }
      .ng-spot-sub {
        font-size: 28px;
        color: var(--text-muted);
        max-width: 820px;
      }
      .ret-c {
        position: absolute;
        width: 30px;
        height: 30px;
        border-color: var(--accent-danger);
        border-style: solid;
      }
      .ret-tl { top: 0; left: 0; border-width: 5px 0 0 5px; }
      .ret-tr { top: 0; right: 0; border-width: 5px 5px 0 0; }
      .ret-bl { bottom: 0; left: 0; border-width: 0 0 5px 5px; }
      .ret-br { bottom: 0; right: 0; border-width: 0 5px 5px 0; }
      .ng-tw-cursor {
        color: var(--scene-accent, var(--accent-warning));
        font-weight: 900;
        margin-left: 4px;
      }
      .ng-custom-stage {
        width: 100%;
        display: flex;
        flex-direction: column;
        align-items: center;
        justify-content: center;
        filter: drop-shadow(0 10px 28px rgba(0, 0, 0, 0.45));
      }
      #root[data-film-grain="true"]::after {
        content: "";
        position: absolute;
        inset: 0;
        pointer-events: none;
        z-index: 45;
        background:
          radial-gradient(circle at 50% 48%, transparent 52%, rgba(0, 0, 0, 0.52) 100%),
          repeating-radial-gradient(circle at 20% 30%, rgba(255, 255, 255, 0.018) 0 1px, transparent 1px 3px);
      }"""

_COMPONENT_CSS_BLOCKS: dict[str, str] = {
    "phone_mockup": """      .ng-phone-frame {
        position: relative;
        width: 620px;
        min-height: 820px;
        background: var(--surface);
        border: 2px solid var(--border-strong);
        border-radius: 42px;
        padding: 36px 32px;
        box-shadow: var(--shadow);
        display: flex;
        flex-direction: column;
        gap: 24px;
      }
      #root[data-width="1920"] .ng-phone-frame {
        width: 560px;
        min-height: 620px;
        border-radius: 36px;
        padding: 28px;
        gap: 18px;
      }
      .ng-phone-statusbar {
        display: flex;
        justify-content: space-between;
        font-size: 22px;
        font-weight: 700;
        color: var(--text-muted);
      }
      .ng-phone-app-title {
        font-size: 46px;
        font-weight: 900;
        color: var(--text-primary);
      }
      #root[data-width="1920"] .ng-phone-app-title {
        font-size: 40px;
      }
      .ng-phone-list {
        display: flex;
        flex-direction: column;
        gap: 18px;
      }
      #root[data-width="1920"] .ng-phone-list {
        gap: 14px;
      }
      .ng-phone-row {
        display: flex;
        align-items: center;
        gap: 20px;
        padding: 20px 24px;
        background: var(--surface-elevated);
        border: 1px solid var(--border);
        border-radius: 18px;
      }
      #root[data-width="1920"] .ng-phone-row {
        gap: 18px;
        padding: 16px 20px;
        border-radius: 16px;
      }
      .ng-phone-row.phone-row-alert {
        border-color: var(--accent-danger);
      }
      .ng-phone-meta {
        display: flex;
        flex-direction: column;
        gap: 4px;
        text-align: left;
      }
      .ng-phone-lbl {
        font-size: 30px;
        font-weight: 800;
        color: var(--text-primary);
      }
      #root[data-width="1920"] .ng-phone-lbl {
        font-size: 28px;
      }
      .ng-phone-sub {
        font-size: 28px;
        color: var(--text-muted);
      }
      .ng-focus-reticle {
        position: absolute;
        left: 14px;
        right: 14px;
        height: 118px;
        pointer-events: none;
        opacity: 0;
      }
      .ng-phone-hud-wrap {
        position: relative;
        width: 100%;
        display: flex;
        flex-direction: column;
        align-items: center;
        justify-content: center;
      }
      .ng-phone-hud-ring {
        position: absolute;
        pointer-events: none;
        z-index: 1;
      }
      .ng-hud-floating-tag {
        position: relative;
        z-index: 3;
        font-family: var(--font-mono);
        font-size: 28px;
        font-weight: 800;
        color: var(--text-primary);
        letter-spacing: 0.08em;
        margin-bottom: 24px;
      }
      .ng-phone-grid-mode {
        position: relative;
        z-index: 2;
        width: 520px;
        min-height: 760px;
        align-items: center;
        justify-content: space-between;
        overflow: hidden;
      }
      .ng-phone-flash {
        position: absolute;
        inset: 0;
        background: #ffffff;
        opacity: 0;
        pointer-events: none;
        z-index: 10;
        border-radius: inherit;
      }
      .ng-capture-counter {
        position: absolute;
        right: 72px;
        bottom: 18px;
        z-index: 5;
        display: inline-flex;
        align-items: center;
        gap: 10px;
        font-family: var(--font-mono);
        font-size: 38px;
        font-weight: 900;
        color: var(--scene-accent, var(--accent-danger));
        opacity: 0;
      }
      .ng-phone-cursor {
        position: absolute;
        top: 0;
        left: 50%;
        z-index: 12;
        opacity: 0;
        pointer-events: none;
        filter: drop-shadow(0 6px 12px rgba(0, 0, 0, 0.65));
      }
      .ng-phone-island {
        width: 110px;
        height: 24px;
        background: var(--bg);
        border-radius: 12px;
      }
      .ng-phone-big-clock {
        font-size: 92px;
        font-weight: 900;
        color: var(--text-primary);
        letter-spacing: -0.03em;
        line-height: 1;
      }
      .ng-app-grid {
        width: 100%;
        display: grid;
        grid-template-columns: repeat(4, 1fr);
        gap: 20px;
        padding: 12px 8px;
      }
      .ng-app-tile {
        height: 86px;
        background: var(--surface-elevated);
        border: 2px solid var(--border-strong);
        border-radius: 20px;
        display: flex;
        align-items: center;
        justify-content: center;
      }
      .ng-app-glyph {
        width: 32px;
        height: 32px;
        border: 2px solid var(--text-primary);
        border-radius: 8px;
      }
      .ng-phone-dock {
        width: 100%;
        height: 68px;
        background: var(--surface-elevated);
        border-radius: 24px;
      }""",
    "terminal_grid": """      .ng-term-grid {
        display: grid;
        grid-template-columns: 1fr 1fr;
        gap: 24px;
        width: 100%;
      }
      #root[data-width="1920"] .ng-term-grid {
        grid-template-columns: repeat(3, 1fr);
        gap: 20px;
        max-width: 1320px;
      }
      .ng-term-card {
        background: var(--surface);
        border: 2px solid var(--border-strong);
        border-radius: var(--radius-md, 14px);
        padding: 24px;
        display: flex;
        flex-direction: column;
        justify-content: space-between;
        min-height: 240px;
        font-family: var(--font-mono);
        text-align: left;
      }
      #root[data-width="1920"] .ng-term-card {
        padding: 20px;
        min-height: 200px;
      }
      .ng-term-card.ng-term-alert {
        border-color: var(--accent-danger);
      }
      .ng-term-body {
        display: flex;
        flex-direction: column;
        gap: 10px;
      }
      .ng-term-line {
        font-size: 28px;
        color: var(--accent-secondary);
        font-weight: 600;
      }
      .ng-term-alert .ng-term-line {
        color: var(--accent-danger);
      }
      .ng-term-foot {
        display: flex;
        justify-content: space-between;
        align-items: center;
        font-size: 28px;
        color: var(--text-muted);
        margin-top: 16px;
      }
      .ng-term-led {
        width: 14px;
        height: 14px;
        border-radius: 50%;
        background: var(--accent-secondary);
      }
      .ng-term-alert .ng-term-led {
        background: var(--accent-danger);
      }""",
    "connector_flow": """      .ng-flow-wrap {
        width: 100%;
        max-width: 1120px;
        display: flex;
        align-items: center;
        justify-content: space-between;
        gap: 24px;
      }
      .ng-flow-host {
        position: relative;
        width: 410px;
        height: 460px;
        background: var(--surface);
        border: 2px solid var(--border-strong);
        border-radius: 24px;
        padding: 36px;
        display: flex;
        flex-direction: column;
        justify-content: space-between;
      }
      #root[data-width="1920"] .ng-flow-host {
        width: 380px;
        height: 360px;
        padding: 32px;
      }
      .ng-flow-vents {
        display: flex;
        flex-direction: column;
        gap: 14px;
      }
      .ng-flow-vents span {
        height: 10px;
        width: 100%;
        background: var(--divider);
        border-radius: 4px;
      }
      .ng-flow-port {
        position: absolute;
        right: -14px;
        top: 50%;
        transform: translateY(-50%);
        width: 28px;
        height: 68px;
        background: var(--surface-elevated);
        border: 2px solid var(--accent-primary);
        border-radius: 6px;
      }
      .ng-flow-label {
        font-family: var(--font-mono);
        font-size: 30px;
        font-weight: 800;
        color: var(--text-primary);
      }
      .ng-flow-device {
        display: flex;
        align-items: center;
        flex: 1;
      }
      .ng-flow-tip {
        width: 72px;
        height: 54px;
        background: var(--text-secondary);
        border-radius: 6px 0 0 6px;
      }
      .ng-flow-body {
        flex: 1;
        min-height: 190px;
        background: var(--surface-elevated);
        border: 2px solid var(--accent-primary);
        border-radius: 20px;
        padding: 28px;
        display: flex;
        flex-direction: column;
        justify-content: center;
        gap: 12px;
        text-align: left;
      }
      .ng-flow-dev-title {
        font-size: 32px;
        font-weight: 900;
        color: var(--text-primary);
      }
      .ng-flow-status {
        font-family: var(--font-mono);
        font-size: 28px;
        font-weight: 700;
        color: var(--accent-secondary);
      }""",
    "network_graph": """      .ng-graph-wrap {
        width: 100%;
        max-width: 960px;
        display: flex;
        justify-content: center;
      }
      .ng-graph-svg {
        width: 100%;
        height: auto;
      }""",
    "stat_callout": """      .ng-stat-wrap {
        width: 100%;
        max-width: 960px;
        display: flex;
        flex-direction: column;
        align-items: center;
        gap: 32px;
        text-align: center;
      }
      .ng-stat-primary {
        font-size: 112px;
        font-weight: 900;
        line-height: 1;
        color: var(--accent-primary);
      }
      .ng-stat-secondary {
        font-size: 42px;
        font-weight: 800;
        color: var(--text-primary);
      }
      .ng-stat-bars {
        width: 100%;
        display: flex;
        flex-direction: column;
        gap: 24px;
        margin-top: 12px;
      }
      .ng-stat-bar-row {
        display: flex;
        flex-direction: column;
        gap: 10px;
      }
      .ng-stat-bar-head {
        display: flex;
        justify-content: space-between;
        font-size: 30px;
        font-weight: 700;
        color: var(--text-primary);
      }
      .ng-stat-track {
        width: 100%;
        height: 22px;
        background: var(--surface-elevated);
        border-radius: 12px;
        overflow: hidden;
      }
      .ng-stat-fill {
        height: 100%;
        border-radius: 12px;
      }""",
    "timeline_steps": """      .ng-timeline {
        width: 100%;
        display: flex;
        flex-direction: column;
        gap: 24px;
      }
      #root[data-width="1920"] .ng-timeline {
        max-width: 1360px;
        display: grid;
        grid-template-columns: repeat(3, 1fr);
        gap: 28px;
      }
      .ng-tl-item {
        display: flex;
        align-items: center;
        gap: 24px;
        padding: 28px 32px;
        background: var(--surface);
        border: 1px solid var(--border);
        border-radius: 20px;
      }
      #root[data-width="1920"] .ng-tl-item {
        flex-direction: column;
        align-items: flex-start;
        gap: 14px;
        padding: 36px 32px;
        border-radius: 22px;
        text-align: left;
      }
      .ng-tl-item.ng-tl-highlight {
        border: 2px solid var(--accent-primary);
      }
      .ng-tl-marker {
        font-family: var(--font-mono);
        font-size: 30px;
        font-weight: 800;
        color: var(--accent-primary);
        min-width: 72px;
      }
      .ng-tl-content {
        display: flex;
        flex-direction: column;
        gap: 6px;
        text-align: left;
      }
      .ng-tl-title {
        font-size: 34px;
        font-weight: 800;
        color: var(--text-primary);
      }
      .ng-tl-detail {
        font-size: 28px;
        line-height: 1.35;
        color: var(--text-muted);
      }""",
    "comparison_split": """      .ng-compare {
        width: 100%;
        max-width: 1320px;
        display: grid;
        grid-template-columns: 1fr 1fr;
        gap: 28px;
      }
      #root[data-width="1920"] .ng-compare {
        gap: 40px;
      }
      .ng-cmp-col {
        background: var(--surface);
        border: 1px solid var(--border);
        border-radius: 24px;
        padding: 36px 30px;
        display: flex;
        flex-direction: column;
        gap: 22px;
        text-align: left;
      }
      .ng-cmp-col.ng-cmp-accent {
        border: 2px solid var(--accent-secondary);
      }
      .ng-cmp-title {
        font-size: 34px;
        font-weight: 900;
        color: var(--text-primary);
      }
      .ng-cmp-list {
        list-style: none;
        display: flex;
        flex-direction: column;
        gap: 16px;
        font-size: 28px;
        line-height: 1.35;
        color: var(--text-secondary);
      }""",
    "quote_focus": """      .ng-quote-card {
        width: 100%;
        max-width: 1200px;
        padding: 56px 48px;
        background: var(--surface);
        border: 1px solid var(--border);
        border-radius: 28px;
        text-align: center;
        display: flex;
        flex-direction: column;
        gap: 24px;
      }
      .ng-quote-mark {
        font-size: 84px;
        line-height: 0.8;
        font-weight: 900;
        color: var(--accent-primary);
      }
      .ng-quote-text {
        font-size: 42px;
        font-weight: 700;
        line-height: 1.35;
        color: var(--text-primary);
      }
      .ng-quote-author {
        font-size: 28px;
        font-weight: 800;
        letter-spacing: 0.08em;
        text-transform: uppercase;
        color: var(--accent-primary);
      }
      .ng-quote-ctx {
        font-size: 28px;
        color: var(--text-muted);
      }""",
    "bar_chart": """      .ng-bars {
        width: 100%;
        max-width: 1120px;
        display: flex;
        flex-direction: column;
        gap: 28px;
        padding: 40px 36px;
        background: var(--surface);
        border: 1px solid var(--border);
        border-radius: 24px;
      }
      .ng-bar-row {
        display: flex;
        flex-direction: column;
        gap: 10px;
      }
      .ng-bar-head {
        display: flex;
        justify-content: space-between;
        font-size: 28px;
        font-weight: 700;
        color: var(--text-primary);
      }
      .ng-bar-track {
        width: 100%;
        height: 24px;
        background: var(--surface-elevated);
        border-radius: 12px;
        overflow: hidden;
      }
      .ng-bar-fill {
        height: 100%;
        background: var(--accent-primary);
        border-radius: 12px;
      }
      .ng-bar-highlight .ng-bar-fill {
        background: var(--accent-secondary);
      }""",
    "code_spotlight": """      .ng-code-card {
        width: 100%;
        max-width: 1180px;
        background: var(--surface);
        border: 1px solid var(--border);
        border-radius: 22px;
        padding: 32px;
        display: flex;
        flex-direction: column;
        gap: 18px;
        text-align: left;
      }
      .ng-code-lang {
        font-family: var(--font-mono);
        font-size: 28px;
        font-weight: 700;
        text-transform: uppercase;
        color: var(--accent-primary);
      }
      .ng-code-body {
        display: flex;
        flex-direction: column;
        gap: 10px;
        font-family: var(--font-mono);
        font-size: 28px;
        line-height: 1.4;
      }
      .ng-code-line {
        display: flex;
        gap: 18px;
        padding: 8px 14px;
        border-radius: 10px;
        color: var(--text-muted);
      }
      .ng-code-line-active {
        background: var(--accent-primary-soft);
        color: var(--text-primary);
        font-weight: 700;
      }
      .ng-code-num {
        color: var(--text-muted);
        min-width: 32px;
      }""",
    "icon_spotlight": """      .ng-spotlight {
        display: flex;
        flex-direction: column;
        align-items: center;
        gap: 24px;
        text-align: center;
      }
      .ng-spot-ring {
        position: relative;
        width: 300px;
        height: 300px;
        display: flex;
        align-items: center;
        justify-content: center;
      }
      .ng-ring-svg {
        position: absolute;
        inset: 0;
      }
      .ng-spot-icon {
        position: relative;
        z-index: 2;
        display: flex;
        align-items: center;
        justify-content: center;
      }
      .ng-spot-label {
        font-size: 42px;
        font-weight: 900;
        color: var(--text-primary);
      }""",
    "radar_map": """      .ng-radar-wrap {
        width: 100%;
        display: flex;
        justify-content: center;
      }
      .ng-radar-svg {
        width: 100%;
        height: auto;
        filter: drop-shadow(0 0 24px rgba(0, 0, 0, 0.4));
      }""",
    "xray_scanner": """      .ng-xray-stage {
        width: 100%;
        display: flex;
        flex-direction: column;
        align-items: center;
        gap: 28px;
      }
      .ng-xray-core {
        position: relative;
        width: 100%;
        max-width: 760px;
        min-height: 440px;
        background: var(--surface);
        border: 2px solid var(--border-strong);
        border-radius: 28px;
        padding: 36px;
        display: flex;
        flex-direction: column;
        align-items: center;
        justify-content: space-between;
        overflow: hidden;
      }
      .ng-xray-subject {
        font-family: var(--font-mono);
        font-size: 32px;
        font-weight: 800;
        color: var(--scene-accent, var(--accent-primary));
      }
      .ng-xray-matrix {
        width: 100%;
        display: grid;
        grid-template-columns: repeat(4, 1fr);
        gap: 18px;
        padding: 20px 0;
      }
      .ng-xray-cell {
        height: 74px;
        background: var(--surface-elevated);
        border: 1px solid var(--border);
        border-radius: 14px;
      }
      .ng-xray-laser {
        position: absolute;
        top: 24px;
        left: 16px;
        right: 16px;
        height: 4px;
        background: var(--scene-accent, var(--accent-danger));
        box-shadow: 0 0 20px var(--scene-accent, var(--accent-danger));
      }
      .ng-xray-footer {
        font-family: var(--font-mono);
        font-size: 28px;
        font-weight: 800;
        color: var(--text-secondary);
        letter-spacing: 0.1em;
      }
      .ng-xray-callouts {
        width: 100%;
        display: grid;
        grid-template-columns: 1fr 1fr;
        gap: 24px;
      }
      .ng-xray-callout {
        background: var(--surface);
        border: 2px solid var(--scene-accent, var(--accent-primary));
        border-radius: 18px;
        padding: 22px 26px;
        text-align: left;
      }
      .ng-xray-call-title {
        font-size: 30px;
        font-weight: 900;
        color: var(--text-primary);
      }
      .ng-xray-call-detail {
        font-size: 28px;
        color: var(--text-muted);
      }""",
    "system_alert": """      .ng-alert-modal {
        width: 100%;
        max-width: 820px;
        background: var(--surface);
        border: 2px solid var(--scene-accent, var(--accent-warning));
        border-radius: 24px;
        overflow: hidden;
        box-shadow: var(--shadow);
      }
      .ng-alert-head {
        background: var(--scene-accent, var(--accent-warning));
        color: var(--bg);
        padding: 22px 30px;
        display: flex;
        align-items: center;
        gap: 16px;
        font-size: 34px;
        font-weight: 900;
        letter-spacing: 0.04em;
      }
      .ng-alert-body {
        padding: 40px 36px;
        display: flex;
        flex-direction: column;
        gap: 20px;
        text-align: left;
      }
      .ng-alert-msg {
        font-size: 38px;
        font-weight: 800;
        line-height: 1.35;
        color: var(--text-primary);
      }
      .ng-alert-sub {
        font-family: var(--font-mono);
        font-size: 28px;
        color: var(--text-muted);
      }""",
    "hex_inspector": """      .ng-hex-card {
        width: 100%;
        background: var(--surface);
        border: 1px solid var(--border);
        border-radius: 22px;
        padding: 28px;
        display: flex;
        flex-direction: column;
        gap: 22px;
        font-family: var(--font-mono);
      }
      .ng-hex-stream {
        display: flex;
        flex-direction: column;
        gap: 10px;
      }
      .ng-hex-row {
        display: flex;
        align-items: center;
        justify-content: space-between;
        padding: 10px 16px;
        border-radius: 10px;
        font-size: 28px;
        color: var(--text-muted);
      }
      .ng-hex-row-active {
        background: var(--accent-primary-soft);
        color: var(--text-primary);
        font-weight: 800;
      }
      .ng-hex-tag {
        color: var(--accent-danger);
        font-weight: 900;
      }
      .ng-hex-finding {
        align-self: center;
        padding: 18px 32px;
        background: var(--surface-elevated);
        border: 2px solid var(--accent-danger);
        border-radius: 16px;
        font-size: 32px;
        font-weight: 900;
        color: var(--text-primary);
      }""",
    "desktop_monitor": """      .ng-monitor-wrap {
        width: 100%;
        display: flex;
        flex-direction: column;
        align-items: center;
      }
      .ng-monitor-screen {
        position: relative;
        width: 100%;
        max-width: 860px;
        min-height: 500px;
        background: var(--surface);
        border: 4px solid var(--border-strong);
        border-radius: 24px;
        padding: 36px;
        display: flex;
        align-items: center;
        justify-content: center;
        overflow: hidden;
      }
      .ng-monitor-icons {
        position: absolute;
        left: 28px;
        top: 32px;
        display: flex;
        flex-direction: column;
        gap: 16px;
      }
      .ng-monitor-icons span {
        width: 44px;
        height: 44px;
        background: var(--surface-elevated);
        border: 1px solid var(--border);
        border-radius: 10px;
      }
      .ng-monitor-center {
        display: flex;
        flex-direction: column;
        align-items: center;
        gap: 14px;
        text-align: center;
      }
      .ng-monitor-title {
        font-size: 44px;
        font-weight: 900;
        color: var(--text-primary);
      }
      .ng-monitor-sub {
        font-family: var(--font-mono);
        font-size: 28px;
        color: var(--text-muted);
      }
      .ng-monitor-taskbar {
        position: absolute;
        left: 0;
        right: 0;
        bottom: 0;
        height: 44px;
        background: var(--surface-elevated);
        display: flex;
        align-items: center;
        gap: 14px;
        padding: 0 24px;
      }
      .ng-task-dot {
        width: 18px;
        height: 18px;
        border-radius: 50%;
        background: var(--accent-danger);
      }
      .ng-task-slot {
        width: 84px;
        height: 16px;
        background: var(--divider);
        border-radius: 6px;
      }
      .ng-monitor-neck {
        width: 96px;
        height: 54px;
        background: var(--border-strong);
      }
      .ng-monitor-base {
        width: 320px;
        height: 18px;
        background: var(--border-strong);
        border-radius: 9px;
      }""",
    "keyboard_type": """      .ng-kb-wrap {
        width: 100%;
        display: flex;
        flex-direction: column;
        align-items: center;
        gap: 24px;
      }
      .ng-kb-input {
        width: 100%;
        max-width: 780px;
        padding: 24px 32px;
        background: var(--surface);
        border: 2px solid var(--scene-accent, var(--accent-primary));
        border-radius: 20px;
        font-family: var(--font-mono);
        font-size: 40px;
        font-weight: 800;
        color: var(--text-primary);
        text-align: left;
      }
      .ng-kb-sug-bar {
        display: flex;
        gap: 20px;
      }
      .ng-kb-sug {
        padding: 12px 26px;
        background: var(--surface);
        border: 1px solid var(--border);
        border-radius: 14px;
        font-size: 28px;
        font-weight: 700;
        color: var(--text-muted);
      }
      .ng-kb-sug-hl {
        border: 2px solid var(--scene-accent, var(--accent-danger));
        color: var(--text-primary);
      }
      .ng-kb-board {
        width: 100%;
        max-width: 840px;
        background: var(--surface);
        border: 2px solid var(--border-strong);
        border-radius: 24px;
        padding: 24px 18px;
        display: flex;
        flex-direction: column;
        align-items: center;
        gap: 12px;
      }
      .ng-kb-row {
        display: flex;
        gap: 10px;
        justify-content: center;
      }
      .ng-kb-key {
        width: 68px;
        height: 68px;
        background: var(--surface-elevated);
        border: 1px solid var(--border);
        border-radius: 12px;
        display: flex;
        align-items: center;
        justify-content: center;
        font-size: 28px;
        font-weight: 800;
        color: var(--text-primary);
      }
      .ng-kb-key-active {
        background: var(--scene-accent, var(--accent-danger));
        color: var(--bg);
      }
      .ng-kb-space {
        width: 420px;
        height: 52px;
        background: var(--surface-elevated);
        border: 1px solid var(--border);
        border-radius: 12px;
      }""",
    "padlock_denied": """      .ng-lock-wrap {
        width: 100%;
        display: flex;
        flex-direction: column;
        align-items: center;
        gap: 24px;
        text-align: center;
      }
      .ng-lock-stamp {
        padding: 16px 36px;
        background: var(--surface);
        border: 3px solid var(--accent-danger);
        border-radius: 14px;
        font-size: 40px;
        font-weight: 900;
        color: var(--accent-danger);
        letter-spacing: 0.08em;
      }""",
    "file_cards": """      .ng-fcards-wrap {
        width: 100%;
        display: flex;
        flex-direction: column;
        align-items: center;
        gap: 28px;
        text-align: center;
      }
      .ng-fcards-serial {
        font-family: var(--font-mono);
        font-size: 48px;
        font-weight: 900;
        color: var(--text-primary);
        letter-spacing: 0.08em;
      }
      .ng-fcards-grid {
        width: 100%;
        display: grid;
        grid-template-columns: repeat(3, 1fr);
        gap: 20px;
      }
      .ng-fcard {
        background: var(--surface);
        border: 2px solid var(--scene-accent, var(--accent-primary));
        border-radius: 20px;
        padding: 32px 20px;
        display: flex;
        flex-direction: column;
        align-items: center;
        gap: 12px;
      }
      .ng-fcard-name {
        font-family: var(--font-mono);
        font-size: 28px;
        font-weight: 800;
        color: var(--text-primary);
      }
      .ng-fcard-hash {
        font-family: var(--font-mono);
        font-size: 22px;
        color: var(--accent-danger);
      }""",
    "canvas_fx": """      .ng-canvas-wrap {
        width: 100%;
        display: flex;
        flex-direction: column;
        align-items: center;
        justify-content: center;
        gap: 20px;
      }
      .ng-canvas-el {
        width: 100%;
        max-width: 840px;
        height: auto;
        border-radius: 22px;
        border: 1px solid var(--border);
        background: var(--surface);
      }
      .ng-canvas-title {
        font-size: 42px;
        font-weight: 900;
        color: var(--text-primary);
        text-align: center;
      }""",
    "image_cutout": """      .ng-cutout-wrap {
        width: 100%;
        display: flex;
        flex-direction: column;
        align-items: center;
        justify-content: center;
        gap: 24px;
        text-align: center;
      }
      .ng-cutout-stage {
        display: flex;
        align-items: center;
        justify-content: center;
      }
      .ng-cutout-img {
        width: 100%;
        height: auto;
        max-height: 680px;
        object-fit: contain;
        filter: drop-shadow(0 18px 36px rgba(0, 0, 0, 0.55));
      }
      .ng-cutout-title {
        font-size: 42px;
        font-weight: 900;
        color: var(--text-primary);
        text-align: center;
      }""",
}


def build_scenes_css(used_components: set[str] | None = None) -> str:
    """
    Devuelve el bloque CSS canónico para los componentes narrativos usados,
    cabecera de marca, subtítulos Hero-Top y atmósfera dinámica.
    Si used_components es None, incluye todos los bloques (compatibilidad total).
    """
    parts = ["      /* @scenes-css:start */", _SCENES_BASE_CSS]
    for comp_name, css_block in _COMPONENT_CSS_BLOCKS.items():
        if used_components is None or comp_name in used_components:
            parts.append(css_block)
    parts.append("      /* @scenes-css:end */")
    return "\n".join(parts)


def load_storyboard(path: Path) -> StoryboardSpec:
    """Carga y valida estrictamente un archivo storyboard.json."""
    if not path.exists():
        raise FileNotFoundError(f"No se encontró el storyboard: {path}")

    raw = json.loads(path.read_text(encoding="utf-8-sig"))
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

        sc_atmos = item.get("atmosphere")
        if sc_atmos and str(sc_atmos) not in VALID_ATMOSPHERES:
            sc_atmos = None

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
                accent=str(item["accent"]).strip() if item.get("accent") else None,
                atmosphere=str(sc_atmos) if sc_atmos else None,
            )
        )

    duration = float(raw.get("duration", max_end))
    if duration < max_end:
        duration = max_end

    atmosphere = str(raw.get("atmosphere", "sunburst"))
    if atmosphere not in VALID_ATMOSPHERES:
        atmosphere = "sunburst"

    caption_position = str(raw.get("caption_position", "bottom"))
    if caption_position not in VALID_CAPTION_POSITIONS:
        caption_position = "bottom"

    raw_wpg = raw.get("words_per_group")
    words_per_group = int(raw_wpg) if raw_wpg is not None else None
    raw_emph = raw.get("emphasis_words") or []
    emphasis_words = [str(w).strip() for w in raw_emph if str(w).strip()]

    return StoryboardSpec(
        title=str(raw.get("title", "Storyboard")),
        duration=duration,
        aspect_ratio=str(raw.get("aspect_ratio", "9:16")),
        atmosphere=atmosphere,
        caption_position=caption_position,
        brand=str(raw["brand"]).strip() if raw.get("brand") else None,
        category=str(raw["category"]).strip() if raw.get("category") else None,
        ambient_bed=bool(raw.get("ambient_bed", False)),
        music=str(raw["music"]).strip() if raw.get("music") else None,
        camera_motion=bool(raw.get("camera_motion", True)),
        film_grain=bool(raw.get("film_grain", False)),
        words_per_group=words_per_group,
        emphasis_words=emphasis_words,
        scenes=scenes,
    )


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
            norm = normalize_token(str(w.get("word", "")))
            if norm:
                words.append((norm, float(w.get("start", 0.0))))

    adjusted: list[SceneSpec] = [SceneSpec(**s.__dict__) for s in storyboard.scenes]

    last_t = 0.0
    for idx, scene in enumerate(adjusted):
        if scene.cue_word:
            target = normalize_token(scene.cue_word)
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
        caption_position=storyboard.caption_position,
        brand=storyboard.brand,
        category=storyboard.category,
        ambient_bed=storyboard.ambient_bed,
        music=storyboard.music,
        camera_motion=storyboard.camera_motion,
        film_grain=storyboard.film_grain,
        words_per_group=storyboard.words_per_group,
        emphasis_words=list(storyboard.emphasis_words),
        scenes=adjusted,
    )


def extract_sfx_events(
    storyboard: StoryboardSpec, include_sub_events: bool = False
) -> list[SfxEvent]:
    """
    Extrae los eventos de SFX sincronizados con el inicio de cada escena.
    Si una escena declara sfx='none' o sfx_volume <= 0, suprime tanto el evento
    primario como cualquier sub-evento interno.
    Si include_sub_events=True, añade también efectos secundarios intra-escena
    (bloqueo de retícula, barrido de escáner, escritura de alerta, etc.).
    """
    events: list[SfxEvent] = []
    secondary_sfx_map = {
        "phone_mockup": ("shutter", 0.35),
        "terminal_grid": ("glitch", 0.45),
        "connector_flow": ("click", 0.38),
        "radar_map": ("scan", 0.32),
        "xray_scanner": ("scan", 0.30),
        "system_alert": ("alarm", 0.28),
        "hex_inspector": ("glitch", 0.36),
        "keyboard_type": ("keyclick", 0.25),
        "toggle_alert": ("powerdown", 0.65),
        "conveyor_factory": ("boom", 0.35),
        "cta_card": ("riser", 0.45),
    }
    for scene in storyboard.scenes:
        sfx_name = (scene.sfx or "").strip().lower()
        if not sfx_name or sfx_name == "none" or scene.sfx_volume <= 0:
            continue
        events.append(SfxEvent(sfx=scene.sfx, time_sec=scene.start, volume=scene.sfx_volume))
        if include_sub_events and scene.duration >= 1.8 and scene.component in secondary_sfx_map:
            sub_sfx, rel_offset = secondary_sfx_map[scene.component]
            sub_t = round(min(scene.start + scene.duration * rel_offset, scene.end - 0.3), 3)
            events.append(
                SfxEvent(sfx=sub_sfx, time_sec=sub_t, volume=round(scene.sfx_volume * 0.65, 2))
            )
    return events


def build_storyboard_html_and_gsap(storyboard: StoryboardSpec) -> tuple[str, str]:
    """Genera el marcado HTML de todas las escenas y el timeline maestro GSAP determinista."""
    html_parts: list[str] = ["<!-- @scenes:start -->"]
    if storyboard.brand or storyboard.category:
        b_txt = html.escape(storyboard.brand or "", quote=False)
        c_txt = html.escape(storyboard.category or "", quote=False)
        html_parts.append(
            f'<div id="brand-bar" data-layout-ignore>'
            f'<span class="brand-id">{b_txt}</span>'
            f'<span class="brand-category">{c_txt}</span>'
            f"</div>"
        )
    html_parts.append('<div id="scenes-stage">')

    gsap_parts: list[str] = [
        "// @scenes-gsap:start",
        f'tl.fromTo("#progress-bar", {{ scaleX: 0 }}, {{ scaleX: 1, duration: {storyboard.duration:.3f}, ease: "none" }}, 0);',
    ]

    if storyboard.atmosphere == "sunburst" or any(
        s.atmosphere == "sunburst" for s in storyboard.scenes
    ):
        gsap_parts.append(
            f'if (document.getElementById("atmosphere-rays")) {{ tl.to("#atmosphere-rays", {{ rotation: 36, duration: {storyboard.duration:.3f}, ease: "none" }}, 0); }}'
        )

    if storyboard.camera_motion and storyboard.duration >= 1.5:
        half_d = round(storyboard.duration / 2.0, 3)
        gsap_parts.append(
            f'tl.fromTo("#scenes-stage", {{ scale: 1.0 }}, {{ scale: 1.028, duration: {half_d:.3f}, yoyo: true, repeat: 1, ease: "sine.inOut", transformOrigin: "50% 50%" }}, 0);'
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
        header_block = (
            f'<div class="scene-header">{badge_html}{headline_html}</div>'
            if (badge_html or headline_html)
            else ""
        )

        accent_css = _resolve_accent_css(scene.accent)
        style_extra = f" --scene-accent: {accent_css};" if accent_css else ""

        html_parts.append(
            f'<section id="{scene.id}" class="scene-node" style="opacity: 0; display: none;{style_extra}">'
            f"  {header_block}"
            f'  <div class="scene-body">{comp_html}</div>'
            f"</section>"
        )

        if scene.transition == "zoom_in":
            entry_from = "{ opacity: 0, scale: 0.90 }"
            entry_to = '{ opacity: 1, scale: 1, duration: 0.28, ease: "power3.out" }'
        elif scene.transition == "slide_up":
            entry_from = "{ opacity: 0, y: 40 }"
            entry_to = '{ opacity: 1, y: 0, duration: 0.28, ease: "power3.out" }'
        else:
            entry_from = "{ opacity: 0 }"
            entry_to = '{ opacity: 1, duration: 0.18, ease: "power2.out" }'

        if scene.atmosphere:
            show_rays = "block" if scene.atmosphere == "sunburst" else "none"
            show_grid = "block" if scene.atmosphere == "grid" else "none"
            gsap_parts.append(
                f'if (document.getElementById("atmosphere-rays")) {{ tl.set("#atmosphere-rays", {{ display: "{show_rays}" }}, {scene.start:.3f}); }}'
            )
            gsap_parts.append(
                f'if (document.getElementById("atmosphere-grid")) {{ tl.set("#atmosphere-grid", {{ display: "{show_grid}" }}, {scene.start:.3f}); }}'
            )

        gsap_parts.append(f'tl.set("#{scene.id}", {{ display: "flex" }}, {scene.start:.3f});')
        gsap_parts.append(f'tl.fromTo("#{scene.id}", {entry_from}, {entry_to}, {scene.start:.3f});')
        gsap_parts.append(comp_gsap)

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


def _set_root_attr(content: str, attr: str, value: str) -> str:
    """Actualiza o añade un atributo data-* exclusivamente en la etiqueta raíz data-composition-id='main'."""

    def _repl(match: re.Match[str]) -> str:
        tag = match.group(0)
        attr_pat = rf'\b{re.escape(attr)}="[^"]*"'
        if re.search(attr_pat, tag):
            return re.sub(attr_pat, f'{attr}="{value}"', tag, count=1)
        return tag[:-1] + f' {attr}="{value}">'

    return re.sub(r'<div\b[^>]*\bdata-composition-id="main"[^>]*>', _repl, content, count=1)


def _sync_local_image_assets(project_dir: Path, storyboard: StoryboardSpec) -> None:
    """
    Copia los recortes de imagen referenciados por escenas 'image_cutout' desde el repositorio
    global assets/images/ hacia <project_dir>/assets/images/ para cumplir con el StaticGuard
    de HyperFrames (prohibido '../' fuera de la raíz del proyecto).
    """
    repo_images_dir = Path(__file__).resolve().parent.parent / "assets" / "images"
    for scene in storyboard.scenes:
        if scene.component != "image_cutout":
            continue
        src_raw = str(scene.props.get("src", "")).strip()
        filename = Path(src_raw).name if src_raw else "cutout.png"
        src_candidate = repo_images_dir / filename
        if src_candidate.exists():
            dest_dir = project_dir / "assets" / "images"
            dest_dir.mkdir(parents=True, exist_ok=True)
            dest_file = dest_dir / filename
            if not dest_file.exists() or src_candidate.resolve() != dest_file.resolve():
                import shutil

                shutil.copy2(src_candidate, dest_file)


def inject_storyboard_into_html(html_path: Path, storyboard: StoryboardSpec) -> None:
    """Inyecta de forma idempotente CSS de componentes, escenas HTML y coreografía GSAP en index.html."""
    if not html_path.exists():
        raise FileNotFoundError(f"No se encontró el archivo HTML: {html_path}")

    _sync_local_image_assets(html_path.parent, storyboard)
    scenes_html, scenes_gsap = build_storyboard_html_and_gsap(storyboard)
    used_components = {s.component for s in storyboard.scenes}
    scenes_css = build_scenes_css(used_components=used_components)
    content = html_path.read_text(encoding="utf-8")

    # 0. Inyección idempotente del CSS de los componentes usados (tree-shaking)
    content = upsert_marked_css_block(content, "scenes-css", scenes_css)

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

    # 3. Actualizar data-duration, data-atmosphere, data-caption-pos y data-film-grain exclusivamente en #root
    content = _set_root_attr(content, "data-duration", f"{storyboard.duration:.2f}")
    content = _set_root_attr(content, "data-atmosphere", storyboard.atmosphere)
    content = _set_root_attr(content, "data-caption-pos", storyboard.caption_position)
    content = _set_root_attr(
        content, "data-film-grain", "true" if storyboard.film_grain else "false"
    )

    html_path.write_text(content, encoding="utf-8")


def _select_component_for_text(text: str, index: int) -> tuple[str, dict[str, Any], str]:
    """Selecciona inteligentemente el componente e instancia sus props según el contenido semántico."""
    low = text.lower()
    words = text.split()
    headline = " ".join(words[:5]) + ("..." if len(words) > 5 else "")
    num_match = re.search(r"\b(\d+(?:[.,]\d+)?(?:\s*%|\s*ms|\s*s|\s*gb|\s*mb|\s*tb)?)\b", low)

    if any(k in low for k in ("alerta", "aviso", "prohib", "bloque", "censur", "peligro")):
        return (
            "system_alert",
            {"title": "AVISO DEL SISTEMA", "message": text[:110], "subtext": headline.upper()},
            "beep",
        )
    if any(k in low for k in ("memoria", "hex", "binario", "oculto", "kernel", "bajo nivel")):
        return (
            "hex_inspector",
            {"target_addr": "0040A1D0", "tag": "core", "finding": headline.upper()},
            "glitch",
        )
    if any(k in low for k in ("mapa", "país", "corea", "región", "global", "frontera", "radar")):
        return (
            "radar_map",
            {"region": headline.upper()},
            "scan",
        )
    if any(k in low for k in ("teléfono", "móvil", "celular", "app", "captura", "pantalla")):
        return (
            "phone_mockup",
            {"mode": "app_grid", "alert_text": headline.upper()},
            "sub_hit",
        )
    if any(k in low for k in ("sistema operativo", "escritorio", "monitor", "windows", "linux")):
        return (
            "desktop_monitor",
            {"os_name": headline.upper(), "subtitle": text[:70]},
            "whoosh",
        )
    if any(k in low for k in ("red", "nodo", "servidor", "tráfico", "ruta", "topología")):
        return (
            "network_graph",
            {"center_label": headline.upper()},
            "whoosh",
        )
    if any(k in low for k in ("código", "comando", "script", "función", "producción", "terminal")):
        return (
            "code_spotlight",
            {
                "language": "shell",
                "lines": [f"$ {w}" for w in text.split(",")[:4]],
                "highlight_line": 0,
            },
            "click",
        )
    if num_match:
        val_str = num_match.group(1).strip().upper()
        return (
            "stat_callout",
            {"primary_text": val_str, "secondary_text": headline, "note": text[:80]},
            "sub_hit",
        )

    cycle = [
        (
            "icon_spotlight",
            {"icon": "cpu", "label": headline, "sublabel": text[:90], "ring_progress": 0.82},
            "whoosh",
        ),
        (
            "xray_scanner",
            {"subject": headline.upper(), "footer_tag": "ANÁLISIS ACTIVO"},
            "scan",
        ),
        (
            "quote_focus",
            {"quote": text[:140], "author": f"Punto {index + 1:02d}"},
            "chime",
        ),
        (
            "timeline_steps",
            {
                "steps": [
                    {"tag": "01", "title": headline, "detail": text[:65], "highlight": True},
                ]
            },
            "pop",
        ),
        (
            "comparison_split",
            {
                "left": {"title": "Antes", "items": [headline]},
                "right": {"title": "Ahora", "items": [text[:60]], "highlight": True},
            },
            "whoosh",
        ),
    ]
    return cycle[index % len(cycle)]


def build_storyboard_from_transcript(
    transcript: dict[str, Any],
    title: str = "Explainer",
    aspect_ratio: str = "9:16",
    atmosphere: str = "sunburst",
) -> dict[str, Any]:
    """
    Genera automáticamente una estructura storyboard.json editable a partir de
    segmentos reales de Whisper, seleccionando componentes según el contenido semántico.
    """
    segments = transcript.get("segments", [])
    total_dur = float(transcript.get("duration", 0.0))
    if not segments:
        dur = total_dur if total_dur > 0 else 5.0
        return {
            "title": title,
            "duration": round(dur, 2),
            "aspect_ratio": aspect_ratio,
            "atmosphere": atmosphere if atmosphere in VALID_ATMOSPHERES else "sunburst",
            "scenes": [
                {
                    "id": "scene_1",
                    "start": 0.0,
                    "end": round(dur, 2),
                    "badge": "01 · Idea Central",
                    "headline": title,
                    "component": "quote_focus",
                    "transition": "snap",
                    "sfx": "sub_hit",
                    "props": {"quote": title, "author": "Narración"},
                }
            ],
        }

    chunks: list[dict[str, Any]] = []
    for seg in segments:
        s_start = float(seg.get("start", 0.0))
        s_end = float(seg.get("end", s_start + 2.0))
        s_text = str(seg.get("text", "")).strip()
        if not s_text:
            continue
        if not chunks or (chunks[-1]["end"] - chunks[-1]["start"] >= 3.0 and len(chunks) < 10):
            chunks.append({"start": s_start, "end": s_end, "texts": [s_text]})
        else:
            chunks[-1]["end"] = s_end
            chunks[-1]["texts"].append(s_text)

    if not chunks:
        chunks = [{"start": 0.0, "end": total_dur or 5.0, "texts": [title]}]

    chunks[0]["start"] = 0.0
    final_dur = max(total_dur, float(chunks[-1]["end"]))
    chunks[-1]["end"] = final_dur

    scenes: list[dict[str, Any]] = []
    trans_cycle = ["snap", "zoom_in", "slide_up"]
    accent_cycle = ["primary", "danger", "secondary", "warning", "tertiary"]

    for i, chunk in enumerate(chunks):
        c_start = round(float(chunk["start"]), 3)
        c_end = round(float(chunks[i + 1]["start"]) if i + 1 < len(chunks) else final_dur, 3)
        if c_end <= c_start:
            c_end = round(c_start + 1.0, 3)
        full_text = " ".join(chunk["texts"]).strip()
        words = full_text.split()
        headline = " ".join(words[:5]) + ("..." if len(words) > 5 else "")
        comp, props, sfx_name = _select_component_for_text(full_text, i)

        scenes.append(
            {
                "id": f"scene_{i + 1}",
                "start": c_start,
                "end": c_end,
                "badge": f"{i + 1:02d} · Escena",
                "headline": headline,
                "component": comp,
                "transition": trans_cycle[i % len(trans_cycle)],
                "sfx": sfx_name,
                "sfx_volume": 0.35,
                "accent": accent_cycle[i % len(accent_cycle)],
                "props": props,
            }
        )

    return {
        "title": title,
        "duration": round(final_dur, 3),
        "aspect_ratio": aspect_ratio,
        "atmosphere": atmosphere if atmosphere in VALID_ATMOSPHERES else "sunburst",
        "scenes": scenes,
    }


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
