import ssl
import unittest
from urllib.error import HTTPError, URLError
from urllib.request import Request
from unittest.mock import patch

import httpx

from backend.services import supabase_transport


class SupabaseTransportTests(unittest.TestCase):
    def test_reuses_shared_client_and_preserves_request_data(self):
        request = Request(
            "https://example.supabase.co/rest/v1/sessions",
            data=b'{"problem_text":"test"}',
            headers={"apikey": "anon-key"},
            method="POST",
        )

        with patch.object(
            supabase_transport._client,
            "request",
            side_effect=[
                httpx.Response(200, content=b'{"id":"session-id"}'),
                httpx.Response(200, content=b'{"id":"session-id"}'),
            ],
        ) as send:
            with supabase_transport.urlopen(request, timeout=15) as result:
                self.assertEqual(result.read(), b'{"id":"session-id"}')
            with supabase_transport.urlopen(request, timeout=15) as second_result:
                self.assertEqual(second_result.read(), b'{"id":"session-id"}')

        self.assertEqual(send.call_count, 2)
        self.assertEqual(send.call_args.args[:2], ("POST", request.full_url))
        self.assertEqual(send.call_args.kwargs["content"], request.data)
        self.assertEqual(send.call_args.kwargs["timeout"], 15)

    def test_converts_http_errors_to_urllib_compatible_error(self):
        response = httpx.Response(
            503,
            headers={"content-type": "application/json"},
            content=b'{"code":"upstream_error"}',
            request=httpx.Request("GET", "https://example.supabase.co/rest/v1/sessions"),
        )
        request = Request("https://example.supabase.co/rest/v1/sessions")

        with (
            patch.object(supabase_transport._client, "request", return_value=response),
            self.assertRaises(HTTPError) as raised,
        ):
            supabase_transport.urlopen(request)

        self.assertEqual(raised.exception.code, 503)
        self.assertEqual(raised.exception.read(), b'{"code":"upstream_error"}')

    def test_preserves_tls_error_for_existing_retry_policy(self):
        request = Request("https://example.supabase.co/rest/v1/sessions")
        tls_error = ssl.SSLError(1, "handshake failed")
        transport_error = httpx.ConnectError("TLS failed", request=httpx.Request("GET", request.full_url))
        transport_error.__cause__ = tls_error

        with (
            patch.object(supabase_transport._client, "request", side_effect=transport_error),
            self.assertRaises(URLError) as raised,
        ):
            supabase_transport.urlopen(request)

        self.assertIs(raised.exception.reason, tls_error)

    def test_converts_timeout_to_urllib_compatible_timeout(self):
        request = Request("https://example.supabase.co/rest/v1/sessions")
        timeout = httpx.ConnectTimeout("timed out", request=httpx.Request("GET", request.full_url))

        with (
            patch.object(supabase_transport._client, "request", side_effect=timeout),
            self.assertRaises(URLError) as raised,
        ):
            supabase_transport.urlopen(request)

        self.assertIsInstance(raised.exception.reason, TimeoutError)


if __name__ == "__main__":
    unittest.main()
