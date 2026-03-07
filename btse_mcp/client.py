"""
BTSE Futures REST client.

Authentication
--------------
BTSE uses HMAC-SHA384 signing. Every authenticated request requires three headers:

    request-api    Your API key
    request-nonce  Current timestamp in milliseconds (integer as string)
    request-sign   HMAC-SHA384( api_secret, url_path + nonce + body )
                   body is the raw JSON string for POST/PUT, or '' for GET/DELETE

Base URLs
---------
    Production : https://api.btse.com/futures
    Testnet    : https://testapi.btse.io/futures

Symbol naming
-------------
Use new-style names: BTC-PERP, ETH-PERP, SOL-PERP, etc.
"""

import hashlib
import hmac
import json
import time
from typing import Any, Optional
from urllib.parse import urlencode   # FIX: proper URL encoding

import httpx

FUTURES_BASE = "https://api.btse.com/futures"
TESTNET_BASE = "https://testapi.btse.io/futures"


class BTSEClient:
    def __init__(self, api_key: str, api_secret: str, testnet: bool = False):
        self.api_key    = api_key
        self.api_secret = api_secret
        self.base_url   = TESTNET_BASE if testnet else FUTURES_BASE

    # ── Auth ──────────────────────────────────────────────────────────────────

    def _sign(self, path: str, nonce: str, body: str = "") -> str:
        """Return HMAC-SHA384 hex digest over (path + nonce + body)."""
        msg = path + nonce + body
        return hmac.new(
            self.api_secret.encode(),
            msg.encode(),
            hashlib.sha384,
        ).hexdigest()

    def _headers(self, path: str, body: str = "") -> dict:
        nonce = str(int(time.time() * 1000))
        return {
            "request-api":   self.api_key,
            "request-nonce": nonce,
            "request-sign":  self._sign(path, nonce, body),
            "Content-Type":  "application/json",
        }

    # ── HTTP helpers ──────────────────────────────────────────────────────────

    def _get(self, path: str, params: Optional[dict] = None) -> Any:
        # FIX: use urlencode — manual join doesn't percent-encode values
        if params:
            filtered  = {k: v for k, v in params.items() if v is not None}
            full_path = f"{path}?{urlencode(filtered)}" if filtered else path
        else:
            full_path = path
        headers = self._headers(full_path)
        r = httpx.get(self.base_url + full_path, headers=headers, timeout=10)
        _raise_with_body(r)
        return r.json()

    def _post(self, path: str, payload: dict) -> Any:
        body    = json.dumps(payload, separators=(",", ":"))
        headers = self._headers(path, body)
        r = httpx.post(self.base_url + path, headers=headers, content=body, timeout=10)
        _raise_with_body(r)
        return r.json()

    def _put(self, path: str, payload: dict) -> Any:
        body    = json.dumps(payload, separators=(",", ":"))
        headers = self._headers(path, body)
        r = httpx.put(self.base_url + path, headers=headers, content=body, timeout=10)
        _raise_with_body(r)
        return r.json()

    def _delete(self, path: str, params: Optional[dict] = None) -> Any:
        # FIX: use urlencode
        if params:
            filtered  = {k: v for k, v in params.items() if v is not None}
            full_path = f"{path}?{urlencode(filtered)}" if filtered else path
        else:
            full_path = path
        headers = self._headers(full_path)
        r = httpx.delete(self.base_url + full_path, headers=headers, timeout=10)
        _raise_with_body(r)
        return r.json()

    # ── Public endpoints ──────────────────────────────────────────────────────

    def get_market_summary(self, symbol: str = None) -> Any:
        """GET /api/v2.1/market_summary — omit symbol for all markets."""
        params = {"symbol": symbol} if symbol else {}
        return self._get("/api/v2.1/market_summary", params or None)

    def get_orderbook(self, symbol: str, depth: int = None) -> Any:
        """GET /api/v2.1/orderbook/L2 — L2 orderbook snapshot."""
        params = {"symbol": symbol}
        if depth:
            params["depth"] = depth
        return self._get("/api/v2.1/orderbook/L2", params)

    def get_price(self, symbol: str = None) -> Any:
        """GET /api/v2.1/price — mark / index / last price."""
        params = {"symbol": symbol} if symbol else {}
        return self._get("/api/v2.1/price", params or None)

    def get_trades(self, symbol: str, count: int = 20) -> Any:
        """GET /api/v2.1/trades — recent public trade fills."""
        return self._get("/api/v2.1/trades", {"symbol": symbol, "count": count})

    def get_ohlcv(
        self,
        symbol: str,
        resolution: str,
        start: int = None,
        end: int = None,
    ) -> Any:
        """
        GET /api/v2.1/ohlcv — candlestick data.
        resolution: 1 | 5 | 15 | 30 | 60 | 240 | 360 | 1440 | 10080 | 43200
        """
        params = {"symbol": symbol, "resolution": resolution}
        if start:
            params["start"] = start
        if end:
            params["end"] = end
        return self._get("/api/v2.1/ohlcv", params)

    def get_funding_history(self, symbol: str = None, count: int = 10) -> Any:
        """GET /api/v2.1/funding_history — historical funding rates."""
        params = {"count": count}
        if symbol:
            params["symbol"] = symbol
        return self._get("/api/v2.1/funding_history", params)

    # ── Account endpoints ─────────────────────────────────────────────────────

    def get_wallet_balance(self, wallet: str = None) -> Any:
        """GET /api/v2.1/user/wallet — futures wallet balance.
        Falls back to /api/v2.2/user/wallet for unified wallet accounts."""
        params = {"wallet": wallet} if wallet else {}
        try:
            return self._get("/api/v2.1/user/wallet", params or None)
        except Exception as e:
            if "33000001" in str(e) or "newer API version" in str(e):
                return self._get("/api/v2.2/user/wallet", params or None)
            raise

    def get_positions(self, symbol: str = None) -> Any:
        """GET /api/v2.1/user/positions — open positions."""
        params = {"symbol": symbol} if symbol else {}
        try:
            return self._get("/api/v2.1/user/positions", params or None)
        except Exception as e:
            if "33000001" in str(e) or "newer API version" in str(e):
                return self._get("/api/v2.2/user/positions", params or None)
            raise

    def get_account_fees(self, symbol: str = None) -> Any:
        """GET /api/v2.1/user/fees — maker/taker fee rates."""
        params = {"symbol": symbol} if symbol else {}
        try:
            return self._get("/api/v2.1/user/fees", params or None)
        except Exception as e:
            if "33000001" in str(e) or "newer API version" in str(e):
                return self._get("/api/v2.2/user/fees", params or None)
            raise

    def get_leverage(self, symbol: str) -> Any:
        """GET /api/v2.1/leverage — current leverage and margin mode."""
        return self._get("/api/v2.1/leverage", {"symbol": symbol})

    def get_risk_limit(self, symbol: str) -> Any:
        """GET /api/v2.1/risk_limit — current risk limit tier."""
        return self._get("/api/v2.1/risk_limit", {"symbol": symbol})

    def get_wallet_history(self, symbol: str = None, count: int = 20) -> Any:
        """GET /api/v2.1/user/wallet_history — wallet transaction history."""
        params = {"count": count}
        if symbol:
            params["symbol"] = symbol
        try:
            return self._get("/api/v2.1/user/wallet_history", params)
        except Exception as e:
            if "33000001" in str(e) or "newer API version" in str(e):
                return self._get("/api/v2.2/user/wallet_history", params)
            raise

    # ── Order endpoints ───────────────────────────────────────────────────────

    def create_order(
        self,
        symbol: str,
        side: str,
        order_type: str,
        size: float,
        price: float = None,
        time_in_force: str = "GTC",
        post_only: bool = False,
        reduce_only: bool = False,
        cl_order_id: str = None,
        tx_type: str = None,
        trigger_price: float = None,
        take_profit_price: float = None,
        stop_loss_price: float = None,
    ) -> Any:
        """
        POST /api/v2.1/order — create a new order.

        order_type    : LIMIT | MARKET | OCO
        side          : BUY | SELL
        tx_type       : TRIGGER | STOP | LIMIT (default)
        time_in_force : GTC | IOC | FOK | DAY | WEEK | MONTH
        """
        payload: dict = {
            "symbol":        symbol,
            "side":          side.upper(),
            "type":          order_type.upper(),
            "size":          size,
            "time_in_force": time_in_force,
            "postOnly":      post_only,
            "reduceOnly":    reduce_only,
        }
        if price is not None:
            payload["price"] = price
        if cl_order_id:
            payload["clOrderID"] = cl_order_id
        if tx_type:
            payload["txType"] = tx_type
        if trigger_price is not None:
            payload["triggerPrice"] = trigger_price
        if take_profit_price is not None:
            payload["takeProfitPrice"] = take_profit_price
        if stop_loss_price is not None:
            payload["stopLossPrice"] = stop_loss_price
        return self._post("/api/v2.1/order", payload)

    def cancel_order(
        self,
        symbol: str,
        order_id: str = None,
        cl_order_id: str = None,
    ) -> Any:
        """
        DELETE /api/v2.1/order — cancel one order, or all orders for symbol
        if neither order_id nor cl_order_id is given.
        """
        params = {"symbol": symbol}
        if order_id:
            params["orderID"] = order_id
        elif cl_order_id:
            params["clOrderID"] = cl_order_id
        return self._delete("/api/v2.1/order", params)

    def get_open_orders(self, symbol: str = None) -> Any:
        """GET /api/v2.1/user/open_orders — list open orders."""
        params = {"symbol": symbol} if symbol else {}
        try:
            return self._get("/api/v2.1/user/open_orders", params or None)
        except Exception as e:
            if "33000001" in str(e) or "newer API version" in str(e):
                return self._get("/api/v2.2/user/open_orders", params or None)
            raise

    def get_order(self, order_id: str = None, cl_order_id: str = None) -> Any:
        """GET /api/v2.1/order — single order detail."""
        # FIX: validate at least one identifier is provided
        if not order_id and not cl_order_id:
            raise ValueError("get_order requires either order_id or cl_order_id")
        params = {}
        if order_id:
            params["orderID"] = order_id
        else:
            params["clOrderID"] = cl_order_id
        return self._get("/api/v2.1/order", params)

    def get_trade_history(self, symbol: str = None, count: int = 20) -> Any:
        """GET /api/v2.1/user/trade_history — user trade history."""
        params = {"count": count}
        if symbol:
            params["symbol"] = symbol
        try:
            return self._get("/api/v2.1/user/trade_history", params)
        except Exception as e:
            if "33000001" in str(e) or "newer API version" in str(e):
                return self._get("/api/v2.2/user/trade_history", params)
            raise

    def amend_order(
        self,
        symbol: str,
        order_id: str,
        amend_type: str,
        value: float = None,
        order_price: float = None,
        order_size: float = None,
        trigger_price: float = None,
    ) -> Any:
        """
        PUT /api/v2.1/order — amend an existing order.
        amend_type: PRICE | SIZE | TRIGGERPRICE | ALL
        """
        payload: dict = {
            "symbol":  symbol,
            "orderID": order_id,
            "type":    amend_type.upper(),
        }
        if value is not None:
            payload["value"] = value
        if order_price is not None:
            payload["orderPrice"] = order_price
        if order_size is not None:
            payload["orderSize"] = order_size
        if trigger_price is not None:
            payload["triggerPrice"] = trigger_price
        return self._put("/api/v2.1/order", payload)

    def close_position(
        self,
        symbol: str,
        close_type: str = "MARKET",
        price: float = None,
    ) -> Any:
        """POST /api/v2.1/order/close_position — close an open position."""
        payload: dict = {"symbol": symbol, "type": close_type.upper()}
        if price is not None:
            payload["price"] = price
        return self._post("/api/v2.1/order/close_position", payload)

    # ── Risk / leverage ───────────────────────────────────────────────────────

    def set_leverage(
        self,
        symbol: str,
        leverage: float,
        margin_mode: str = "ISOLATED",
    ) -> Any:
        """POST /api/v2.1/leverage — set leverage. leverage=0 means max cross."""
        return self._post("/api/v2.1/leverage", {
            "symbol":     symbol,
            "leverage":   leverage,
            "marginMode": margin_mode.upper(),
        })

    def set_risk_limit(self, symbol: str, risk_limit_level: int) -> Any:
        """POST /api/v2.1/risk_limit — set risk limit tier."""
        return self._post("/api/v2.1/risk_limit", {
            "symbol":         symbol,
            "riskLimitLevel": risk_limit_level,
        })


# ── Helpers ───────────────────────────────────────────────────────────────────

def _raise_with_body(r: httpx.Response) -> None:
    """
    FIX: raise on HTTP errors and include BTSE's response body in the message
    so callers see the actual rejection reason (e.g. 'Order size too small'),
    not just the HTTP status code.
    """
    if r.is_error:
        try:
            detail = r.json()
        except Exception:
            detail = r.text
        raise httpx.HTTPStatusError(
            f"HTTP {r.status_code} from BTSE: {detail}",
            request=r.request,
            response=r,
        )
