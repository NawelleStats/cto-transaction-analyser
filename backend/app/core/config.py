from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

BASE_DIR = Path(__file__).resolve().parents[3]

DEFAULT_CSV_COLUMNS = (
    "Date opération",
    "Date valeur",
    "Opération",
    "Valeur",
    "Code ISIN",
    "Montant",
    "Quantité",
    "Cours",
)


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=(BASE_DIR / ".env", BASE_DIR / "backend" / ".env"),
        env_ignore_empty=True,
        extra="ignore",
        # ignored_types=(list,),
    )

    PROJECT_NAME: str = "Boursorama CTO Analyzer API"
    API_VERSION: str = "0.0.1"
    FRONTEND_HOST: str = "http://localhost:8501"
    BACKEND_HOST: str = "127.0.0.1"
    BACKEND_PORT: int = 8000
    CSV_REQUIRED_COLUMNS: str = ",".join(DEFAULT_CSV_COLUMNS)
    TRANSACTIONS_DATA_DIR: Path = BASE_DIR.parent / "data" / "data_transaction"

    @property
    def transactions_data_dir(self) -> Path:
        path = self.TRANSACTIONS_DATA_DIR.expanduser()
        return (path if path.is_absolute() else BASE_DIR / path).resolve()

    @property
    def csv_required_columns(self) -> list[str]:
        columns = [column.strip() for column in self.CSV_REQUIRED_COLUMNS.split(",") if column.strip()]
        missing = set(DEFAULT_CSV_COLUMNS) - set(columns)
        if missing:
            raise ValueError(
                "CSV_REQUIRED_COLUMNS doit contenir les colonnes métier obligatoires : "
                f"{sorted(missing)}"
            )
        return columns

settings = Settings()
