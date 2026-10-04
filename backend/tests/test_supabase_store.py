import io
import ssl
import unittest
from urllib.error import HTTPError, URLError
from unittest.mock import patch

from backend.services import supabase_store


class SupabaseStoreDiagnosticsTests(unittest.TestCase):
    def test_database_error_includes_table_status_and_error_code_not_response_body(self):
        error_body = b'{"code":"23503","message":"sensitive row value"}'
        http_error = HTTPError(
            url="https://example.supabase.co/rest/v1/sessions",
            code=400,
            msg="Bad Request",
            hdrs=None,
            fp=io.BytesIO(error_body),
        )

        with (
            patch.object(
                supabase_store,
                "_settings",
                return_value=("https://example.supabase.co", "service-key"),
            ),
            patch.object(supabase_store, "urlopen", side_effect=http_error),
        ):
            with self.assertRaises(supabase_store.SupabaseError) as raised:
                supabase_store._request("sessions", method="POST", body={"problem_text": "private"})

        self.assertIn("POST on sessions", str(raised.exception))
        self.assertIn("HTTP 400", str(raised.exception))
        self.assertIn("23503", str(raised.exception))
        self.assertNotIn("sensitive row value", str(raised.exception))
        self.assertNotIn("private", str(raised.exception))

    def test_retries_post_after_tls_handshake_failure(self):
        response = unittest.mock.MagicMock()
        response.__enter__.return_value.read.return_value = b'[{"id":"session-id"}]'
        tls_error = URLError(ssl.SSLError(1, "record layer failure"))

        with (
            patch.object(
                supabase_store,
                "_settings",
                return_value=("https://example.supabase.co", "service-key"),
            ),
            patch.object(supabase_store, "urlopen", side_effect=[tls_error, response]) as open_url,
            patch.object(supabase_store.time, "sleep"),
        ):
            result = supabase_store._request(
                "sessions",
                method="POST",
                body={"problem_text": "private"},
            )

        self.assertEqual(result, [{"id": "session-id"}])
        self.assertEqual(open_url.call_count, 2)

    def test_retries_message_upsert_after_tls_handshake_timeout_with_same_message_id(self):
        response = unittest.mock.MagicMock()
        response.__enter__.return_value.read.return_value = b'[{"id":"message-id","role":"tutor"}]'
        handshake_timeout = URLError(TimeoutError("_ssl.c: handshake operation timed out"))

        with (
            patch.object(
                supabase_store,
                "_settings",
                return_value=("https://example.supabase.co", "service-key"),
            ),
            patch.object(
                supabase_store,
                "urlopen",
                side_effect=[handshake_timeout, response],
            ) as open_url,
            patch.object(supabase_store.time, "sleep"),
        ):
            result = supabase_store.add_message("session-id", "tutor", "Try this next?", 1)

        self.assertEqual(result["id"], "message-id")
        self.assertEqual(open_url.call_count, 2)
        first_request, second_request = [call.args[0] for call in open_url.call_args_list]
        self.assertEqual(first_request.full_url, second_request.full_url)
        self.assertEqual(first_request.data, second_request.data)
        self.assertEqual(first_request.get_method(), "POST")
        self.assertIn("messages?on_conflict=id", first_request.full_url)
        self.assertIn("resolution=merge-duplicates", first_request.get_header("Prefer"))

    def test_retries_timeout_only_for_explicitly_idempotent_message_post(self):
        response = unittest.mock.MagicMock()
        response.__enter__.return_value.read.return_value = b'[]'
        handshake_timeout = URLError(TimeoutError("TLS handshake timeout"))

        with (
            patch.object(
                supabase_store,
                "_settings",
                return_value=("https://example.supabase.co", "service-key"),
            ),
            patch.object(
                supabase_store,
                "urlopen",
                side_effect=[handshake_timeout, response],
            ) as open_url,
            patch.object(supabase_store.time, "sleep"),
        ):
            result = supabase_store._request(
                "messages?on_conflict=id",
                method="POST",
                body={"id": "stable-message-id"},
                prefer="resolution=merge-duplicates,return=representation",
                retryable_post=True,
            )

        self.assertEqual(result, [])
        self.assertEqual(open_url.call_count, 2)

    def test_does_not_retry_non_tls_network_errors(self):
        network_error = URLError("connection refused")
        with (
            patch.object(
                supabase_store,
                "_settings",
                return_value=("https://example.supabase.co", "service-key"),
            ),
            patch.object(supabase_store, "urlopen", side_effect=network_error) as open_url,
        ):
            with self.assertRaisesRegex(
                supabase_store.SupabaseError,
                "could not be reached",
            ):
                supabase_store._request("sessions", method="POST")

        open_url.assert_called_once()

    def test_retries_idempotent_patch_after_connection_failure(self):
        response = unittest.mock.MagicMock()
        response.__enter__.return_value.read.return_value = b""
        network_error = URLError(ConnectionResetError("connection reset"))

        with (
            patch.object(
                supabase_store,
                "_settings",
                return_value=("https://example.supabase.co", "service-key"),
            ),
            patch.object(
                supabase_store,
                "urlopen",
                side_effect=[network_error, response],
            ) as open_url,
            patch.object(supabase_store.time, "sleep"),
        ):
            result = supabase_store._request(
                "sessions?id=eq.session-id&user_id=eq.user-id",
                method="PATCH",
                body={"mode": "explore"},
                prefer="return=minimal",
            )

        self.assertIsNone(result)
        self.assertEqual(open_url.call_count, 2)

    def test_does_not_retry_non_idempotent_post_after_network_failure(self):
        network_error = URLError(ConnectionResetError("connection reset"))
        with (
            patch.object(
                supabase_store,
                "_settings",
                return_value=("https://example.supabase.co", "service-key"),
            ),
            patch.object(supabase_store, "urlopen", side_effect=network_error) as open_url,
        ):
            with self.assertRaisesRegex(
                supabase_store.SupabaseError,
                r"could not be reached after 1 attempt\(s\) \(ConnectionResetError\)",
            ):
                supabase_store._request(
                    "sessions",
                    method="POST",
                    body={"problem_text": "private"},
                )

        open_url.assert_called_once()

    def test_converts_raw_tls_error_during_post_response_to_supabase_error(self):
        with (
            patch.object(
                supabase_store,
                "_settings",
                return_value=("https://example.supabase.co", "service-key"),
            ),
            patch.object(
                supabase_store,
                "urlopen",
                side_effect=ssl.SSLError(1, "record layer failure"),
            ) as open_url,
        ):
            with self.assertRaisesRegex(
                supabase_store.SupabaseError,
                "failed during TLS communication",
            ):
                supabase_store._request(
                    "sessions",
                    method="POST",
                    body={"problem_text": "Who is the current President of India?"},
                )

        open_url.assert_called_once()

    def test_retries_raw_tls_error_during_idempotent_patch_response(self):
        response = unittest.mock.MagicMock()
        response.__enter__.return_value.read.return_value = b""

        with (
            patch.object(
                supabase_store,
                "_settings",
                return_value=("https://example.supabase.co", "service-key"),
            ),
            patch.object(
                supabase_store,
                "urlopen",
                side_effect=[ssl.SSLError(1, "record layer failure"), response],
            ) as open_url,
            patch.object(supabase_store.time, "sleep"),
        ):
            result = supabase_store._request(
                "sessions?id=eq.session-id",
                method="PATCH",
                body={"mode": "explore"},
            )

        self.assertIsNone(result)
        self.assertEqual(open_url.call_count, 2)


if __name__ == "__main__":
    unittest.main()
