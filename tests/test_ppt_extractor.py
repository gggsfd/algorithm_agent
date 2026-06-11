import sys

import pytest

sys.path.insert(0, "d:/Mycode/算法_agent/algorithm_agent")

from app.domain_adapter.ppt_extractor import PPTExtractor


def test_ppt_extractor_extracts_text(tmp_path):
    pptx = pytest.importorskip("pptx")
    path = tmp_path / "course.pptx"
    prs = pptx.Presentation()
    slide = prs.slides.add_slide(prs.slide_layouts[5])
    box = slide.shapes.add_textbox(0, 0, 5000000, 1000000)
    box.text = "主定理\n递归树"
    prs.save(path)

    text = PPTExtractor().extract(str(path))

    assert "主定理" in text
    assert "递归树" in text
