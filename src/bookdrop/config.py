from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="BOOKDROP_")

    # Root of the library Stump reads: Author/[Series/]Title/ beneath it.
    books_root: Path = Path("/books")
    # Uploads awaiting confirmation, and the ledger.
    data_dir: Path = Path("/data")
    # The Adobe device key: device.xml, activation.xml and devicesalt.
    adept_dir: Path = Path("/adept")

    # Stump, asked to scan the library after each filing. The key needs only the
    # ScanLibrary permission. Unset, a book is still filed and the page says
    # Stump was not asked.
    stump_url: str = ""
    stump_api_key: str = ""
    stump_library_id: str = ""
