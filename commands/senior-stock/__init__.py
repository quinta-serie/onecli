import click
import beautifultable
from common.config import settings_for_command
from common.cache import Cache
from common.filter import FilterEngine
from .senior_stock_api import SeniorStockAPI

DEFAULT_COLUMNS = ["cd_produto", "ean", "qt_disponivel"]
DEFAULT_ALL_COLUMNS = [
    "cd_empresa",
    "cd_produto",
    "ds_produto",
    "nu_lote",
    "qt_disponivel",
    "qt_reservado",
    "qt_reservado_digital",
    "ean",
    "tem_estoque",
    "ds_area_erp",
    "cd_area_armaz",
    "ds_area_armaz",
    "id_area_faturavel",
    "id_resultado_completo",
]


FILTER_HELP_TEXT = """
Filter expression, e.g. 'ean[eq]12345', 'ean[re]12345', can be used multiple times for multiple filters\n
Supported filter types:\n
- [re]: regex match, e.g. 'ean[re]12345' matches any ean containing '12345'\n
- [eq]: exact match, e.g. 'ean[eq]12345' matches only ean '12345'\n
- [ne]: not equals, e.g. 'ean[ne]12345' matches any ean except '12345'\n
- [lt]: less than, e.g. 'qt_disponivel[lt]10' matches any qt_disponivel less than 10\n
- [gt]: greater than, e.g. 'qt_disponivel[gt]10' matches any qt_disponivel greater than 10\n
- [lte]: less than or equals, e.g. 'qt_disponivel[lte]10' matches any qt_disponivel less than or equals 10\n
- [gte]: greater than or equals, e.g. 'qt_disponivel[gte]10' matches any qt_disponivel greater than or equals 10\n
- [contains]: contains, e.g. 'ds_produto[contains]abc' matches any ds_produto containing 'abc'\n
- [not_contains]: not contains, e.g. 'ds_produto[not_contains]abc' matches any ds_produto not containing 'abc'\n
- [starts_with]: starts with, e.g. 'ds_produto[starts_with]abc' matches any ds_produto starting with 'abc'\n
- [ends_with]: ends with, e.g. 'ds_produto[ends_with]abc' matches any ds_produto ending with 'abc'\n
_
"""

COLUMNS_HELP_TEXT = """
Columns to display, e.g. 'cd_produto,ean,qt_disponivel'. By default, only a few key columns are displayed.\n
Use --all-columns to display all available columns.
"""

ALL_COLUMNS_HELP_TEXT = """
Use --all-columns to display all available columns instead of specifying them with --columns.
All available columns:\n
- cd_empresa,\n
- cd_produto,\n
- ds_produto,\n
- nu_lote,\n
- qt_disponivel,\n
- qt_reservado,\n
- qt_reservado_digital,\n
- ean,\n
- tem_estoque,\n
- ds_area_erp,\n
- cd_area_armaz,\n
- ds_area_armaz,\n
- id_area_faturavel,\n
- id_resultado_completo
"""


@click.command(name="senior-stock")
@click.option("--filter","filter_expr", multiple=True, help=FILTER_HELP_TEXT)
@click.option("--columns", help=COLUMNS_HELP_TEXT)
@click.option("--no-cache", "no_cache_flag", is_flag=True, help="Bypass cache and fetch fresh data from the API")
@click.option("--all-columns", "all_columns_flag", is_flag=True, help=ALL_COLUMNS_HELP_TEXT)
@click.option("--quiet", "quiet_flag", is_flag=True, help="Only display the table without additional info")
def command(filter_expr, columns, no_cache_flag, all_columns_flag, quiet_flag):
    """Show the stock returned by the senior stock API."""
    settings = settings_for_command("senior_stock")
    cache = Cache("senior_stock")
    api_client = SeniorStockAPI(settings, cache)

    stock_data = api_client.get_all_stock(no_cache=no_cache_flag)

    columns_list = parse_columns(columns, all_columns_flag)
    filter_engine = FilterEngine(stock_data, filter_expr, columns_list)

    table = beautifultable.BeautifulTable(maxwidth=1600)
    table.columns.header = columns_list

    for row in filter_engine.apply_filters():
        table.rows.append(row)

    click.echo(table)
    if not quiet_flag:
        total_items = len(stock_data)
        total_matching_items = len(table.rows)
        click.echo(f"\nTotal items: {total_items}, Matching items: {total_matching_items}\n")


def parse_columns(columns, all_columns_flag):
    columns_list = columns.split(",") if columns else DEFAULT_COLUMNS

    if all_columns_flag:
        columns_list = DEFAULT_ALL_COLUMNS
    return columns_list
