"""Manual registration request helper for explicitly configured local test APIs."""

import getpass
import ipaddress
import json
import os
import re
import sys
from collections.abc import Mapping
from typing import Any
from urllib.parse import urlparse

import requests


class BotError(Exception):
    """Base class for safe, user-facing errors."""


class InputValidationError(BotError):
    """Raised when required input is missing or malformed."""


class EndpointConfigurationError(BotError):
    """Raised when no permitted local test endpoint is configured."""


class RegistrationRequestError(BotError):
    """Raised when the local test request fails or returns invalid data."""


def validate_phone(phone: str) -> str:
    """Validate a phone number and return digits, using 84 for a local 0 prefix."""
    if not isinstance(phone, str):
        raise InputValidationError("Số điện thoại phải là văn bản.")

    value = phone.strip()
    if not value or not re.fullmatch(r"\+?[0-9\s().-]+", value):
        raise InputValidationError("Số điện thoại không hợp lệ.")

    digits = re.sub(r"\D", "", value)
    if not 8 <= len(digits) <= 15:
        raise InputValidationError("Số điện thoại phải có từ 8 đến 15 chữ số.")
    if digits.startswith("0"):
        digits = "84" + digits[1:]
    return digits


def validate_registration_data(data: Mapping[str, Any]) -> dict[str, str]:
    """Validate user-supplied form fields without embedding personal data."""
    if not isinstance(data, Mapping) or not data:
        raise InputValidationError("Dữ liệu đăng ký phải là một đối tượng JSON không rỗng.")

    validated: dict[str, str] = {}
    reserved_fields = {"mobile", "captcha"}
    for key, value in data.items():
        if not isinstance(key, str) or not key.strip():
            raise InputValidationError("Tên trường đăng ký không được để trống.")
        normalized_key = key.strip()
        if normalized_key.lower() in reserved_fields:
            raise InputValidationError(
                f"Không nhập trường '{normalized_key}'; trường này được lấy từ đầu vào riêng."
            )
        if not isinstance(value, str) or not value.strip():
            raise InputValidationError(
                f"Giá trị của trường '{normalized_key}' phải là văn bản không rỗng."
            )
        validated[normalized_key] = value
    return validated


def validate_endpoint(endpoint: str | None) -> str:
    """Allow only an explicitly configured endpoint on the local machine."""
    if not isinstance(endpoint, str) or not endpoint.strip():
        raise EndpointConfigurationError(
            "Chưa cấu hình BOT_TEST_ENDPOINT cho dịch vụ kiểm thử cục bộ."
        )

    value = endpoint.strip()
    try:
        parsed = urlparse(value)
        hostname = parsed.hostname
        is_loopback = hostname == "localhost"
        if hostname and not is_loopback:
            try:
                is_loopback = ipaddress.ip_address(hostname).is_loopback
            except ValueError:
                is_loopback = False
    except ValueError:
        is_loopback = False
        parsed = None

    if (
        parsed is None
        or parsed.scheme not in {"http", "https"}
        or not parsed.hostname
        or not is_loopback
        or parsed.username
        or parsed.password
        or parsed.fragment
    ):
        raise EndpointConfigurationError(
            "BOT_TEST_ENDPOINT phải là URL HTTP(S) của localhost hoặc địa chỉ loopback."
        )
    return value


def register_test(
    phone: str,
    registration_data: Mapping[str, Any],
    verification_code: str,
    endpoint: str | None,
    *,
    timeout: float = 10,
) -> Any:
    """Submit manually provided form data to a configured local test endpoint."""
    normalized_phone = validate_phone(phone)
    validated_data = validate_registration_data(registration_data)
    if not isinstance(verification_code, str) or not verification_code.strip():
        raise InputValidationError("Mã xác minh không được để trống.")
    if len(verification_code.strip()) > 128:
        raise InputValidationError("Mã xác minh quá dài.")
    permitted_endpoint = validate_endpoint(endpoint)

    payload = {
        **validated_data,
        "mobile": normalized_phone,
        "captcha": verification_code.strip(),
    }
    try:
        with requests.Session() as session:
            session.trust_env = False
            response = session.post(
                permitted_endpoint,
                headers={"Accept": "application/json"},
                files={key: (None, value) for key, value in payload.items()},
                timeout=timeout,
                allow_redirects=False,
            )
    except requests.Timeout as exc:
        raise RegistrationRequestError("Dịch vụ kiểm thử hết thời gian chờ.") from exc
    except requests.RequestException as exc:
        raise RegistrationRequestError(
            "Không thể kết nối đến dịch vụ kiểm thử cục bộ."
        ) from exc

    status_code = response.status_code
    if not 200 <= status_code < 300:
        raise RegistrationRequestError(
            f"Dịch vụ kiểm thử trả về lỗi HTTP {status_code}."
        )
    try:
        return response.json()
    except (ValueError, requests.exceptions.JSONDecodeError) as exc:
        raise RegistrationRequestError(
            f"Dịch vụ kiểm thử trả về nội dung không phải JSON (HTTP {status_code})."
        ) from exc


def main() -> int:
    try:
        # Check configuration before prompting for personal or verification data.
        endpoint = validate_endpoint(os.environ.get("BOT_TEST_ENDPOINT"))
        phone = input("Số điện thoại: ")
        data_text = input("Dữ liệu đăng ký (đối tượng JSON): ")
        try:
            registration_data = json.loads(data_text)
        except json.JSONDecodeError as exc:
            raise InputValidationError("Dữ liệu đăng ký không phải JSON hợp lệ.") from exc
        verification_code = getpass.getpass("Nhập mã xác minh: ")

        register_test(phone, registration_data, verification_code, endpoint)
        print("Đã gửi request đến dịch vụ kiểm thử và nhận được phản hồi JSON.")
        return 0
    except (BotError, EOFError, KeyboardInterrupt) as exc:
        message = str(exc) if isinstance(exc, BotError) else "Đã hủy nhập dữ liệu."
        print(message, file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
