import os
import unittest
from contextlib import redirect_stderr, redirect_stdout
from io import StringIO
from unittest.mock import MagicMock, patch

import requests

from bot import (
    EndpointConfigurationError,
    InputValidationError,
    RegistrationRequestError,
    main,
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
    def test_posts_custom_phone_and_verification_code_fields(self, session_factory):
        session_factory.return_value = self.session_context

        result = register_test(
            "0912345678",
            {"nickname": "tester"},
            "manual-code",
            "http://localhost:8000/register",
            phone_field="phone_number",
            verification_code_field="verification_code",
        )

        self.assertEqual(result, {"accepted": True})
        _, kwargs = self.session.post.call_args
        self.assertEqual(
            kwargs["files"],
            {
                "nickname": (None, "tester"),
                "phone_number": (None, "84912345678"),
                "verification_code": (None, "manual-code"),
            },
        )

    @patch("bot.requests.Session")
    def test_custom_field_names_cannot_conflict_or_bypass_loopback_check(
        self, session_factory
    ):
        session_factory.return_value = self.session_context

        with self.assertRaises(InputValidationError):
            register_test(
                "0912345678",
                {"phone_number": "other"},
                "manual-code",
                "http://localhost/register",
                phone_field="phone_number",
                verification_code_field="verification_code",
            )
        with self.assertRaises(InputValidationError):
            register_test(
                "0912345678",
                {"nickname": "tester"},
                "manual-code",
                "http://localhost/register",
                phone_field="same",
                verification_code_field="same",
            )
        with self.assertRaises(EndpointConfigurationError):
            register_test(
                "0912345678",
                {"nickname": "tester"},
                "manual-code",
                "https://example.com/register",
                phone_field="phone_number",
                verification_code_field="verification_code",
            )

        self.session.post.assert_not_called()

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


class CommandLineTests(unittest.TestCase):
    def setUp(self):
        self.session = MagicMock()
        self.session_context = MagicMock()
        self.session_context.__enter__.return_value = self.session
        self.session_context.__exit__.return_value = False
        self.session.post.return_value = MagicMock(
            status_code=200,
            json=MagicMock(return_value={"accepted": True}),
        )

    def test_cli_uses_manual_inputs_and_configured_local_endpoint(self):
        endpoint = "http://127.0.0.1:8080/register"
        with (
            patch.dict(os.environ, {"BOT_TEST_ENDPOINT": endpoint}, clear=True),
            patch(
                "builtins.input",
                side_effect=["0912345678", '{"nickname": "tester"}'],
            ) as input_mock,
            patch("bot.getpass.getpass", return_value="manual-code") as getpass_mock,
            patch("bot.requests.Session", return_value=self.session_context),
            redirect_stdout(StringIO()),
            redirect_stderr(StringIO()),
        ):
            result = main()

        self.assertEqual(result, 0)
        self.assertEqual(
            [call.args[0] for call in input_mock.call_args_list],
            ["Số điện thoại: ", "Dữ liệu đăng ký (đối tượng JSON): "],
        )
        getpass_mock.assert_called_once_with("Nhập mã xác minh: ")
        self.session.post.assert_called_once()
        args, kwargs = self.session.post.call_args
        self.assertEqual(args[0], endpoint)
        self.assertEqual(
            kwargs["files"],
            {
                "nickname": (None, "tester"),
                "mobile": (None, "84912345678"),
                "captcha": (None, "manual-code"),
            },
        )

    def test_cli_uses_custom_field_names_from_environment(self):
        endpoint = "http://127.0.0.1:8080/register"
        environment = {
            "BOT_TEST_ENDPOINT": endpoint,
            "BOT_TEST_PHONE_FIELD": "phone_number",
            "BOT_TEST_CODE_FIELD": "verification_code",
        }
        with (
            patch.dict(os.environ, environment, clear=True),
            patch(
                "builtins.input",
                side_effect=["0912345678", '{"nickname": "tester"}'],
            ),
            patch("bot.getpass.getpass", return_value="manual-code"),
            patch("bot.requests.Session", return_value=self.session_context),
            redirect_stdout(StringIO()),
            redirect_stderr(StringIO()),
        ):
            result = main()

        self.assertEqual(result, 0)
        _, kwargs = self.session.post.call_args
        self.assertEqual(
            kwargs["files"],
            {
                "nickname": (None, "tester"),
                "phone_number": (None, "84912345678"),
                "verification_code": (None, "manual-code"),
            },
        )

    def test_missing_or_disallowed_endpoint_exits_before_input_or_request(self):
        cases = [
            ("missing endpoint", {}),
            (
                "non-loopback endpoint",
                {"BOT_TEST_ENDPOINT": "https://example.com/register"},
            ),
        ]
        for name, environment in cases:
            with self.subTest(name=name):
                with (
                    patch.dict(os.environ, environment, clear=True),
                    patch("builtins.input") as input_mock,
                    patch("bot.getpass.getpass") as getpass_mock,
                    patch("bot.requests.Session") as session_factory,
                    redirect_stdout(StringIO()),
                    redirect_stderr(StringIO()),
                ):
                    result = main()

                self.assertEqual(result, 1)
                input_mock.assert_not_called()
                getpass_mock.assert_not_called()
                session_factory.assert_not_called()


if __name__ == "__main__":
    unittest.main()
