"""Configuration du service catalog, lue dans l'environnement et le .env racine."""

from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

# Ce fichier est dans services/catalog/src/catalog_service/ : la racine du
# dépôt est 4 niveaux au-dessus. Le chemin ne dépend donc pas du dossier courant.
ROOT_ENV_FILE = Path(__file__).resolve().parents[4] / ".env"


class Settings(BaseSettings):
    """Paramètres du service. Une variable d'environnement prime sur le .env."""

    model_config = SettingsConfigDict(env_file=ROOT_ENV_FILE, extra="ignore")

    host: str = Field(default="127.0.0.1", validation_alias="CATALOG_HOST")
    port: int = Field(default=3001, validation_alias="CATALOG_PORT")
    # Le service tourne sur l'hôte : listener HOST de Kafka (localhost).
    kafka_brokers: str = Field(default="localhost:9092", validation_alias="KAFKA_BROKERS")
