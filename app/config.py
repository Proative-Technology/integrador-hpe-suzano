from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    app_name: str = 'Topdesk x OpsRamp -- '
    root_path: str
    debug: bool
    log_file: str 
    conn_str: str
    topdesk_base_url: str
    topdesk_user: str
    topdesk_password: str
    opsramp_base_url: str
    opsramp_tenant: str
    opsramp_client_id: str
    opsramp_client_secret: str
    opsramp_api_key: str

    model_config = SettingsConfigDict(env_file='.env', env_file_encoding='utf-8', case_sensitivity=False)


settings = Settings(_env_file='.env', _env_file_encoding='utf-8')