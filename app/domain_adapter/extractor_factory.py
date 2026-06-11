from pathlib import Path

from app.domain_adapter.pdf_extractor import DocumentExtractor, PDFExtractor
from app.domain_adapter.ppt_extractor import PPTExtractor


class UnsupportedDocumentError(ValueError):
    pass


class DocumentExtractorFactory:
    def create(self, filename: str) -> DocumentExtractor:
        suffix = Path(filename).suffix.lower()
        if suffix == ".pdf":
            return PDFExtractor()
        if suffix == ".pptx":
            return PPTExtractor()
        if suffix == ".ppt":
            raise UnsupportedDocumentError("暂不支持 .ppt，请先转换为 .pptx")
        raise UnsupportedDocumentError(f"不支持的课程材料格式: {suffix or filename}")
