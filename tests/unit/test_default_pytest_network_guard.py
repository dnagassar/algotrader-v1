import os
import socket

import pytest

from conftest import (
    NETWORK_BLOCK_MESSAGE,
    NETWORK_TESTS_FLAG,
    _network_tests_allowed,
)


class _FakePytestConfig:
    def __init__(self, *, allow_network: bool = False) -> None:
        self.allow_network = allow_network

    def getoption(self, name: str, default: object = None) -> object:
        if name == "allow_network":
            return self.allow_network
        return default


def test_socket_creation_is_blocked_in_normal_pytest(pytestconfig) -> None:
    if _network_tests_allowed(pytestconfig, os.environ):
        pytest.skip("network guard intentionally disabled by explicit test config")

    with pytest.raises(RuntimeError) as exc_info:
        socket.socket()

    assert str(exc_info.value) == NETWORK_BLOCK_MESSAGE
    assert "offline and credential-free" in str(exc_info.value)


def test_socket_create_connection_is_blocked_in_normal_pytest(pytestconfig) -> None:
    if _network_tests_allowed(pytestconfig, os.environ):
        pytest.skip("network guard intentionally disabled by explicit test config")

    with pytest.raises(RuntimeError) as exc_info:
        socket.create_connection(("127.0.0.1", 9), timeout=0)

    assert str(exc_info.value) == NETWORK_BLOCK_MESSAGE


def test_network_escape_hatch_is_disabled_by_default() -> None:
    assert _network_tests_allowed(_FakePytestConfig(), {}) is False


def test_network_escape_hatch_can_be_enabled_by_cli_flag() -> None:
    assert _network_tests_allowed(_FakePytestConfig(allow_network=True), {}) is True


def test_network_escape_hatch_can_be_enabled_by_environment_flag() -> None:
    assert (
        _network_tests_allowed(
            _FakePytestConfig(),
            {NETWORK_TESTS_FLAG: "1"},
        )
        is True
    )


def test_network_escape_hatch_rejects_non_enabled_environment_values() -> None:
    assert (
        _network_tests_allowed(
            _FakePytestConfig(),
            {NETWORK_TESTS_FLAG: "0"},
        )
        is False
    )
