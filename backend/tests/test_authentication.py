import base64
import json
import ssl
import time
import unittest
from urllib.error import HTTPError, URLError
from unittest.mock import patch

from fastapi import HTTPException

from backend.services.authentication import _verify_token
from backend.services import supabase_store


def _token(payload: dict) -> str:
    encoded = base64.urlsafe_b64encode(json.dumps(payload).encode()).decode().rstrip("=")
    return f"header.{encoded}.signature"


class AuthenticationTests(unittest.TestCase):
    def test_validates_supabase_user_and_reads_password_auth_time(self):
        timestamp = int(time.time())
        token = _token({
            "sub": "user-id",
            "amr": [{"method": "password", "timestamp": timestamp}],
        })
        response_body = json.dumps({
            "id": "user-id",
            "email": "student@example.com",
            "email_confirmed_at": "2026-10-01T00:00:00Z",
        }).encode()
        with patch("backend.services.authentication.urlopen") as urlopen:
            urlopen.return_value.__enter__.return_value.read.return_value = response_body
            user = _verify_token(token, "https://example.supabase.co", "anon-key")

        self.assertEqual(user["id"], "user-id")
        self.assertEqual(user["auth_time"], timestamp)

    def test_rejects_an_unverified_email(self):
        token = _token({"sub": "user-id", "amr": []})
        response_body = json.dumps({
            "id": "user-id",
            "email": "student@example.com",
        }).encode()
        with patch("backend.services.authentication.urlopen") as urlopen:
            urlopen.return_value.__enter__.return_value.read.return_value = response_body
            with self.assertRaises(HTTPException) as error:
                _verify_token(token, "https://example.supabase.co", "anon-key")

        self.assertEqual(error.exception.status_code, 403)

    def test_rejects_token_with_different_user_subject(self):
        token = _token({"sub": "another-user", "amr": []})
        response_body = json.dumps({
            "id": "user-id",
            "email": "student@example.com",
            "email_confirmed_at": "2026-10-01T00:00:00Z",
        }).encode()
        with patch("backend.services.authentication.urlopen") as urlopen:
            urlopen.return_value.__enter__.return_value.read.return_value = response_body
            with self.assertRaises(HTTPException) as error:
                _verify_token(token, "https://example.supabase.co", "anon-key")

        self.assertEqual(error.exception.status_code, 401)

    def test_retries_supabase_user_lookup_after_tls_handshake_failure(self):
        timestamp = int(time.time())
        token = _token({
            "sub": "user-id",
            "amr": [{"method": "password", "timestamp": timestamp}],
        })
        response_body = json.dumps({
            "id": "user-id",
            "email": "student@example.com",
            "email_confirmed_at": "2026-10-01T00:00:00Z",
        }).encode()
        tls_error = URLError(ssl.SSLError(1, "record layer failure"))

        with (
            patch("backend.services.authentication.urlopen") as urlopen,
            patch("backend.services.authentication.time.sleep"),
        ):
            urlopen.side_effect = [
                tls_error,
                unittest.mock.MagicMock(
                    __enter__=unittest.mock.Mock(return_value=unittest.mock.MagicMock(
                        read=unittest.mock.Mock(return_value=response_body),
                    )),
                ),
            ]
            user = _verify_token(token, "https://example.supabase.co", "anon-key")

        self.assertEqual(user["id"], "user-id")
        self.assertEqual(urlopen.call_count, 2)

    def test_retries_supabase_user_lookup_after_request_timeout(self):
        token = _token({"sub": "user-id", "amr": []})
        response_body = json.dumps({
            "id": "user-id",
            "email": "student@example.com",
            "email_confirmed_at": "2026-10-01T00:00:00Z",
        }).encode()
        success = unittest.mock.MagicMock()
        success.__enter__.return_value.read.return_value = response_body

        with (
            patch(
                "backend.services.authentication.urlopen",
                side_effect=[URLError(TimeoutError()), success],
            ) as urlopen,
            patch("backend.services.authentication.time.sleep"),
        ):
            user = _verify_token(token, "https://example.supabase.co", "anon-key")

        self.assertEqual(user["id"], "user-id")
        self.assertEqual(urlopen.call_count, 2)
        self.assertEqual(urlopen.call_args.kwargs["timeout"], 15)

    def test_returns_actionable_error_after_repeated_supabase_request_timeouts(self):
        token = _token({"sub": "user-id", "amr": []})
        with (
            patch(
                "backend.services.authentication.urlopen",
                side_effect=URLError(TimeoutError()),
            ) as urlopen,
            patch("backend.services.authentication.time.sleep"),
        ):
            with self.assertRaises(HTTPException) as error:
                _verify_token(token, "https://example.supabase.co", "anon-key")

        self.assertEqual(error.exception.status_code, 502)
        self.assertIn("timed out", error.exception.detail)
        self.assertEqual(urlopen.call_count, 3)

    def test_rejects_authentication_after_repeated_tls_failures(self):
        token = _token({"sub": "user-id", "amr": []})
        tls_error = URLError(ssl.SSLError(1, "record layer failure"))
        with (
            patch("backend.services.authentication.urlopen", side_effect=tls_error) as urlopen,
            patch("backend.services.authentication.time.sleep"),
        ):
            with self.assertRaises(HTTPException) as error:
                _verify_token(token, "https://example.supabase.co", "anon-key")

        self.assertEqual(error.exception.status_code, 502)
        self.assertIn("TLS handshake", error.exception.detail)
        self.assertEqual(urlopen.call_count, 3)

    def test_retries_raw_tls_error_raised_while_reading_auth_response(self):
        token = _token({"sub": "user-id", "amr": []})
        response_body = json.dumps({
            "id": "user-id",
            "email": "student@example.com",
            "email_confirmed_at": "2026-10-01T00:00:00Z",
        }).encode()
        response = unittest.mock.MagicMock()
        response.__enter__.return_value.read.return_value = response_body

        with (
            patch(
                "backend.services.authentication.urlopen",
                side_effect=[ssl.SSLError(1, "record layer failure"), response],
            ) as urlopen,
            patch("backend.services.authentication.time.sleep"),
        ):
            user = _verify_token(token, "https://example.supabase.co", "anon-key")

        self.assertEqual(user["id"], "user-id")
        self.assertEqual(urlopen.call_count, 2)

    def test_returns_cors_compatible_http_error_after_repeated_raw_tls_errors(self):
        token = _token({"sub": "user-id", "amr": []})
        with (
            patch(
                "backend.services.authentication.urlopen",
                side_effect=ssl.SSLError(1, "record layer failure"),
            ) as urlopen,
            patch("backend.services.authentication.time.sleep"),
        ):
            with self.assertRaises(HTTPException) as error:
                _verify_token(token, "https://example.supabase.co", "anon-key")

        self.assertEqual(error.exception.status_code, 502)
        self.assertIn("TLS communication", error.exception.detail)
        self.assertEqual(urlopen.call_count, 3)

    def test_reports_supabase_http_status_and_code_without_response_body(self):
        token = _token({"sub": "user-id", "amr": []})
        response_body = json.dumps({
            "code": "over_request_rate_limit",
            "message": "private upstream response",
        }).encode()
        error_response = unittest.mock.MagicMock()
        error_response.read.return_value = response_body
        http_error = HTTPError(
            url="https://example.supabase.co/auth/v1/user",
            code=429,
            msg="Too Many Requests",
            hdrs=None,
            fp=error_response,
        )

        with patch("backend.services.authentication.urlopen", side_effect=http_error):
            with self.assertRaises(HTTPException) as error:
                _verify_token(token, "https://example.supabase.co", "anon-key")

        self.assertEqual(error.exception.status_code, 502)
        self.assertIn("HTTP 429", error.exception.detail)
        self.assertIn("over_request_rate_limit", error.exception.detail)
        self.assertNotIn("private upstream response", error.exception.detail)

    def test_distinguishes_non_tls_network_failure(self):
        token = _token({"sub": "user-id", "amr": []})
        with patch(
            "backend.services.authentication.urlopen",
            side_effect=URLError(ConnectionError("connection refused")),
        ):
            with self.assertRaises(HTTPException) as error:
                _verify_token(token, "https://example.supabase.co", "anon-key")

        self.assertEqual(error.exception.status_code, 502)
        self.assertIn("ConnectionError", error.exception.detail)


class AccountDeletionTests(unittest.TestCase):
    def test_removes_application_data_before_deleting_auth_identity(self):
        events = []

        def record_data_deletion(path, method="GET", body=None, prefer=None):
            events.append(("data", path, method))

        def record_auth_deletion(request, timeout):
            events.append(("auth", request.full_url, request.method))
            return unittest.mock.MagicMock()

        with (
            patch.object(supabase_store, "_settings", return_value=("https://example.supabase.co", "service-key")),
            patch.object(supabase_store, "_request", side_effect=record_data_deletion),
            patch.object(supabase_store, "urlopen", side_effect=record_auth_deletion),
        ):
            supabase_store.delete_account("user-id")

        self.assertEqual(events[0][0], "data")
        self.assertEqual(events[0][2], "DELETE")
        self.assertEqual(events[1][0], "auth")
        self.assertEqual(events[1][2], "DELETE")


if __name__ == "__main__":
    unittest.main()
