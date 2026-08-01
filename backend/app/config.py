from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # MQTT
    mqtt_host: str = "mosquitto"
    mqtt_port: int = 8883
    mqtt_use_tls: bool = True
    mqtt_ca_cert: str = "/certs/ca.crt"
    mqtt_username: str = "backend"
    mqtt_password: str = "change-me-backend-pass"
    mqtt_topics: str = "factory/#"

    # InfluxDB
    influx_url: str = "http://influxdb:8086"
    influx_token: str = "demo-admin-token-change-me"
    influx_org: str = "iiot"
    influx_bucket: str = "factory_data"

    # Auth
    jwt_secret: str = "change-me-development-secret-key"
    jwt_algorithm: str = "HS256"
    jwt_expire_minutes: int = 60 * 8

    demo_username: str = "admin"
    demo_password: str = "admin123"

    rules_config_path: str = "/app/rules.yaml"

    cors_origins: str = "http://localhost:5173,http://localhost:3000"

    class Config:
        env_file = ".env"


settings = Settings()
