from openai import OpenAI

from app.domain_adapter.asr_mapping_generator import ASRMappingGenerator
from app.domain_adapter.candidate_asr_mapping_generator import CandidateASRMappingGenerator
from app.domain_adapter.course_profile_builder import CourseProfileBuilder
from app.domain_adapter.evidence_builder import DynamicEvidenceBuilder
from app.domain_adapter.extractor_factory import DocumentExtractorFactory
from app.domain_adapter.pdf_extractor import PDFExtractor
from app.domain_adapter.supplement_term_generator import SupplementTermGenerator
from app.domain_adapter.term_extractor import TermExtractor
from app.rag.pinyin_converter import PinyinConverter


class DomainAdapter:
    def __init__(self, api_key: str, base_url: str = "https://api.deepseek.com"):
        self.llm_client = OpenAI(api_key=api_key, base_url=base_url)
        self.extractor = PDFExtractor()
        self.extractor_factory = DocumentExtractorFactory()
        self.term_extractor = TermExtractor(self.llm_client)
        self.mapping_gen = ASRMappingGenerator(PinyinConverter(), llm_client=self.llm_client)
        self.course_profile_builder = CourseProfileBuilder(self.llm_client)
        self.supplement_term_generator = SupplementTermGenerator(self.llm_client)
        self.candidate_mapping_gen = CandidateASRMappingGenerator()
        self.evidence_builder = DynamicEvidenceBuilder(PinyinConverter())

    def adapt_from_pdf(self, pdf_path: str, model: str = "deepseek-chat") -> dict:
        text = self.extractor.extract(pdf_path)
        if not text.strip():
            raise ValueError(f"PDF 文本提取为空: {pdf_path}")

        terms = self.term_extractor.extract(text, model=model)
        term_names = [item["term"] for item in terms]
        asr_map = self.mapping_gen.generate(term_names)
        return self.evidence_builder.build(terms, asr_map)

    def adapt_from_document(
        self,
        path: str,
        filename: str | None = None,
        model: str = "deepseek-chat",
        enable_supplement: bool = True,
        supplement_limit: int = 30,
        existing_terms: dict | None = None,
        existing_candidates: dict | None = None,
        existing_profile: dict | None = None,
    ) -> dict:
        extractor = self.extractor_factory.create(filename or path)
        text = extractor.extract(path)
        if not text.strip():
            raise ValueError(f"课程材料文本提取为空: {filename or path}")

        terms = self.term_extractor.extract(text, model=model)
        term_names = [item["term"] for item in terms]
        asr_map = self.mapping_gen.generate(term_names, context=text)
        evidence = self.evidence_builder.build(terms, asr_map)
        course_profile = {}
        candidate_terms = []
        candidate_asr_mapping = {}
        if enable_supplement:
            course_profile = self.course_profile_builder.build(
                filename=filename or path,
                text=text,
                explicit_terms=terms,
                existing_profile=existing_profile,
                model=model,
            )
            candidate_terms = self.supplement_term_generator.generate(
                course_profile=course_profile,
                explicit_terms=terms,
                existing_terms=existing_terms,
                existing_candidates=existing_candidates,
                limit=supplement_limit,
                model=model,
            )
            candidate_asr_mapping = self.candidate_mapping_gen.generate(candidate_terms)
        evidence["course_profile"] = course_profile
        evidence["candidate_terms"] = candidate_terms
        evidence["candidate_asr_mapping"] = candidate_asr_mapping
        evidence["source_text_length"] = len(text)
        return evidence


__all__ = ["DomainAdapter"]
