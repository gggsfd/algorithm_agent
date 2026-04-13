from typing import Optional, List
from pydantic import BaseModel, Field


class FileInfo(BaseModel):
    saved: bool = Field(description="是否成功保存文件")
    file_path: Optional[str] = Field(None, description="保存的文件路径")
    file_size: Optional[int] = Field(None, description="文件大小（字节）")
    original_filename: str = Field(description="原始文件名")
    corrected_filename: str = Field(description="纠错后文件名")


class CorrectionDetail(BaseModel):
    index: int = Field(description="字幕序号")
    original: str = Field(description="原文")
    corrected: str = Field(description="纠正后")
    corrections_made: List[str] = Field(default_factory=list, description="具体做了哪些修改")


class CorrectionReport(BaseModel):
    generated: bool = Field(description="是否生成报告")
    report_path: Optional[str] = Field(None, description="报告文件路径")
    total_items: int = Field(0, description="字幕总数")
    corrected_items: int = Field(0, description="被纠正的字幕数")
    unchanged_items: int = Field(0, description="未变化的字幕数")
    correction_rate: float = Field(0.0, description="纠错率（百分比）")
    corrections: List[CorrectionDetail] = Field(default_factory=list, description="具体纠错详情")


class SaveResult(BaseModel):
    file_info: FileInfo
    correction_report: Optional[CorrectionReport] = None
    success: bool
    warning: Optional[str] = None
