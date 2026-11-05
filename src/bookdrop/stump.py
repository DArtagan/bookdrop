import httpx

TIMEOUT = 15.0
SCAN = "mutation Scan($id: ID!) { scanLibrary(id: $id) }"


class ScanFailed(Exception):
    """Stump could not be asked to scan, or refused."""


def scan(url: str, api_key: str, library_id: str, http: httpx.Client) -> None:
    """Ask Stump to scan the library, which it queues and runs on its own.

    The key needs only the ScanLibrary permission. A filed book reaches Stump
    only this way: its watcher sees nothing written by another client of the
    share.
    """
    try:
        response = http.post(
            f"{url.rstrip('/')}/api/graphql",
            json={"query": SCAN, "variables": {"id": library_id}},
            headers={"Authorization": f"Bearer {api_key}"},
            timeout=TIMEOUT,
        )
        response.raise_for_status()
        body = response.json()
    except httpx.HTTPError as error:
        raise ScanFailed(f"{type(error).__name__}: {error}") from error
    except ValueError as error:
        raise ScanFailed(f"an answer it could not read ({error!r})") from error
    if body.get("errors"):
        raise ScanFailed(body["errors"][0].get("message", "an unnamed error"))
    if (body.get("data") or {}).get("scanLibrary") is not True:
        raise ScanFailed(f"an unexpected answer: {body!r}")
