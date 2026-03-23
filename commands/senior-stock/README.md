# senior-stock

Fetches and displays stock data from the Senior stock API. Supports filtering, column selection, and transparent response caching.

---

## Settings

Configure the command by adding a `[senior_stock]` section to your `~/.oneclirc` file:

```ini
[senior_stock]
stock_url=<example>
auth_url=<example>
cd_empresa=1081
cd_deposito=1
tp_consulta=SaldoProdutosEnderecosFaturaveis
id_produto_sem_estoque=S
usuario=*****
senha=*****
# Optional cache TTL settings (in seconds)
cache_token_ttl_seconds=3600
cache_data_ttl_seconds=300
```

| Key | Description |
|---|---|
| `stock_url` | Base URL of the Senior stock API endpoint |
| `auth_url` | URL used to obtain an authentication token |
| `cd_empresa` | Company code |
| `cd_deposito` | Warehouse/deposit code |
| `tp_consulta` | Query type (e.g. `SaldoProdutosEnderecosFaturaveis`) |
| `id_produto_sem_estoque` | Whether to include out-of-stock products (`S` = yes, `N` = no) |
| `usuario` | API username |
| `senha` | API password |
| `cache_token_ttl_seconds` | (Optional) Time-to-live for the authentication token cache, in seconds (default: 3600) |
| `cache_data_ttl_seconds` | (Optional) Time-to-live for the stock data cache, in seconds (default: 300) |

### Overriding settings with environment variables

Any setting can be overridden at runtime using a `ONECLI_` prefixed environment variable. The key is the setting name uppercased:

```sh
export ONECLI_STOCK_URL=<example>
export ONECLI_AUTH_URL=<example>
export ONECLI_CD_EMPRESA=7010
export ONECLI_CD_DEPOSITO=2
export ONECLI_TP_CONSULTA=SaldoProdutosEnderecosFaturaveis
export ONECLI_ID_PRODUTO_SEM_ESTOQUE=N
export ONECLI_USUARIO=myuser
export ONECLI_SENHA=mypassword
export ONECLI_CACHE_TOKEN_TTL_SECONDS=3600
export ONECLI_CACHE_DATA_TTL_SECONDS=300
```

Environment variables take **higher precedence** than the `~/.oneclirc` file, making them suitable for CI pipelines and secrets management.

---

## Usage

> Before running, make sure the `[senior_stock]` section is configured in your `~/.oneclirc` file (see [Settings](#settings) above), or the equivalent `ONECLI_*` environment variables are exported.

### Basic usage — default columns

```sh
./onecli senior-stock
```

Displays `cd_produto`, `ean`, and `qt_disponivel` for all stock entries.

### Show all available columns

```sh
./onecli senior-stock --all-columns
```

Displays the full set of columns:
`cd_empresa`, `cd_produto`, `ds_produto`, `nu_lote`, `qt_disponivel`, `qt_reservado`, `qt_reservado_digital`, `ean`, `tem_estoque`, `ds_area_erp`, `cd_area_armaz`, `ds_area_armaz`, `id_area_faturavel`, `id_resultado_completo`.

### Select specific columns

```sh
./onecli senior-stock --columns cd_produto,ds_produto,qt_disponivel
```

### Filter by exact value

```sh
./onecli senior-stock --filter ean[eq]7891234567890
```

### Filter by regular expression

```sh
./onecli senior-stock --filter "ds_produto[re]^Camiseta"
```

### Combine multiple filters

Multiple `--filter` flags are applied as an AND condition — only rows matching all filters are shown:

```sh
./onecli senior-stock --filter cd_empresa[eq]1081 --filter "ds_produto[re]Tênis"
```

### Bypass the cache

```sh
./onecli senior-stock --no-cache
```

Forces a fresh API request, ignoring any previously cached response.

### Full example

```sh
./onecli senior-stock \
  --all-columns \
  --filter cd_empresa:1081 \
  --filter "ds_produto[re]^Camisa" \
  --no-cache
```

### Help

```sh
./onecli senior-stock --help
```
