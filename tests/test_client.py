"""
Unit tests for BTSEClient.

These tests verify auth signature construction against the worked examples
in the official BTSE API docs. No live API connection is required.

Run with:
    pytest -v
"""

from btse_mcp.client import BTSEClient, FUTURES_BASE, TESTNET_BASE


# ── Signature tests ───────────────────────────────────────────────────────────
# Test vectors taken verbatim from https://btsecom.github.io/docs/futures/en/

SECRET = "848db84ac252b6726e5f6e7a711d9c96d9fd77d020151b45839a5b59c37203bx"


def test_signature_get_wallet():
    """GET /api/v2.1/user/wallet — no request body."""
    client   = BTSEClient("dummy", SECRET)
    sig      = client._sign("/api/v2.1/user/wallet", "1624984297330")
    expected = (
        "ea4f1f2b43a0f4d750ae560c5274d6214d140fcab3093da5f4a83e36828535bd"
        "2ba7b12160cd12199596f422c8883333"
    )
    assert sig == expected


def test_signature_post_order():
    """POST /api/v2.1/order — with JSON body."""
    client = BTSEClient("dummy", SECRET)
    body   = (
        '{"postOnly":false,"price":8500.0,"reduceOnly":false,"side":"BUY",'
        '"size":1,"stopPrice":0.0,"symbol":"BTCPFC","time_in_force":"GTC",'
        '"trailValue":0.0,"triggerPrice":0.0,"txType":"LIMIT","type":"LIMIT"}'
    )
    sig      = client._sign("/api/v2.1/order", "1624985375123", body)
    expected = (
        "943adfce43b609a28506274976b96e08cf4bdc4ea53ca0b4cac0eb2cf0773a7d"
        "0807efc0aeab779d47fadcd9a60eea13"
    )
    assert sig == expected


# ── URL tests ─────────────────────────────────────────────────────────────────

def test_production_base_url():
    client = BTSEClient("k", "s", testnet=False)
    assert client.base_url == FUTURES_BASE
    assert "testapi" not in client.base_url


def test_testnet_base_url():
    client = BTSEClient("k", "s", testnet=True)
    assert client.base_url == TESTNET_BASE
    assert "testapi" in client.base_url


# ── Header structure tests ────────────────────────────────────────────────────

def test_headers_contain_required_keys():
    client  = BTSEClient("my-api-key", SECRET)
    headers = client._headers("/api/v2.1/user/wallet")
    assert "request-api"   in headers
    assert "request-nonce" in headers
    assert "request-sign"  in headers
    assert "Content-Type"  in headers


def test_headers_api_key_matches():
    client  = BTSEClient("my-api-key", SECRET)
    headers = client._headers("/api/v2.1/user/wallet")
    assert headers["request-api"] == "my-api-key"


def test_headers_nonce_is_numeric_string():
    client  = BTSEClient("k", SECRET)
    headers = client._headers("/api/v2.1/user/wallet")
    assert headers["request-nonce"].isdigit()


def test_headers_sign_is_hex_string():
    client  = BTSEClient("k", SECRET)
    headers = client._headers("/api/v2.1/user/wallet")
    sig     = headers["request-sign"]
    # SHA-384 produces 96 hex chars
    assert len(sig) == 96
    assert all(c in "0123456789abcdef" for c in sig)


# ── Validation tests ──────────────────────────────────────────────────────────

def test_get_order_raises_without_ids():
    """get_order must raise if neither order_id nor cl_order_id is given."""
    import pytest
    client = BTSEClient("k", "s")
    with pytest.raises(ValueError, match="requires either"):
        client.get_order()


def test_get_order_accepts_order_id():
    """get_order should not raise when order_id is provided (no network call here)."""
    # We just verify the method doesn't raise before making a network call.
    # The actual network path is covered by integration tests.
    client = BTSEClient("k", "s")
    # Patch _get to avoid a real HTTP call
    client._get = lambda path, params=None: [{"orderID": params.get("orderID")}]
    result = client.get_order(order_id="abc123")
    assert result[0]["orderID"] == "abc123"
