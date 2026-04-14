from pathlib import Path
from typing import cast

import dagster as dg
from matplotlib.figure import Figure


class FigureIOManager(dg.ConfigurableIOManager):
    """Persist figure assets as both PNG and SVG."""

    base_dir: str = "data"
    dpi: int = 300

    def _output_parts(self, context: dg.OutputContext) -> list[str]:
        asset_key = context.asset_key
        assert asset_key is not None, "FigureIOManager requires an asset-backed output"
        return cast(list[str], list(asset_key.path))

    def _output_base_path(self, context: dg.OutputContext) -> Path:
        parts = self._output_parts(context)
        layer, name_parts = parts[0], parts[1:]
        if layer == "results":
            return Path(self.base_dir) / "results" / "figures" / Path(*name_parts)
        return Path(self.base_dir) / layer / Path(*name_parts)

    def handle_output(self, context: dg.OutputContext, obj: Figure) -> None:
        base_path = self._output_base_path(context)
        base_path.parent.mkdir(parents=True, exist_ok=True)

        png_path = base_path.with_suffix(".png")
        svg_path = base_path.with_suffix(".svg")
        obj.savefig(png_path, dpi=self.dpi, bbox_inches="tight")
        obj.savefig(svg_path, bbox_inches="tight")

        context.add_output_metadata({"png_path": str(png_path), "svg_path": str(svg_path)})

    def load_input(self, context: dg.InputContext) -> Figure:
        raise NotImplementedError("Figure assets are write-only in the default scaffold")
