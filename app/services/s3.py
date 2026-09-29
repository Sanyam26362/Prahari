import os
from pathlib import Path
from loguru import logger

class StorageService:
    def __init__(self, base_dir: str = "/workspace/storage"):
        self.base_dir = Path(base_dir)
        self.raw_dir = self.base_dir / "raw-forecasts"
        self.grids_dir = self.base_dir / "highres-grids"

    def initialize_storage(self):
        """Creates storage directories if they do not exist."""
        self.raw_dir.mkdir(parents=True, exist_ok=True)
        self.grids_dir.mkdir(parents=True, exist_ok=True)
        logger.info(f"Local storage initialized at: {self.base_dir}")

    def is_healthy(self) -> bool:
        return self.raw_dir.exists() and self.grids_dir.exists()

storage_service = StorageService()