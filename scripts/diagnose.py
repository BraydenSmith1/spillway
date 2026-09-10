"""Checks credentials without ever printing them. Run: python scripts/diagnose.py"""

import os
import requests
from dotenv import load_dotenv, find_dotenv

path = find_dotenv()
print(f".env found at: {path or 'NOT FOUND — is it at the project root?'}")
load_dotenv()

u = os.getenv("ERCOT_USERNAME")
p = os.getenv("ERCOT_PASSWORD")
k = os.getenv("ERCOT_SUBSCRIPTION_KEY")

print(f"username             : {u!r}")
print(f"password length      : {len(p) if p else 0}   <-- compare to your real password")
print(f"password stray space : {p != p.strip() if p else 'n/a'}")
print(f"key length           : {len(k) if k else 0}")

print("\n--- login attempt ---")
r = requests.post(
    "https://ercotb2c.b2clogin.com/ercotb2c.onmicrosoft.com/"
    "B2C_1_PUBAPI-ROPC-FLOW/oauth2/v2.0/token",
    data={
        "grant_type": "password",
        "username": (u or "").strip(),
        "password": (p or "").strip(),
        "response_type": "id_token",
        "scope": "openid fec253ea-0d06-4272-a5e6-b478baeecd70 offline_access",
        "client_id": "fec253ea-0d06-4272-a5e6-b478baeecd70",
    },
    timeout=60,
)

print(f"status: {r.status_code}")
if r.status_code == 200:
    body = r.json()
    print("SUCCESS. id_token present:", "id_token" in body)
    print("token keys returned:", list(body.keys()))
else:
    print(r.text[:600])