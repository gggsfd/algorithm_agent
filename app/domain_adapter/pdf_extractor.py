from abc import ABC, abstractmethod


class DocumentExtractor(ABC):
    @abstractmethod
    def extract(self, path: str) -> str:
        ...


class PDFExtractor(DocumentExtractor):
    def extract(self, pdf_path: str) -> str:
        try:
            import pdfplumber
        except ImportError as exc:
            raise RuntimeError("缺少 pdfplumber 依赖，请先安装 pdfplumber") from exc

        text_segments = []
        with pdfplumber.open(pdf_path) as pdf:
            for page in pdf.pages:
                text = page.extract_text()
                if not text:
                    continue
                lines = [
                    line.strip()
                    for line in text.splitlines()
                    if len(line.strip()) > 10 and not line.strip().isdigit()
                ]
                if lines:
                    text_segments.append("\n".join(lines))
        return "\n".join(text_segments)
