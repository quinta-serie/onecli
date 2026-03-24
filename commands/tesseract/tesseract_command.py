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

    table = beautifultable.BeautifulTable(maxwidth=1600)
    table.columns.header = ["SKU", "EXTERNAL_ID", "BLOCKED", "AVAILABLE", "TOTAL", "BLOCK_REASONS"]

    total_items = 0
    total_matching_items = 0

    for variation in data.get("modelVariations", []):
        for product in variation.get("products", []):
            total_items += 1

            if filter == "blocked" and not product.get("blocked", False):
                continue
            if filter == "unblocked" and product.get("blocked", False):
                continue

            total_matching_items += 1

            table.rows.append([
                product.get("sku", ""),
                product.get("externalId", ""),
                str(product.get("blocked", "")),
                str(product.get("stock", {}).get("available", "")),
                str(product.get("stock", {}).get("total", "")),
                ", ".join(product.get("blockReasons", []))
            ])
    click.echo(table)

    if not quiet:
        click.echo(f"\nTotal items: {total_items}, Matching items: {total_matching_items}\n")
