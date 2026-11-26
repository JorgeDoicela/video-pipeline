"""
Escena Manim semilla de demostración para video-pipeline.
Se sincroniza automáticamente con el tema activo del pipeline (dark_violet, paper_warm, clean_light)
y no requiere instalación de LaTeX.
"""

import math

from manim import *

from core.manim_tools import apply_pipeline_background, get_pipeline_palette, is_vertical_aspect


class DemoSineWaveScene(Scene):
    def construct(self):
        p = get_pipeline_palette("dark_violet")
        vertical = is_vertical_aspect()
        apply_pipeline_background(self, p)

        axes = Axes(
            x_range=[-4, 4, 1],
            y_range=[-2, 2, 1],
            x_length=3.8 if vertical else 9.0,
            y_length=3.6 if vertical else 4.5,
            axis_config={"color": p["text_muted"], "include_tip": True},
        )
        sine = axes.plot(lambda x: math.sin(x), color=p["accent_primary"], stroke_width=5)
        cosine = axes.plot(lambda x: math.cos(x), color=p["accent_secondary"], stroke_width=5)
        area = axes.get_area(sine, x_range=[0, math.pi], color=p["accent_primary"], opacity=0.25)

        title = Text("f(x) = sin(x) -> cos(x)", font=p["font_mono"], color=p["text_primary"]).scale(
            0.40 if vertical else 0.65
        )
        title.to_edge(UP, buff=0.6)

        self.play(Create(axes), FadeIn(title, shift=DOWN * 0.2), run_time=0.6)
        self.play(Create(sine), run_time=0.8)
        self.play(FadeIn(area), run_time=0.5)
        self.play(Transform(sine, cosine), FadeOut(area), run_time=0.8)
        self.wait(0.6)
