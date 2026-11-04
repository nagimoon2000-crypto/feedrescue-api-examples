"""Anonymous FeedRescue preflight. No API key or product payload is sent."""
import argparse
import json
from urllib.error import HTTPError, URLError
from urllib.parse import urlsplit
from urllib.request import HTTPRedirectHandler, Request, build_opener

ORIGIN = "https://gimoon.pythonanywhere.com"
OPERATIONS = ("/v1/products/validate", "/v1/products/batch-validate",
              "/v1/feeds/validate", "/v1/products/suggest-fixes")


class NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, *args, **kwargs):
        return None


def check_connection(origin=ORIGIN):
    parsed = urlsplit(origin)
    local = parsed.hostname in {"127.0.0.1", "localhost", "::1"}
    if (parsed.username or parsed.password or parsed.query or parsed.fragment or
            parsed.path not in {"", "/"} or not parsed.hostname or
            (parsed.scheme != "https" and not (local and parsed.scheme == "http"))):
        raise ValueError("Use a bare HTTPS origin, or HTTP localhost; no credentials or query.")
    checks = []
    for path, expected in (("/v1/health", 200), ("/v1/openapi.json", 200), ("/v1/usage", 401)):
        status = None
        valid = False
        try:
            request = Request(origin.rstrip("/") + path, headers={"Accept": "application/json"})
            try:
                response = build_opener(NoRedirect).open(request, timeout=10)
            except HTTPError as error:
                response = error
            with response:
                status = response.status
                payload = json.loads(response.read(1048577))
            valid = status == expected
            if path == "/v1/health":
                valid = valid and payload.get("ok") is True
            elif path == "/v1/openapi.json":
                valid = valid and all("post" in payload.get("paths", {}).get(p, {}) for p in OPERATIONS)
            else:
                valid = valid and payload.get("error", {}).get("code") == "INVALID_API_KEY"
        except (OSError, URLError, ValueError, AttributeError, TypeError):
            pass
        # Never echo raw provider responses, headers, user data or environment secrets.
        checks.append({"path": path, "status": status, "passed": bool(valid)})
    ready = all(item["passed"] for item in checks)
    return {"ready_for_key_request": ready, "checks": checks,
        "api_key_sent": False, "product_data_sent": False,
        "next_step": "Request a manual free pilot key using the README contact instructions." if ready
                     else "Read docs/errors-and-limits.md; report only status codes and a synthetic reproduction.",
        "limits": "Anonymous origin preflight only. Not a product diagnosis, RapidAPI gateway test, or uptime guarantee."}


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--origin", default=ORIGIN)
    args = parser.parse_args()
    try:
        result = check_connection(args.origin)
    except ValueError as error:
        parser.error(str(error))
    print(json.dumps(result, indent=2))
    raise SystemExit(0 if result["ready_for_key_request"] else 1)
