import json
from pathlib import Path
from datetime import datetime
from typing import Optional, List, Dict, Tuple

from app.schemas.file_saver import (
    FileInfo,
    CorrectionReport,
    CorrectionDetail,
    SaveResult,
)
from app.core.srt_file_saver_config import SRTFileSaverConfig


class SRTFileSaver:
    def __init__(self, config: Optional[SRTFileSaverConfig] = None):
        self.config = config or SRTFileSaverConfig()
        self._ensure_directories()

    def _ensure_directories(self) -> None:
        self.config.output_dir.mkdir(parents=True, exist_ok=True)
        if self.config.generate_report:
            self.config.report_dir.mkdir(parents=True, exist_ok=True)

    def _generate_filename(self, original_filename: str, rule: str = None) -> str:
        rule = rule or self.config.filename_rule
        base_name = original_filename.rsplit(".", 1)[0]
        extension = original_filename.rsplit(".", 1)[1] if "." in original_filename else "srt"

        if rule == "timestamp":
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            return f"{base_name}_{timestamp}.{extension}"
        elif rule == "corrected":
            return f"{base_name}_corrected.{extension}"
        elif rule == "version":
            version = self._get_next_version(base_name, extension)
            return f"{base_name}_v{version}.{extension}"
        else:
            return f"{base_name}_corrected.{extension}"

    def _get_next_version(self, base_name: str, extension: str) -> int:
        counter_file = self.config.output_dir / f".{base_name}_version"
        if counter_file.exists():
            with open(counter_file, "r") as f:
                version = int(f.read().strip()) + 1
        else:
            version = 1
        with open(counter_file, "w") as f:
            f.write(str(version))
        return version

    def _compare_subtitles(
        self,
        original_items: List[Dict],
        corrected_items: List[Dict]
    ) -> Tuple[int, List[CorrectionDetail]]:
        corrections = []
        corrected_count = 0

        orig_dict = {item["id"]: item["text"] for item in original_items}
        corr_dict = {item["id"]: item["text"] for item in corrected_items}

        for idx, (item_id, orig_text) in enumerate(orig_dict.items(), 1):
            corr_text = corr_dict.get(item_id, "")
            if orig_text != corr_text:
                corrections_made = self._extract_corrections(orig_text, corr_text)
                corrections.append(CorrectionDetail(
                    index=item_id,
                    original=orig_text,
                    corrected=corr_text,
                    corrections_made=corrections_made
                ))
                corrected_count += 1

        return corrected_count, corrections

    def _extract_corrections(self, original: str, corrected: str) -> List[str]:
        corrections = []
        orig_words = set(original.split())
        corr_words = set(corrected.split())

        added = corr_words - orig_words
        removed = orig_words - corr_words

        if added:
            corrections.append(f"添加: {' '.join(added)}")
        if removed:
            corrections.append(f"删除: {' '.join(removed)}")

        return corrections if corrections else ["文本修改"]

    def _generate_report(
        self,
        original_items: List[Dict],
        corrected_items: List[Dict],
        original_filename: str
    ) -> Tuple[CorrectionReport, Optional[str]]:
        total_items = len(original_items)
        corrected_items_count, corrections = self._compare_subtitles(
            original_items, corrected_items
        )
        unchanged_items = total_items - corrected_items_count
        correction_rate = (corrected_items_count / total_items * 100) if total_items > 0 else 0.0

        report = CorrectionReport(
            generated=self.config.generate_report,
            report_path=None,
            total_items=total_items,
            corrected_items=corrected_items_count,
            unchanged_items=unchanged_items,
            correction_rate=round(correction_rate, 2),
            corrections=corrections
        )

        if self.config.generate_report:
            report_path = self._save_report(report, original_filename)
            report.report_path = str(report_path)

        return report, report.report_path if self.config.generate_report else None

    def _save_report(self, report: CorrectionReport, original_filename: str) -> Path:
        base_name = original_filename.rsplit(".", 1)[0]
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        report_filename = f"{base_name}_report_{timestamp}.json"
        report_path = self.config.report_dir / report_filename

        with open(report_path, "w", encoding="utf-8") as f:
            json.dump(report.model_dump(), f, ensure_ascii=False, indent=2)

        return report_path

    def save(
        self,
        corrected_srt: str,
        original_filename: str,
        original_items: List[Dict],
        corrected_items: List[Dict]
    ) -> SaveResult:
        if not self.config.auto_save:
            return SaveResult(
                file_info=FileInfo(
                    saved=False,
                    file_path=None,
                    file_size=None,
                    original_filename=original_filename,
                    corrected_filename=""
                ),
                correction_report=None,
                success=True,
                warning="Auto-save is disabled"
            )

        try:
            self._ensure_directories()

            corrected_filename = self._generate_filename(original_filename)
            output_path = self.config.output_dir / corrected_filename

            with open(output_path, "w", encoding="utf-8") as f:
                f.write(corrected_srt)

            file_size = output_path.stat().st_size

            report, report_path = self._generate_report(
                original_items, corrected_items, original_filename
            )

            return SaveResult(
                file_info=FileInfo(
                    saved=True,
                    file_path=str(output_path),
                    file_size=file_size,
                    original_filename=original_filename,
                    corrected_filename=corrected_filename
                ),
                correction_report=report if self.config.generate_report else None,
                success=True
            )

        except Exception as e:
            return SaveResult(
                file_info=FileInfo(
                    saved=False,
                    file_path=None,
                    file_size=None,
                    original_filename=original_filename,
                    corrected_filename=""
                ),
                correction_report=None,
                success=False,
                warning=f"File save failed: {str(e)}"
            )
