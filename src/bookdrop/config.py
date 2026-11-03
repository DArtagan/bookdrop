from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="BOOKDROP_")

    # True unless the deployment says otherwise: a missing or misspelt variable
    # must leave the library untouched, never start writing into it.
    dry_run: bool = True

    # Root of the library Stump reads: Author/[Series/]Title/ beneath it.
    books_root: Path = Path("/books")
    # Uploads awaiting confirmation, and the ledger.
    data_dir: Path = Path("/data")
