from dagster import Definitions, load_asset_checks_from_modules, load_assets_from_modules

from {{ cookiecutter.package_name }}.defs import checks
from {{ cookiecutter.package_name }}.defs.assets import analysis, processed, raw, results
from {{ cookiecutter.package_name }}.defs.resources import resources

asset_modules = [raw, processed, analysis, results]


defs = Definitions(
    assets=load_assets_from_modules(asset_modules),
    asset_checks=load_asset_checks_from_modules([checks]),
    resources=resources,
)
