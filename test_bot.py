import unittest
from unittest.mock import MagicMock, patch

import requests

from bot import (
    EndpointConfigurationError,
    InputValidationError,
    RegistrationRequestError,
    register_test,
    validate_endpoint,
    validate_phone,
    validate_registration_data,
)


class InputValidationTests(unittest.TestCase):
    def test_normalizes_vietnamese_local_phone(self):
        self.assertEqual(validate_phone("0912 345 678"), "84912345678")

    def test_rejects_missing_or_invalid_phone(self):
        for phone in ("", "abc", "123"):
            with self.subTest(phone=phone):
                with self.assertRaises(InputValidationError):
                    validate_phone(phone)

    def test_registration_data_must_be_nonempty_text_fields(self):
        self.assertEqual(validate_registration_data({"nickname": "tester"}), {"nickname": "tester"})
        for data in ({}, {"nickname": ""}, {"captcha": "not-allowed"}):
            with self.subTest(data=data):
                with self.assertRaises(InputValidationError):
                    validate_registration_data(data)

    def test_endpoint_must_be_configured_and_loopback(self):
        self.assertEqual(
            validate_endpoint("http://127.0.0.1:8080/register"),
            "http://127.0.0.1:8080/register",
        )
        for endpoint in (None, "", "https://example.com/register", "not a URL"):
            with self.subTest(endpoint=endpoint):
                with self.assertRaises(EndpointConfigurationError):
                    validate_endpoint(endpoint)


class RegisterRequestTests(unittest.TestCase):
    def setUp(self):
        self.session = MagicMock()
        self.session_context = MagicMock()
        self.session_context.__enter__.return_value = self.session
        self.session_context.__exit__.return_value = False
        self.session.post.return_value = MagicMock(
            status_code=200,
            json=MagicMock(return_value={"accepted": True}),
        )

    @patch("bot.requests.Session")
    def test_posts_explicit_inputs_and_returns_json(self, session_factory):
        session_factory.return_value = self.session_context

        result = register_test(
            "0912345678",
            {"nickname": "tester"},
            "manual-code",
            "http://localhost:8000/register",
        )

        self.assertEqual(result, {"accepted": True})
        self.session.post.assert_called_once()
        args, kwargs = self.session.post.call_args
        self.assertEqual(args[0], "http://localhost:8000/register")
        self.assertEqual(
            kwargs["files"],
            {
                "nickname": (None, "tester"),
                "mobile": (None, "84912345678"),
                "captcha": (None, "manual-code"),
            },
        )
        self.assertFalse(self.session.trust_env)
        self.assertFalse(kwargs["allow_redirects"])

    @patch("bot.requests.Session")
    def test_invalid_input_or_endpoint_never_sends_request(self, session_factory):
        session_factory.return_value = self.session_context

        cases = [
            ("", {"nickname": "tester"}, "code", "http://localhost/register"),
            ("0912345678", {}, "code", "http://localhost/register"),
            ("0912345678", {"nickname": "tester"}, "", "http://localhost/register"),
            ("0912345678", {"nickname": "tester"}, "code", None),
            ("0912345678", {"nickname": "tester"}, "code", "https://example.com"),
        ]
        for args in cases:
            with self.subTest(args=args), self.assertRaises(
                (InputValidationError, EndpointConfigurationError)
            ):
                register_test(*args)

        self.session.post.assert_not_called()

    @patch("bot.requests.Session")
    def test_timeout_has_clear_safe_error(self, session_factory):
        session_factory.return_value = self.session_context
        self.session.post.side_effect = requests.Timeout()

        with self.assertRaisesRegex(RegistrationRequestError, "hết thời gian chờ"):
            register_test(
                "0912345678",
                {"nickname": "tester"},
                "code",
                "http://localhost/register",
            )

    @patch("bot.requests.Session")
    def test_connection_error_has_clear_safe_error(self, session_factory):
        session_factory.return_value = self.session_context
        self.session.post.side_effect = requests.ConnectionError()

        with self.assertRaisesRegex(RegistrationRequestError, "Không thể kết nối"):
            register_test(
                "0912345678",
                {"nickname": "tester"},
                "code",
                "http://localhost/register",
            )

    @patch("bot.requests.Session")
    def test_http_and_non_json_responses_have_clear_errors(self, session_factory):
        session_factory.return_value = self.session_context

        self.session.post.return_value = MagicMock(status_code=503)
        with self.assertRaisesRegex(RegistrationRequestError, "HTTP 503"):
            register_test(
                "0912345678",
                {"nickname": "tester"},
                "code",
                "http://localhost/register",
            )

        self.session.post.return_value = MagicMock(
            status_code=200,
            json=MagicMock(side_effect=ValueError("invalid json")),
        )
        with self.assertRaisesRegex(RegistrationRequestError, "không phải JSON"):
            register_test(
                "0912345678",
                {"nickname": "tester"},
                "code",
                "http://localhost/register",
            )


if __name__ == "__main__":
    unittest.main()
