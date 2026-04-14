from dagster import PipesSubprocessClient

from {{ cookiecutter.package_name }}.io_managers.anndata import AnnDataIOManager
from {{ cookiecutter.package_name }}.io_managers.dataframe import DataFrameIOManager
from {{ cookiecutter.package_name }}.io_managers.figure import FigureIOManager

resources = {
    "anndata_io": AnnDataIOManager(base_dir="data"),
    "dataframe_io": DataFrameIOManager(base_dir="data"),
    "figure_io": FigureIOManager(base_dir="data", dpi=300),
    "pipes_subprocess_client": PipesSubprocessClient(),
}
