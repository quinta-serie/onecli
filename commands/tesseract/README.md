# tesseract

Fetches and displays product variation data from the Tesseract API. Supports filtering by blocked status and quiet output mode.

---

## Settings

Configure the command by adding a `[tesseract]` section to your `~/.oneclirc` file:

```ini
[tesseract]
tesseract_fisia_url=<url-example>
tesseract_centauro_url=<url-example>
```

| Key | Description |
|---|---|
| `tesseract_fisia_url` | Tesseract API base URL for the Fisia business unit |
| `tesseract_centauro_url` | Tesseract API base URL for the Centauro business unit |

At least one of the two URL keys must be present. You only need to configure the business units you intend to use.

### Overriding settings with environment variables

Any setting can be overridden at runtime using a `ONECLI_` prefixed environment variable. The key is the setting name uppercased:

```sh
export ONECLI_TESSERACT_FISIA_URL=<url-example>
export ONECLI_TESSERACT_CENTAURO_URL=<url-example>
```

Environment variables take **higher precedence** than the `~/.oneclirc` file, making them suitable for CI pipelines and environment-specific overrides.

---

## Usage

> Before running, make sure the `[tesseract]` section is configured in your `~/.oneclirc` file (see [Settings](#settings) above), or the equivalent `ONECLI_*` environment variables are exported.

### Command syntax

```
./onecli tesseract BU MODEL [OPTIONS]
```

| Argument | Values | Description |
|---|---|---|
| `BU` | `fisia`, `centauro` | Business unit to query |
| `MODEL` | 6-digit numeric string | Model identifier (e.g. `097802`) |

### Basic usage

```sh
./onecli tesseract fisia 097802
```

Fetches all product variations for model `097802` in the Fisia business unit and displays a table with SKU, external ID, blocked status, available stock, total stock and block reasons.

### Query a different business unit

```sh
./onecli tesseract centauro 097802
```

### Filter by blocked status

```sh
# Show only blocked products
./onecli tesseract fisia 097802 --show-only blocked

# Show only unblocked products
./onecli tesseract fisia 097802 --show-only unblocked

# Show all products (default)
./onecli tesseract fisia 097802 --show-only all
```

### Suppress the summary line

```sh
./onecli tesseract fisia 097802 --quiet
```

By default the command prints a summary line at the end:

```
Total items: 10, Matching items: 4
```

The `--quiet` flag suppresses this line — useful when piping or scripting.

### Handle a model not found

If the model does not exist in Tesseract for the given business unit, the command prints a human-readable message and exits cleanly (no stack trace):

```
Model '097802' not found in Tesseract for business unit 'fisia'.
```

### Full example

```sh
./onecli tesseract fisia 097802 --show-only unblocked --quiet
```

### Help

```sh
./onecli tesseract --help
```

### Output columns

| Column | Description |
|---|---|
| `SKU` | Product SKU |
| `EXTERNAL_ID` | External identifier |
| `BLOCKED` | Whether the product is blocked (`True` / `False`) |
| `AVAILABLE` | Available stock quantity |
| `TOTAL` | Total stock quantity |
| `BLOCK_REASONS` | Comma-separated list of block reasons (empty if unblocked) |
