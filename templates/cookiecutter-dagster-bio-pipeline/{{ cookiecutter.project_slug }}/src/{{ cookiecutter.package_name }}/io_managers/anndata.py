from pathlib import Path
from typing import cast

import anndata as ad
import dagster as dg


class AnnDataIOManager(dg.ConfigurableIOManager):
    """Persist AnnData checkpoints as .h5ad files."""

    base_dir: str = "data"

    def _output_parts(self, context: dg.OutputContext) -> list[str]:
        asset_key = context.asset_key
        assert asset_key is not None, "AnnDataIOManager requires an asset-backed output"
        return cast(list[str], list(asset_key.path))

    def _input_parts(self, context: dg.InputContext) -> list[str]:
        upstream_output = context.upstream_output
        assert upstream_output is not None, "AnnDataIOManager requires an upstream asset output"
        return cast(list[str], list(upstream_output.asset_key.path))

    def _output_path(self, context: dg.OutputContext) -> Path:
        parts = self._output_parts(context)
        layer, name_parts = parts[0], parts[1:]
        return Path(self.base_dir) / layer / Path(*name_parts).with_suffix(".h5ad")

    def _input_path(self, context: dg.InputContext) -> Path:
        parts = self._input_parts(context)
        layer, name_parts = parts[0], parts[1:]
        return Path(self.base_dir) / layer / Path(*name_parts).with_suffix(".h5ad")

    def handle_output(self, context: dg.OutputContext, obj: ad.AnnData) -> None:
        path = self._output_path(context)
        path.parent.mkdir(parents=True, exist_ok=True)
        obj.write_h5ad(path)
        context.add_output_metadata(
            {"path": str(path), "n_obs": obj.n_obs, "n_vars": obj.n_vars}
        )

    def load_input(self, context: dg.InputContext) -> ad.AnnData:
        return ad.read_h5ad(self._input_path(context))
