import os
from pathlib import Path
from pydantic_settings import BaseSettings


class SRTFileSaverConfig(BaseSettings):
    output_dir: Path = Path("./output")
    filename_rule: str = "timestamp"
    auto_save: bool = True
    generate_report: bool = True
    report_dir: Path = Path("./reports")

    class Config:
        env_prefix = "SRT_"
        case_sensitive = False

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.output_dir = Path(self.output_dir)
        self.report_dir = Path(self.report_dir)

    def ensure_directories(self) -> None:
        self.output_dir.mkdir(parents=True, exist_ok=True)
        if self.generate_report:
            self.report_dir.mkdir(parents=True, exist_ok=True)
