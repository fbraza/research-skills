from pathlib import Path
from typing import cast

import dagster as dg
import pandas as pd


class DataFrameIOManager(dg.ConfigurableIOManager):
    """Persist DataFrames as parquet, with CSV sidecars for result tables."""

    base_dir: str = "data"

    def _output_parts(self, context: dg.OutputContext) -> list[str]:
        asset_key = context.asset_key
        assert asset_key is not None, "DataFrameIOManager requires an asset-backed output"
        return cast(list[str], list(asset_key.path))

    def _input_parts(self, context: dg.InputContext) -> list[str]:
        upstream_output = context.upstream_output
        assert upstream_output is not None, "DataFrameIOManager requires an upstream asset output"
        return cast(list[str], list(upstream_output.asset_key.path))

    def _output_path(self, context: dg.OutputContext) -> Path:
        parts = self._output_parts(context)
        layer, name_parts = parts[0], parts[1:]
        if layer == "results":
            return (
                Path(self.base_dir)
                / "results"
                / "tables"
                / Path(*name_parts).with_suffix(".parquet")
            )
        return Path(self.base_dir) / layer / Path(*name_parts).with_suffix(".parquet")

    def _input_path(self, context: dg.InputContext) -> Path:
        parts = self._input_parts(context)
        layer, name_parts = parts[0], parts[1:]
        if layer == "results":
            return (
                Path(self.base_dir)
                / "results"
                / "tables"
                / Path(*name_parts).with_suffix(".parquet")
            )
        return Path(self.base_dir) / layer / Path(*name_parts).with_suffix(".parquet")

    def handle_output(self, context: dg.OutputContext, obj: pd.DataFrame) -> None:
        path = self._output_path(context)
        path.parent.mkdir(parents=True, exist_ok=True)
        obj.to_parquet(path)

        if self._output_parts(context)[0] == "results":
            obj.to_csv(path.with_suffix(".csv"))

        context.add_output_metadata(
            {"path": str(path), "rows": len(obj), "columns": len(obj.columns)}
        )

    def load_input(self, context: dg.InputContext) -> pd.DataFrame:
        return pd.read_parquet(self._input_path(context))
