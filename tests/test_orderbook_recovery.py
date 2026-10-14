from unittest.mock import Mock, patch

import pytest

from poly_market_maker.order import Order, Side
from poly_market_maker.orderbook import OrderBookManager
from poly_market_maker.strategy import StrategyManager
from poly_market_maker.token import Token


class StopRefresh(BaseException):
    pass


def refresh_once(manager):
    with patch("poly_market_maker.orderbook.time.sleep", side_effect=StopRefresh), pytest.raises(StopRefresh):
        manager._thread_refresh_order_book()


@pytest.fixture
def manager():
    instance = OrderBookManager(1)
    yield instance
    instance._executor.shutdown()


def test_failed_initial_refresh_does_not_publish_an_empty_book(manager):
    manager.get_orders_with(Mock(side_effect=OSError("unavailable")))
    refresh_once(manager)
    assert manager._state is None
    assert manager._refresh_failed
    assert manager._refresh_count == 0


def test_failed_refresh_preserves_pending_orders_and_can_recover(manager):
    order = Order(1.0, 0.4, Side.BUY, Token.A, "pending")
    manager._state = {"orders": [], "balances": {Token.A: 10}}
    manager._orders_placed = [order]
    manager.get_orders_with(Mock(side_effect=OSError("unavailable")))
    refresh_once(manager)
    book = manager.get_order_book()
    assert book.orders == [order]
    assert not book.is_fresh
    assert manager._orders_placed == [order]
    manager.get_orders_with(lambda: [order])
    manager.get_balances_with(lambda: {Token.A: 10})
    refresh_once(manager)
    assert manager.get_order_book().is_fresh
    assert manager.get_order_book().orders == [order]
    assert manager._orders_placed == []


def test_failed_balance_refresh_keeps_the_entire_snapshot_unavailable(manager):
    manager.get_orders_with(lambda: [])
    manager.get_balances_with(Mock(side_effect=OSError("unavailable")))
    refresh_once(manager)
    assert manager._state is None
    assert manager._refresh_failed


def test_balance_callback_is_optional(manager):
    manager.get_orders_with(lambda: [])
    refresh_once(manager)
    assert manager.get_order_book().balances == {}
    assert manager.get_order_book().is_fresh


def test_stale_snapshot_cannot_generate_new_quotes(manager):
    manager._state = {"orders": [], "balances": {Token.A: 10}}
    manager._refresh_failed = True
    strategy = object.__new__(StrategyManager)
    strategy.logger = Mock()
    strategy.order_book_manager = manager
    strategy.get_token_prices = Mock()
    strategy.synchronize()
    strategy.get_token_prices.assert_not_called()
