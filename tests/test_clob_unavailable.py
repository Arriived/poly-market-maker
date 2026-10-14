import logging
from unittest.mock import Mock

import pytest

from poly_market_maker.clob_api import ClobApi


@pytest.fixture
def api():
    instance = object.__new__(ClobApi)
    instance.logger = logging.getLogger("test.clob")
    instance.client = Mock()
    return instance


def test_failed_order_fetch_is_not_reported_as_an_empty_account(api):
    api.client.get_orders.side_effect = OSError("unavailable")
    with pytest.raises(OSError, match="unavailable"):
        api.get_orders("market")


def test_failed_midpoint_fetch_never_invents_a_random_price(api):
    api.client.get_midpoint.side_effect = OSError("unavailable")
    with pytest.raises(OSError, match="unavailable"):
        api.get_price(1)


@pytest.mark.parametrize("mid", [None, "nan", "inf", "0", "1", "-0.1"])
def test_missing_or_invalid_midpoints_are_unavailable(api, mid):
    api.client.get_midpoint.return_value = {"mid": mid}
    with pytest.raises(ValueError):
        api.get_price(1)


def test_valid_midpoint_is_returned(api):
    api.client.get_midpoint.return_value = {"mid": "0.42"}
    assert api.get_price(1) == 0.42
