import sys
import os
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from app.services.srt_file_saver import SRTFileSaver
from app.core.srt_file_saver_config import SRTFileSaverConfig


def test_srt_file_saver():
    config = SRTFileSaverConfig(
        output_dir=Path("./test_output"),
        filename_rule="timestamp",
        auto_save=True,
        generate_report=True,
        report_dir=Path("./test_reports")
    )

    saver = SRTFileSaver(config=config)

    original_items = [
        {"id": 1, "text": "Hello world"},
        {"id": 2, "text": "This is a test"},
        {"id": 3, "text": "Python is great"}
    ]

    corrected_items = [
        {"id": 1, "text": "Hello World"},
        {"id": 2, "text": "This is a test"},
        {"id": 3, "text": "Python is great"}
    ]

    corrected_srt = """1
00:00:00,000 --> 00:00:02,000
Hello World

2
00:00:02,000 --> 00:00:04,000
This is a test

3
00:00:04,000 --> 00:00:06,000
Python is great
"""

    result = saver.save(
        corrected_srt=corrected_srt,
        original_filename="test.srt",
        original_items=original_items,
        corrected_items=corrected_items
    )

    print(f"Success: {result.success}")
    print(f"File saved: {result.file_info.saved}")
    print(f"File path: {result.file_info.file_path}")
    print(f"Report generated: {result.correction_report.generated if result.correction_report else False}")

    if result.file_info.saved and result.correction_report:
        print(f"Total items: {result.correction_report.total_items}")
        print(f"Corrected items: {result.correction_report.corrected_items}")
        print(f"Correction rate: {result.correction_report.correction_rate}%")

    import shutil
    if Path("./test_output").exists():
        shutil.rmtree("./test_output")
    if Path("./test_reports").exists():
        shutil.rmtree("./test_reports")

    print("\nTest completed successfully!")


if __name__ == "__main__":
    test_srt_file_saver()
