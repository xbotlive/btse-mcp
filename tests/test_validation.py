"""
Tests for the input validation layer in btse_mcp.tools.

No live API calls — all validation happens before any network request.
"""

import pytest
from btse_mcp.tools import (
    ValidationError,
    _validate_create_order,
    _validate_amend_order,
    _validate_set_leverage,
)


# ── btse_create_order validation ──────────────────────────────────────────────

class TestValidateCreateOrder:

    def test_valid_market_order(self):
        # Should not raise
        _validate_create_order({"side": "BUY", "order_type": "MARKET", "size": 1})

    def test_valid_limit_order(self):
        _validate_create_order({"side": "SELL", "order_type": "LIMIT", "size": 0.5, "price": 50000})

    def test_valid_oco_order(self):
        _validate_create_order({
            "side": "BUY", "order_type": "OCO", "size": 1,
            "take_profit_price": 55000, "stop_loss_price": 45000,
        })

    def test_lowercase_side_normalised(self):
        # "buy" is uppercased to "BUY" — should NOT raise (normalization, not rejection)
        _validate_create_order({"side": "buy", "order_type": "MARKET", "size": 1})

    def test_invalid_side_garbage(self):
        # "LONG" is not BUY or SELL even after uppercasing
        with pytest.raises(ValidationError, match="side must be BUY or SELL"):
            _validate_create_order({"side": "LONG", "order_type": "MARKET", "size": 1})

    def test_zero_size(self):
        with pytest.raises(ValidationError, match="size must be a positive number"):
            _validate_create_order({"side": "BUY", "order_type": "MARKET", "size": 0})

    def test_negative_size(self):
        with pytest.raises(ValidationError, match="size must be a positive number"):
            _validate_create_order({"side": "BUY", "order_type": "MARKET", "size": -1})

    def test_limit_order_missing_price(self):
        with pytest.raises(ValidationError, match="price is required for LIMIT orders"):
            _validate_create_order({"side": "BUY", "order_type": "LIMIT", "size": 1})

    def test_oco_missing_take_profit(self):
        with pytest.raises(ValidationError, match="take_profit_price is required"):
            _validate_create_order({
                "side": "BUY", "order_type": "OCO", "size": 1,
                "stop_loss_price": 45000,
            })

    def test_oco_missing_stop_loss(self):
        with pytest.raises(ValidationError, match="stop_loss_price is required"):
            _validate_create_order({
                "side": "BUY", "order_type": "OCO", "size": 1,
                "take_profit_price": 55000,
            })

    def test_side_is_case_normalised(self):
        # Uppercase BUY passed to _validate; the client itself also uppercases
        _validate_create_order({"side": "BUY", "order_type": "MARKET", "size": 1})


# ── btse_amend_order validation ───────────────────────────────────────────────

class TestValidateAmendOrder:

    def test_valid_price_amend(self):
        _validate_amend_order({"amend_type": "PRICE", "value": 50000})

    def test_valid_size_amend(self):
        _validate_amend_order({"amend_type": "SIZE", "value": 2})

    def test_valid_trigger_amend(self):
        _validate_amend_order({"amend_type": "TRIGGERPRICE", "trigger_price": 48000})

    def test_valid_all_amend(self):
        _validate_amend_order({
            "amend_type": "ALL",
            "order_price": 50000, "order_size": 2, "trigger_price": 49000,
        })

    def test_invalid_amend_type(self):
        with pytest.raises(ValidationError, match="amend_type must be one of"):
            _validate_amend_order({"amend_type": "WHATEVER"})

    def test_all_amend_no_fields(self):
        with pytest.raises(ValidationError, match="requires at least one of"):
            _validate_amend_order({"amend_type": "ALL"})

    def test_price_amend_no_value(self):
        with pytest.raises(ValidationError, match="PRICE amendment requires"):
            _validate_amend_order({"amend_type": "PRICE"})

    def test_size_amend_no_value(self):
        with pytest.raises(ValidationError, match="SIZE amendment requires"):
            _validate_amend_order({"amend_type": "SIZE"})

    def test_trigger_amend_no_price(self):
        with pytest.raises(ValidationError, match="TRIGGERPRICE amendment requires"):
            _validate_amend_order({"amend_type": "TRIGGERPRICE"})


# ── btse_set_leverage validation ──────────────────────────────────────────────

class TestValidateSetLeverage:

    def test_valid_leverage(self):
        _validate_set_leverage({"leverage": 10})

    def test_zero_leverage(self):
        # 0 = max cross — valid
        _validate_set_leverage({"leverage": 0})

    def test_max_leverage(self):
        _validate_set_leverage({"leverage": 100})

    def test_negative_leverage(self):
        with pytest.raises(ValidationError, match="leverage must be >= 0"):
            _validate_set_leverage({"leverage": -1})

    def test_over_max_leverage(self):
        with pytest.raises(ValidationError, match="dangerously high"):
            _validate_set_leverage({"leverage": 101})

    def test_missing_leverage(self):
        with pytest.raises(ValidationError, match="leverage is required"):
            _validate_set_leverage({})
