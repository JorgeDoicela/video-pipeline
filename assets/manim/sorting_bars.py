"""Escena Manim generada por video-pipeline (preset: sorting_algorithm)."""

from manim import *

from core.manim_tools import (
    apply_pipeline_background,
    build_scene_header,
    get_pipeline_palette,
    is_vertical_aspect,
)


class SortingBarsScene(Scene):
    def construct(self):
        p = get_pipeline_palette("clean_light")
        vertical = is_vertical_aspect()
        apply_pipeline_background(self, p)

        header = build_scene_header(
            "Ordenamiento Paso a Paso", "Algoritmo · Comparación e Intercambio", p, vertical=vertical
        )

        values = [6, 2, 8, 4, 7, 3]
        bar_w = 0.42 if vertical else 0.92
        gap = 0.16 if vertical else 0.35
        scale_h = 0.32 if vertical else 0.46
        base_y = -2.15 if vertical else -2.25

        bars: list[VGroup] = []
        n = len(values)
        total_w = n * bar_w + (n - 1) * gap
        start_x = -total_w / 2.0 + bar_w / 2.0

        for idx, val in enumerate(values):
            h = val * scale_h
            rect = RoundedRectangle(
                corner_radius=0.08,
                width=bar_w,
                height=h,
                stroke_color=p["accent_primary"],
                stroke_width=2.5,
                fill_color=p["surface"],
                fill_opacity=0.95,
            )
            x = start_x + idx * (bar_w + gap)
            rect.move_to(np.array([x, base_y + h / 2.0, 0.0]))
            num = Text(str(val), font=p["font_mono"], color=p["text_primary"]).scale(
                0.28 if vertical else 0.44
            )
            num.next_to(rect, UP, buff=0.14)
            bars.append(VGroup(rect, num))

        self.play(FadeIn(header, shift=DOWN * 0.2), run_time=0.5)
        self.play(LaggedStart(*[FadeIn(b, shift=UP * 0.25) for b in bars], lag_ratio=0.1), run_time=0.8)

        # Bubble Sort real animado (ordenando los elementos en vivo)
        arr = list(values)
        for end in range(n - 1, 0, -1):
            for j in range(end):
                b1, b2 = bars[j], bars[j + 1]
                self.play(
                    b1[0].animate.set_stroke(p["accent_warning"], width=4),
                    b2[0].animate.set_stroke(p["accent_warning"], width=4),
                    run_time=0.18,
                )
                if arr[j] > arr[j + 1]:
                    dx = b2[0].get_center()[0] - b1[0].get_center()[0]
                    self.play(
                        b1.animate.shift(RIGHT * dx),
                        b2.animate.shift(LEFT * dx),
                        run_time=0.28,
                    )
                    arr[j], arr[j + 1] = arr[j + 1], arr[j]
                    bars[j], bars[j + 1] = bars[j + 1], bars[j]
                self.play(
                    bars[j][0].animate.set_stroke(p["accent_primary"], width=2.5),
                    bars[j + 1][0].animate.set_stroke(p["accent_primary"], width=2.5),
                    run_time=0.12,
                )
            self.play(
                bars[end][0].animate.set_stroke(p["accent_secondary"], width=3.5).set_fill(
                    p["accent_secondary"], opacity=0.22
                ),
                run_time=0.18,
            )

        self.play(
            bars[0][0].animate.set_stroke(p["accent_secondary"], width=3.5).set_fill(
                p["accent_secondary"], opacity=0.22
            ),
            run_time=0.25,
        )
        self.wait(0.8)
