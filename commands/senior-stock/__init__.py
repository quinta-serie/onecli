import re
import click
import beautifultable
from common.config import settings_for_command
from common.cache import Cache
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


@click.command(name="senior-stock")
@click.option("--filter","filter_expr", multiple=True, help="Filter expression, e.g. 'ean:12345', 'ean[re]12345', can be used multiple times for multiple filters")
@click.option("--columns", help="Comma-separated list of columns to display, e.g. 'cd_produto,ean,qt_disponivel'")
@click.option("--no-cache", "no_cache_flag", is_flag=True, help="Bypass cache and fetch fresh data from the API")
@click.option("--all-columns", "all_columns_flag", is_flag=True, help="Display all available columns")
def command(filter_expr, columns, no_cache_flag, all_columns_flag):
    """Show the stock returned by the senior stock API."""
    settings = settings_for_command("senior_stock")
    cache = Cache("senior_stock")
    api_client = SeniorStockAPI(settings, cache)

    stock_data = api_client.get_all_stock(no_cache=no_cache_flag)

    columns_list = parse_columns(columns, all_columns_flag)
    filters = parse_filters(filter_expr)

    table = beautifultable.BeautifulTable()
    table.columns.header = columns_list

    for item in stock_data:
        keys = item.keys()
        if all(key in keys for key in filters.keys()):
            match = True
            for key, filter in filters.items():
                value = str(item.get(key, ""))
                if filter["type"] == "regex":
                    if not filter["value"].search(value):
                        match = False
                        break
                elif filter["type"] == "exact":
                    if value != filter["value"]:
                        match = False
                        break
            if match:
                row = [item.get(col, "") for col in columns_list]
                table.rows.append(row)

    click.echo(table)


def parse_filters(filter_expr):
    filters = {}
    for expr in filter_expr:
        if "[re]" in expr: # regex match filter
            key, value = expr.split("[re]", 1)
            filter = {
                "type": "regex",
                "value": re.compile(value.strip())
            }
            filters[key.strip()] = filter
        elif ":" in expr: # exact match filter
            key, value = expr.split(":", 1)
            filter = {
                "type": "exact",
                "value": value.strip()
            }
            filters[key.strip()] = filter
    return filters

def parse_columns(columns, all_columns_flag):
    columns_list = columns.split(",") if columns else DEFAULT_COLUMNS

    if all_columns_flag:
        columns_list = DEFAULT_ALL_COLUMNS
    return columns_list

