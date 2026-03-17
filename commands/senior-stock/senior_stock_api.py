import requests
from common.cache import Cache

MAX_RETRIES = 3
CACHE_KEY_TOKEN = "senior_stock_token"
CACHE_KEY_DATA = "senior_stock_data"
CACHE_TOKEN_TTL_SECONDS = 1740  # 29 minutes
CACHE_DATA_TTL_SECONDS = 300    # 5 minutes

class SeniorStockAPI:
    """A simple client for the senior stock API."""

    def __init__(self, settings: dict, cache: Cache):
        self._validate_settings(settings)

        self.stock_url = settings.get("stock_url")
        self.auth_url = settings.get("auth_url")
        self.cd_empresa = settings.get("cd_empresa")
        self.cd_deposito = settings.get("cd_deposito")
        self.tp_consulta = settings.get("tp_consulta")
        self.id_produto_sem_estoque = settings.get("id_produto_sem_estoque")
        self.usuario = settings.get("usuario")
        self.senha = settings.get("senha")
        self.cache = cache
        self.cache_token_ttl_seconds = int(settings.get("cache_token_ttl_seconds", CACHE_TOKEN_TTL_SECONDS))
        self.cache_data_ttl_seconds = int(settings.get("cache_data_ttl_seconds", CACHE_DATA_TTL_SECONDS))

    def authenticate(self, force_refresh: bool = False) -> str:
        """Authenticate with the senior stock API and cache the token."""
        cached_token = self.cache.get(CACHE_KEY_TOKEN)
        if cached_token and not force_refresh:
            return cached_token

        response = requests.post(self.auth_url, json={
            "usuario": self.usuario,
            "senha": self.senha
        })

        response.raise_for_status()
        token = response.text

        self.cache.set(CACHE_KEY_TOKEN, token, ttl=self.cache_token_ttl_seconds)
        return token

    def get_all_stock(self, no_cache: bool = False, attempts: int = 1) -> dict:
        """Fetch stock data from the senior stock API."""
        cached_result = self.cache.get(CACHE_KEY_DATA)
        if cached_result and not no_cache:
            return cached_result

        try:
            token = self.authenticate()
            headers = {
                "Content-Type": "application/json",
                "Authorization": f"Bearer {token}",
            }
            body = {
                "cd_empresa": self.cd_empresa,
                "cd_deposito": self.cd_deposito,
                "tp_consulta": self.tp_consulta,
                "id_produto_sem_estoque": self.id_produto_sem_estoque
            }
            response = requests.post(self.stock_url, json=body, headers=headers)

            response.raise_for_status()

            result = response.json()

            self.cache.set(CACHE_KEY_DATA, result, ttl=self.cache_data_ttl_seconds)

            return result
        except requests.HTTPError as e:
            # unauthorized or token expired, try refreshing token and retrying the request
            if e.response.status_code == 401:
                attempts += 1
                self.authenticate(force_refresh=True)
                if attempts <= MAX_RETRIES:
                    return self.get_all_stock(no_cache=no_cache, attempts=attempts)
                else:
                    raise Exception("Maximum retry attempts reached while fetching stock data after token refresh.")
            else:
                raise

    def _validate_settings(self, settings: dict):
        if not isinstance(settings, dict):
            raise ValueError("Settings must be a dictionary.")
        if "stock_url" not in settings:
            raise ValueError("Missing required setting: stock_url")
        if "auth_url" not in settings:
            raise ValueError("Missing required setting: auth_url")
        if "cd_empresa" not in settings:
            raise ValueError("Missing required setting: cd_empresa")
        if "cd_deposito" not in settings:
            raise ValueError("Missing required setting: cd_deposito")
        if "tp_consulta" not in settings:
            raise ValueError("Missing required setting: tp_consulta")
        if "id_produto_sem_estoque" not in settings:
            raise ValueError("Missing required setting: id_produto_sem_estoque")
        if "usuario" not in settings:
            raise ValueError("Missing required setting: usuario")
        if "senha" not in settings:
            raise ValueError("Missing required setting: senha")
