import sys
from fastapi.testclient import TestClient

sys.path.insert(0, 'd:/Mycode/算法_agent/algorithm_agent')

from app.main import app


client = TestClient(app)
SAMPLE_FILE_PATH = 'd:/Mycode/算法_agent/algorithm_agent/tests/test_sample.srt'


def test_correct_api_with_rule_mode():
    with open(SAMPLE_FILE_PATH, 'rb') as f:
        files = {'file': ('test_sample.srt', f, 'text/plain')}
        data = {
            "domain": "algorithm",
            "correction_mode": "rule",
        }
        response = client.post(
            "/api/v1/correct",
            files=files,
            data=data
        )
    result = response.json()
    assert response.status_code == 200
    assert result["code"] == 200
    assert result["data"]["correction_mode"] == "rule"
    assert result["data"]["effective_mode"] == "rule"
    assert result["data"]["degraded"] is False

def test_correct_api_with_invalid_mode():
    with open(SAMPLE_FILE_PATH, 'rb') as f:
        files = {'file': ('test_sample.srt', f, 'text/plain')}
        data = {
            "domain": "algorithm",
            "correction_mode": "invalid_mode",
        }
        response = client.post(
            "/api/v1/correct",
            files=files,
            data=data
        )
    assert response.status_code == 400
    assert "Unsupported correction mode" in response.json()["detail"]


def test_parse_api_invalid_file():
    files = {'file': ('test.txt', b'not an srt file', 'text/plain')}

    response = client.post(
        "/api/v1/parse",
        files=files,
    )
    assert response.status_code == 400


def test_correct_api_with_hybrid_auto_mode():
    with open(SAMPLE_FILE_PATH, 'rb') as f:
        files = {'file': ('test_sample.srt', f, 'text/plain')}
        data = {
            "domain": "algorithm",
            "correction_mode": "hybrid_auto",
        }
        response = client.post(
            "/api/v1/correct",
            files=files,
            data=data
        )
    result = response.json()
    assert response.status_code == 200
    assert result["code"] == 200
    assert result["data"]["correction_mode"] == "hybrid_auto"


if __name__ == "__main__":
    test_correct_api_with_rule_mode()
    test_correct_api_with_invalid_mode()
    test_parse_api_invalid_file()
    test_correct_api_with_hybrid_auto_mode()
