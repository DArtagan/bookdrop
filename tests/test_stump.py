import json

import httpx
import pytest

from bookdrop.stump import ScanFailed, scan


def stump(answer, seen: list | None = None) -> httpx.Client:
    def handle(request: httpx.Request) -> httpx.Response:
        if seen is not None:
            seen.append(request)
        if isinstance(answer, Exception):
            raise answer
        if isinstance(answer, int):
            return httpx.Response(answer)
        return httpx.Response(200, json=answer)

    return httpx.Client(transport=httpx.MockTransport(handle))


def test_asks_for_a_scan_of_the_library_with_the_key():
    seen = []
    scan(
        "http://stump:10801/",
        "key",
        "lib-1",
        stump({"data": {"scanLibrary": True}}, seen),
    )
    (request,) = seen
    assert str(request.url) == "http://stump:10801/api/graphql"
    assert request.headers["Authorization"] == "Bearer key"
    body = json.loads(request.content)
    assert "scanLibrary(id: $id)" in body["query"]
    assert body["variables"] == {"id": "lib-1"}


@pytest.mark.parametrize(
    ("answer", "said"),
    [
        ({"errors": [{"message": "Missing permission: ScanLibrary"}]}, "ScanLibrary"),
        ({"data": {"scanLibrary": False}}, "unexpected answer"),
        (401, "HTTPStatusError"),
        (httpx.ConnectError("refused"), "ConnectError: refused"),
    ],
)
def test_every_failure_is_raised(answer, said):
    with pytest.raises(ScanFailed, match=said):
        scan("http://stump", "key", "lib-1", stump(answer))
