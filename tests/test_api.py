import httpx
import sys

def test_parse_api():
    print("=== 测试 /api/v1/parse 接口 ===")
    with open('d:/Mycode/算法_agent/algorithm_agent/tests/test_sample.srt', 'rb') as f:
        files = {'file': ('test_sample.srt', f, 'text/plain')}

        response = httpx.post(
            "http://localhost:8000/api/v1/parse",
            files=files,
            timeout=30.0
        )

    print(f"状态码: {response.status_code}")
    print(f"响应内容:")
    import json
    result = response.json()
    print(json.dumps(result, ensure_ascii=False, indent=2))


def test_correct_api():
    print("\n=== 测试 /api/v1/correct 接口 ===")
    with open('d:/Mycode/算法_agent/algorithm_agent/tests/test_sample.srt', 'rb') as f:
        files = {'file': ('test_sample.srt', f, 'text/plain')}

        response = httpx.post(
            "http://localhost:8000/api/v1/correct",
            files=files,
            timeout=30.0
        )

    print(f"状态码: {response.status_code}")
    print(f"响应内容:")
    import json
    result = response.json()
    print(json.dumps(result, ensure_ascii=False, indent=2))


def test_invalid_file():
    print("\n=== 测试无效文件类型 ===")
    files = {'file': ('test.txt', b'not an srt file', 'text/plain')}

    response = httpx.post(
        "http://localhost:8000/api/v1/parse",
        files=files,
        timeout=30.0
    )

    print(f"状态码: {response.status_code}")
    print(f"响应内容: {response.json()}")


if __name__ == "__main__":
    try:
        test_parse_api()
        test_correct_api()
        test_invalid_file()
    except httpx.ConnectError:
        print("❌ 无法连接到服务器，请确保服务已启动（python -m uvicorn app.main:app --host 0.0.0.0 --port 8000）")
        sys.exit(1)
