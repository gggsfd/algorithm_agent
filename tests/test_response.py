import sys
sys.path.insert(0, 'd:/Mycode/算法_agent/algorithm_agent')

from app.schemas.response import SuccessResponse, ErrorResponse, ResponseCode


def test_success_response():
    print("=== 成功响应 ===")
    data = {"subtitles": [{"id": 1, "text": "测试"}], "total": 1}
    response = SuccessResponse(data=data, message="字幕解析成功")
    print(f"code: {response.code}")
    print(f"message: {response.message}")
    print(f"data: {response.data}")


def test_error_response():
    print("=== 错误响应 ===")
    response = ErrorResponse(message="SRT格式无效", code=ResponseCode.BAD_REQUEST)
    print(f"code: {response.code}")
    print(f"message: {response.message}")
    print(f"data: {response.data}")


def test_default_response():
    print("=== 默认成功响应 ===")
    response = SuccessResponse()
    print(f"code: {response.code}")
    print(f"message: {response.message}")
    print(f"data: {response.data}")


if __name__ == "__main__":
    test_success_response()
    print()
    test_error_response()
    print()
    test_default_response()
