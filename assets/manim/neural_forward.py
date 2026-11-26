"""Escena Manim generada por video-pipeline (preset: neural_network)."""

from manim import *

from core.manim_tools import (
    apply_pipeline_background,
    build_scene_header,
    get_pipeline_palette,
    is_vertical_aspect,
)


class NeuralForwardScene(Scene):
    def construct(self):
        p = get_pipeline_palette("dark_violet")
        vertical = is_vertical_aspect()
        apply_pipeline_background(self, p)

        header = build_scene_header(
            "Propagación en Red Neuronal", "Forward Pass · Activación", p, vertical=vertical
        )
        layer_sizes = [3, 5, 4, 2]
        layer_names = ["Entrada", "Oculta 1", "Oculta 2", "Salida"]
        layer_colors = [
            p["accent_primary"],
            p["accent_secondary"],
            p["accent_tertiary"],
            p["accent_warning"],
        ]

        x_spacing = 1.05 if vertical else 2.75
        y_spacing = 0.62 if vertical else 0.92
        radius = 0.16 if vertical else 0.26

        layers: list[VGroup] = []
        labels = VGroup()
        for li, (count, name, col) in enumerate(
            zip(layer_sizes, layer_names, layer_colors, strict=True)
        ):
            x_pos = (li - (len(layer_sizes) - 1) / 2.0) * x_spacing
            neurons = VGroup()
            for ni in range(count):
                y_pos = ((count - 1) / 2.0 - ni) * y_spacing - 0.25
                dot = Circle(
                    radius=radius,
                    stroke_color=col,
                    stroke_width=3.0,
                    fill_color=p["surface"],
                    fill_opacity=1.0,
                ).move_to(np.array([x_pos, y_pos, 0.0]))
                dot.set_z_index(3)
                neurons.add(dot)
            layers.append(neurons)
            lbl = Text(name, font=p["font_mono"], color=p["text_secondary"]).scale(
                0.20 if vertical else 0.30
            )
            lbl.move_to(np.array([x_pos, -2.65 if not vertical else -2.15, 0.0]))
            labels.add(lbl)

        edges_by_stage: list[VGroup] = []
        for li in range(len(layers) - 1):
            stage_edges = VGroup()
            for n_src in layers[li]:
                for n_dst in layers[li + 1]:
                    line = Line(
                        n_src.get_center(),
                        n_dst.get_center(),
                        stroke_color=p["cable_idle"],
                        stroke_width=1.4 if vertical else 1.8,
                        stroke_opacity=0.55,
                    )
                    stage_edges.add(line)
            edges_by_stage.append(stage_edges)

        self.play(FadeIn(header, shift=DOWN * 0.2), run_time=0.5)
        self.play(
            LaggedStart(*[Create(st) for st in edges_by_stage], lag_ratio=0.15),
            LaggedStart(*[FadeIn(ly, scale=0.8) for ly in layers], lag_ratio=0.15),
            FadeIn(labels),
            run_time=1.3,
        )

        # Forward pass con pulsos luminosos viajando entre capas
        for li, stage_edges in enumerate(edges_by_stage):
            col = layer_colors[li]
            pulses = [
                ShowPassingFlash(
                    edge.copy().set_stroke(color=col, width=3.5, opacity=1.0),
                    time_width=0.45,
                )
                for edge in stage_edges
            ]
            target_glow = [
                neuron.animate.set_fill(layer_colors[li + 1], opacity=0.85)
                for neuron in layers[li + 1]
            ]
            self.play(*pulses, run_time=0.85)
            self.play(*target_glow, run_time=0.35)

        self.play(Indicate(layers[-1][0], color=p["accent_warning"], scale_factor=1.35), run_time=0.7)
        self.wait(0.8)
