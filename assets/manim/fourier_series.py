"""Escena Manim generada por video-pipeline (preset: fourier_epicycles)."""

import math

from manim import *

from core.manim_tools import (
    apply_pipeline_background,
    build_scene_header,
    get_pipeline_palette,
    is_vertical_aspect,
)


class FourierSeriesScene(Scene):
    def construct(self):
        p = get_pipeline_palette("dark_violet")
        vertical = is_vertical_aspect()
        apply_pipeline_background(self, p)

        header = build_scene_header(
            "Síntesis de Fourier", "Epiciclos · 4 Armónicos", p, vertical=vertical
        )
        harmonics = [1, 3, 5, 7]
        base_r = 0.85 if vertical else 1.45
        origin = np.array([0.0, 1.35, 0.0]) if vertical else np.array([-3.3, -0.35, 0.0])
        wave_start_x = -1.65 if vertical else -0.45
        wave_len = 3.3 if vertical else 6.0
        wave_y_base = -1.65 if vertical else -0.35

        phase = ValueTracker(0.0)
        colors = [
            p["accent_primary"],
            p["accent_secondary"],
            p["accent_tertiary"],
            p["accent_warning"],
        ]

        def epicycle_points(t: float) -> list[np.ndarray]:
            pts = [origin.copy()]
            cur = origin.copy()
            for n in harmonics:
                r = base_r * (4.0 / (n * math.pi)) * 0.55
                angle = n * t
                cur = cur + np.array([r * math.cos(angle), r * math.sin(angle), 0.0])
                pts.append(cur.copy())
            return pts

        epicycles = always_redraw(
            lambda: VGroup(
                *[
                    VGroup(
                        Circle(
                            radius=base_r * (4.0 / (n * math.pi)) * 0.55,
                            color=colors[i % len(colors)],
                            stroke_width=2.0 if i == 0 else 1.5,
                            stroke_opacity=0.65,
                        ).move_to(epicycle_points(phase.get_value())[i]),
                        Line(
                            epicycle_points(phase.get_value())[i],
                            epicycle_points(phase.get_value())[i + 1],
                            color=colors[i % len(colors)],
                            stroke_width=3.0 if i == 0 else 2.2,
                        ),
                    )
                    for i, n in enumerate(harmonics)
                ]
            )
        )

        tip_dot = always_redraw(
            lambda: Dot(
                epicycle_points(phase.get_value())[-1],
                radius=0.07,
                color=p["accent_secondary"],
            )
        )

        def build_wave() -> VMobject:
            t_now = phase.get_value()
            samples = 140
            pts = []
            for k in range(samples):
                u = k / (samples - 1)
                tau = t_now - u * 2.0 * math.pi
                y_sum = sum(
                    base_r * (4.0 / (n * math.pi)) * 0.55 * math.sin(n * tau) for n in harmonics
                )
                x_pos = wave_start_x + u * wave_len
                pts.append(np.array([x_pos, wave_y_base + y_sum, 0.0]))
            mob = VMobject(color=p["accent_primary"], stroke_width=4.0)
            mob.set_points_smoothly(pts)
            return mob

        wave = always_redraw(build_wave)

        connector = always_redraw(
            lambda: DashedLine(
                epicycle_points(phase.get_value())[-1],
                np.array(
                    [
                        wave_start_x,
                        wave_y_base
                        + sum(
                            base_r
                            * (4.0 / (n * math.pi))
                            * 0.55
                            * math.sin(n * phase.get_value())
                            for n in harmonics
                        ),
                        0.0,
                    ]
                ),
                color=p["text_muted"],
                stroke_width=1.8,
                dash_length=0.1,
            )
        )

        baseline = Line(
            np.array([wave_start_x, wave_y_base, 0.0]),
            np.array([wave_start_x + wave_len, wave_y_base, 0.0]),
            color=p["cable_idle"],
            stroke_width=1.5,
        )

        caption = Text(
            "f(t) = (4/pi) * [sin(t) + sin(3t)/3 + sin(5t)/5 + sin(7t)/7]",
            font=p["font_mono"],
            color=p["text_secondary"],
        ).scale(0.22 if vertical else 0.36)
        caption.to_edge(DOWN, buff=0.45)

        self.play(FadeIn(header, shift=DOWN * 0.2), Create(baseline), run_time=0.6)
        self.add(epicycles, wave, connector, tip_dot)
        self.play(FadeIn(caption), run_time=0.4)
        self.play(phase.animate.set_value(4.0 * math.pi), run_time=5.5, rate_func=linear)
        self.wait(0.5)
