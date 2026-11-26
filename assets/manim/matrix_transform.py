"""Escena Manim generada por video-pipeline (preset: matrix_transform)."""

from manim import *

from core.manim_tools import (
    apply_pipeline_background,
    build_scene_header,
    get_pipeline_palette,
    is_vertical_aspect,
)


class MatrixTransformScene(Scene):
    def construct(self):
        p = get_pipeline_palette("paper_warm")
        vertical = is_vertical_aspect()
        apply_pipeline_background(self, p)

        header = build_scene_header(
            "Transformación Lineal 2D", "Matriz A = [[1.5, 0.8], [0.3, 1.3]]", p, vertical=vertical
        )
        header.set_z_index(10)
        header_mask = BackgroundRectangle(header, color=p["bg"], fill_opacity=0.92, buff=0.18)
        header_mask.set_z_index(9)

        bg_grid = NumberPlane(
            x_range=[-5, 5, 1] if vertical else [-7, 7, 1],
            y_range=[-5, 5, 1] if vertical else [-4, 4, 1],
            background_line_style={"stroke_color": p["cable_idle"], "stroke_opacity": 0.25},
            axis_config={"stroke_color": p["text_muted"], "stroke_opacity": 0.4},
        )
        grid = NumberPlane(
            x_range=[-4, 4, 1] if vertical else [-6, 6, 1],
            y_range=[-4, 4, 1] if vertical else [-4, 4, 1],
            background_line_style={"stroke_color": p["accent_primary"], "stroke_opacity": 0.48},
            axis_config={"stroke_color": p["text_primary"], "stroke_width": 2.2},
        )

        unit_sq = Polygon(
            ORIGIN,
            RIGHT,
            RIGHT + UP,
            UP,
            stroke_color=p["accent_warning"],
            stroke_width=2.5,
            fill_color=p["accent_warning"],
            fill_opacity=0.22,
        )
        i_hat = Arrow(ORIGIN, RIGHT, buff=0, color=p["accent_secondary"], stroke_width=6)
        j_hat = Arrow(ORIGIN, UP, buff=0, color=p["accent_tertiary"], stroke_width=6)
        v_vec = Arrow(ORIGIN, RIGHT * 1.0 + UP * 1.5, buff=0, color=p["accent_primary"], stroke_width=6)

        transform_group = VGroup(grid, unit_sq, i_hat, j_hat, v_vec)
        if vertical:
            bg_grid.scale(0.60).shift(DOWN * 0.25)
            transform_group.scale(0.60).shift(DOWN * 0.25)
        else:
            bg_grid.scale(0.84).shift(DOWN * 0.22)
            transform_group.scale(0.84).shift(DOWN * 0.22)

        det_label = Text(
            "det(A) = 1.5 * 1.3 - 0.8 * 0.3 = 1.71x área",
            font=p["font_mono"],
            color=p["text_primary"],
        ).scale(0.24 if vertical else 0.38)
        det_label.to_edge(DOWN, buff=0.42)
        det_label.set_z_index(10)
        det_mask = BackgroundRectangle(det_label, color=p["bg"], fill_opacity=0.92, buff=0.15)
        det_mask.set_z_index(9)

        matrix = [[1.5, 0.8], [0.3, 1.3]]

        self.play(
            FadeIn(bg_grid),
            Create(grid),
            FadeIn(header_mask),
            FadeIn(header, shift=DOWN * 0.2),
            run_time=0.9,
        )
        self.play(FadeIn(unit_sq), GrowArrow(i_hat), GrowArrow(j_hat), GrowArrow(v_vec), run_time=0.9)
        self.wait(0.4)
        self.play(ApplyMatrix(matrix, transform_group), run_time=2.2, rate_func=smooth)
        self.play(FadeIn(det_mask), FadeIn(det_label, shift=UP * 0.15), run_time=0.5)
        self.wait(1.0)
