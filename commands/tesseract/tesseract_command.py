import click
import beautifultable
from common.config import settings_for_command
from requests.exceptions import HTTPError
from .tesseract_api import TesseractAPI


@click.command("tesseract", help="Fetch and display product data from Tesseract")
@click.argument("bu", type=click.Choice(["fisia", "centauro"]), required=True, metavar="BU")
@click.argument("model", type=str, required=True, metavar="MODEL")
@click.option("--show-only", "filter", type=click.Choice(["blocked", "unblocked", "all"]), default="all", help="Filter products by blocked status")
@click.option("--quiet", is_flag=True, help="Suppress output")
def command(bu, model, filter, quiet):
    settings = settings_for_command("tesseract")
    api = TesseractAPI(settings, bu)
    try:
        data = api.fetch_data(model)
    except HTTPError as e:
        if e.response.status_code == 404:
            click.echo(f"Model '{model}' not found in Tesseract for business unit '{bu}'.")
            return
        else:
            raise

    identifier = "EXTERNAL_ID" if bu == "fisia" else "EAN"
    table = beautifultable.BeautifulTable(maxwidth=1600)
    table.columns.header = ["SKU", identifier, "BLOCKED", "AVAILABLE", "TOTAL", "BLOCK_REASONS"]

    total_items = 0
    total_matching_items = 0

    mapped_data = data_mapping_by_bu(data, bu)

    for item in mapped_data:
        total_items += 1
        blocked = item.get("blocked", "") == "True"
        if filter == "blocked" and not blocked:
            continue
        if filter == "unblocked" and blocked:
            continue

        total_matching_items += 1

        table.rows.append([
            item.get("sku", ""),
            item.get("externalId", ""),
            item.get("blocked", ""),
            item.get("available", ""),
            item.get("total", ""),
            item.get("blockReasons", [])
        ])
    click.echo(table)

    if not quiet:
        click.echo(f"\nTotal items: {total_items}, Matching items: {total_matching_items}\n")

def data_mapping_by_bu(data, bu):
    if bu == "fisia":
        return _map_data_for_fisia(data)
    elif bu == "centauro":
        return _map_data_for_centauro(data)
    else:
        raise ValueError(f"Unsupported business unit: {bu}")

def _map_data_for_fisia(data):
    mapping = []
    for variation in data.get("modelVariations", []):
        for product in variation.get("products", []):
            mapping.append({
                "sku": product.get("sku", ""),
                "externalId": product.get("externalId", ""),
                "blocked": str(product.get("blocked", False)),
                "available": product.get("stock", {}).get("available", 0),
                "total": product.get("stock", {}).get("total", 0),
                "blockReasons": ", ".join(product.get("blockReasons", []))
            })
    return mapping

def _map_data_for_centauro(data):
    mapping = []

    model_colors = data.get("model_colors", {})
    keys = model_colors.keys()
    for key in keys:
        for variants in model_colors[key].get("variants", []):
            mapping.append({
                "sku": variants.get("sku", ""),
                "externalId": variants.get("ean", ""),
                "blocked": str(variants.get("blocked", False)),
                "available": variants.get("stock", {}).get("available", 0),
                "total": variants.get("stock", {}).get("total", 0),
                "blockReasons": ", ".join(variants.get("block_reason", []))
            })
    return mapping
