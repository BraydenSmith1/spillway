"""
ercot.py — logs in to ERCOT and downloads data.
You should not need to edit this. Other scripts import from it.
"""

import os
import time
import requests
import pandas as pd
from dotenv import load_dotenv

load_dotenv()

USERNAME = (os.getenv("ERCOT_USERNAME") or "").strip()
PASSWORD = (os.getenv("ERCOT_PASSWORD") or "").strip()
SUB_KEY = (os.getenv("ERCOT_SUBSCRIPTION_KEY") or "").strip()

# Fixed by ERCOT. Do not change.
TOKEN_URL = (
    "https://ercotb2c.b2clogin.com/ercotb2c.onmicrosoft.com/"
    "B2C_1_PUBAPI-ROPC-FLOW/oauth2/v2.0/token"
)
CLIENT_ID = "fec253ea-0d06-4272-a5e6-b478baeecd70"
SCOPE = f"openid {CLIENT_ID} offline_access"
BASE_URL = "https://api.ercot.com/api/public-reports"

_token = None
_expires_at = 0


def get_token():
    """Return a valid id_token, reusing the cached one until near expiry."""
    global _token, _expires_at

    if _token and time.time() < _expires_at - 120:
        return _token

    if not USERNAME or not PASSWORD:
        raise RuntimeError(
            "Missing credentials. Is .env at the project root with "
            "ERCOT_USERNAME and ERCOT_PASSWORD, values in single quotes?"
        )

    r = requests.post(TOKEN_URL, timeout=60, data={
        "grant_type": "password",
        "username": USERNAME,
        "password": PASSWORD,
        "response_type": "id_token",
        "scope": SCOPE,
        "client_id": CLIENT_ID,
    })

    if r.status_code != 200:
        raise RuntimeError(
            f"Login failed ({r.status_code}): {r.text[:400]}\n"
            "Run: python scripts/diagnose.py"
        )

    body = r.json()
    _token = body.get("id_token")          # id_token, NOT access_token
    if not _token:
        raise RuntimeError(f"No id_token returned. Got: {list(body.keys())}")

    _expires_at = time.time() + int(body.get("expires_in", 3600))
    return _token


def headers():
    return {
        "Authorization": f"Bearer {get_token()}",
        "Ocp-Apim-Subscription-Key": SUB_KEY,
        "Accept": "application/json",
    }


def probe(endpoint, params=None):
    """
    Fetch ONE page and return the raw JSON, unparsed.
    Use this first on any new dataset to see its actual shape.
    """
    p = dict(params or {})
    p.setdefault("size", 5)
    r = requests.get(BASE_URL + endpoint, headers=headers(), params=p, timeout=120)
    print(f"status: {r.status_code}")
    if r.status_code != 200:
        print(r.text[:800])
        return None
    return r.json()


def iter_pages(endpoint, params=None, max_pages=5000, max_retries=8,
               start_page=1, log=None, log_every=50):
    """
    Yield one API page at a time as (page, total_pages, batch, cols).

    Streaming instead of accumulating means a caller can save progress as it
    goes, so an interrupted download costs minutes instead of hours — and a
    million-row month never has to fit in memory all at once.

    start_page lets a caller resume where it left off.
    """
    p = dict(params or {})
    p.setdefault("size", 5000)
    cols, page = None, start_page
    total_pages = total_records = None
    retries = 0
    seen = 0

    while page <= max_pages:
        p["page"] = page
        try:
            r = requests.get(BASE_URL + endpoint, headers=headers(),
                             params=p, timeout=180)
        except requests.exceptions.RequestException as e:
            retries += 1
            if retries > max_retries:
                raise RuntimeError(f"Gave up on page {page} after {max_retries} "
                                    f"connection retries: {e}")
            time.sleep(10)
            continue

        if r.status_code == 429:                # rate limited
            retries += 1
            if retries > max_retries:
                raise RuntimeError(f"Still rate limited on page {page} after "
                                    f"{max_retries} retries")
            time.sleep(15)
            continue
        if r.status_code in (502, 503, 504):    # transient
            retries += 1
            if retries > max_retries:
                raise RuntimeError(f"Server still returning {r.status_code} on "
                                    f"page {page} after {max_retries} retries")
            time.sleep(10)
            continue
        if r.status_code != 200:
            raise RuntimeError(f"Request failed ({r.status_code}): {r.text[:400]}")

        retries = 0                             # reset after a good page
        body = r.json()

        # Column names live in a separate "fields" block, and the key
        # holding the name has varied. Try the likely ones.
        if cols is None and isinstance(body.get("fields"), list):
            cols = []
            for f in body["fields"]:
                if isinstance(f, dict):
                    cols.append(f.get("name") or f.get("label")
                                or f.get("fieldName") or str(len(cols)))
                else:
                    cols.append(str(f))

        batch = body.get("data") or []
        if not batch:
            return

        meta = body.get("_meta") or {}
        total_pages = meta.get("totalPages", page)
        total_records = meta.get("totalRecords", seen)
        seen += len(batch)

        # Progress every log_every pages, so a long month is visibly alive
        # rather than silent for hours.
        if log and (page == start_page or page % log_every == 0):
            log(f"      page {page}/{total_pages}, {seen:,} rows this pass")

        yield page, total_pages, batch, cols

        if page >= total_pages:
            return
        page += 1
        time.sleep(0.25)

    raise RuntimeError(
        f"Truncated: hit max_pages={max_pages} with only "
        f"{seen:,} of {total_records:,} rows ({page - 1}/{total_pages} "
        "pages) fetched. Narrow the date range or raise max_pages."
    )


def to_frame(rows, cols=None):
    """Turn raw API rows into a DataFrame, list- or dict-shaped."""
    if not rows:
        return pd.DataFrame()
    # Rows may be lists (needing `cols`) or dicts (self-describing).
    if isinstance(rows[0], dict):
        return pd.DataFrame(rows)
    if cols and len(cols) == len(rows[0]):
        return pd.DataFrame(rows, columns=cols)
    return pd.DataFrame(rows)   # last resort: numbered columns


def fetch(endpoint, params=None, max_pages=5000, verbose=False, max_retries=8):
    """
    Download a whole dataset, following pagination.
    Returns a pandas DataFrame.

    Convenience wrapper around iter_pages() for small datasets. For anything
    large, prefer iter_pages() so progress can be saved incrementally.
    """
    rows, cols = [], None
    for _page, _total, batch, page_cols in iter_pages(
            endpoint, params, max_pages=max_pages, max_retries=max_retries,
            log=print if verbose else None):
        rows.extend(batch)
        cols = page_cols or cols
    return to_frame(rows, cols)