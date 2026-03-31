import sys
sys.path.insert(0, 'd:/Mycode/算法_agent/algorithm_agent')

from app.core.srt_parser import SRTParser
from app.core.exceptions import SRTParseError
import pytest

def test_srt_parser():
    parser = SRTParser()

    with open('d:/Mycode/算法_agent/algorithm_agent/tests/test_sample.srt', 'r', encoding='utf-8') as f:
        content = f.read()

    result = parser.parse(content)
    assert len(result) == 5
    assert result.items[0]["id"] == 1
    assert result.items[1]["text"] == "它的时间复杂度是 O(n log n)"
    assert result.items[4]["text"] == "动态鬼话是常用技巧"
    assert result.items[4]["_timestamp_end"] == "00:00:19,000"


def test_invalid_srt():
    parser = SRTParser()
    with pytest.raises(SRTParseError):
        parser.parse("这不是有效的SRT格式")

def test_parse_crlf_srt():
    parser = SRTParser()
    srt_content = (
        "1\r\n"
        "00:00:01,000 --> 00:00:02,000\r\n"
        "第一句\r\n"
        "\r\n"
        "2\r\n"
        "00:00:03,000 --> 00:00:04,000\r\n"
        "第二句\r\n"
        "\r\n"
        "3\r\n"
        "00:00:05,000 --> 00:00:06,000\r\n"
        "第三句\r\n"
    )
    result = parser.parse(srt_content)
    assert len(result) == 3
    assert [item["text"] for item in result.items] == ["第一句", "第二句", "第三句"]


if __name__ == "__main__":
    test_srt_parser()
    print()
    test_invalid_srt()
