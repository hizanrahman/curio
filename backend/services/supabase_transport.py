import atexit
from io import BytesIO
import ssl
from urllib.error import HTTPError, URLError
from urllib.request import Request

import httpx


_client = httpx.Client(
    timeout=httpx.Timeout(20.0, connect=15.0),
    limits=httpx.Limits(
        max_connections=100,
        max_keepalive_connections=20,
        keepalive_expiry=30.0,
    ),
    follow_redirects=False,
    trust_env=True,
)
atexit.register(_client.close)


class _PooledResponse:
    def __init__(self, response: httpx.Response):
        self._response = response
        self._body = BytesIO(response.content)

    def __enter__(self):
        return self

    def __exit__(self, _exception_type, _exception, _traceback):
        self.close()

    def read(self) -> bytes:
        return self._body.read()

    def close(self) -> None:
        self._response.close()


def _ssl_error(error: BaseException) -> ssl.SSLError | None:
    pending = [error]
    visited: set[int] = set()
    while pending:
        current = pending.pop()
        if id(current) in visited:
            continue
        visited.add(id(current))
        if isinstance(current, ssl.SSLError):
            return current
        for nested in (
            getattr(current, "__cause__", None),
            getattr(current, "__context__", None),
            getattr(current, "reason", None),
        ):
            if isinstance(nested, BaseException):
                pending.append(nested)
    return None


def urlopen(request: Request, timeout: float = 20.0) -> _PooledResponse:
    try:
        response = _client.request(
            request.get_method(),
            request.full_url,
            headers=dict(request.header_items()),
            content=request.data,
            timeout=timeout,
        )
    except httpx.TransportError as exc:
        tls_error = _ssl_error(exc)
        if tls_error is not None:
            raise URLError(tls_error) from exc
        if isinstance(exc, httpx.TimeoutException):
            raise URLError(TimeoutError()) from exc
        raise URLError(ConnectionError(type(exc).__name__)) from exc

    if response.status_code >= 400:
        response_body = response.content
        status_code = response.status_code
        reason_phrase = response.reason_phrase
        response_headers = response.headers
        response.close()
        raise HTTPError(
            request.full_url,
            status_code,
            reason_phrase,
            response_headers,
            BytesIO(response_body),
        )
    return _PooledResponse(response)
