import pytest
import requests

import extract
from extract import MAX_ATTEMPTS, RETRY_WAIT_SECONDS, fetch_city_day


class GoodResponse:
    text = '{"ok": true}'

    def raise_for_status(self):
        pass


class BadRequestResponse:
    text = "bad request"

    def raise_for_status(self):
        raise requests.exceptions.HTTPError("400 Client Error")


def install_fakes(monkeypatch, outcomes):
    """Make requests.get return/raise `outcomes` in order. Return (calls, sleeps)."""
    calls = []
    sleeps = []
    remaining = iter(outcomes)

    def fake_get(url, params=None, timeout=None):
        calls.append(params)
        outcome = next(remaining)
        if isinstance(outcome, Exception):
            raise outcome
        return outcome

    monkeypatch.setattr(extract.requests, "get", fake_get)
    monkeypatch.setattr(extract.time, "sleep", sleeps.append)
    return calls, sleeps


def test_succeeds_after_two_timeouts_with_doubling_wait(monkeypatch):
    calls, sleeps = install_fakes(monkeypatch, [
        requests.exceptions.Timeout(),
        requests.exceptions.Timeout(),
        GoodResponse(),
    ])
    result = fetch_city_day(12.9, 74.8, "2026-10-05")
    assert result == '{"ok": true}'
    assert len(calls) == 3
    assert sleeps == [RETRY_WAIT_SECONDS, RETRY_WAIT_SECONDS * 2]


def test_gives_up_after_max_attempts(monkeypatch):
    calls, sleeps = install_fakes(monkeypatch, [
        requests.exceptions.ConnectionError() for _ in range(MAX_ATTEMPTS)
    ])
    with pytest.raises(requests.exceptions.ConnectionError):
        fetch_city_day(12.9, 74.8, "2026-10-05")
    assert len(calls) == MAX_ATTEMPTS
    assert len(sleeps) == MAX_ATTEMPTS - 1


def test_client_error_is_not_retried(monkeypatch):
    calls, sleeps = install_fakes(monkeypatch, [BadRequestResponse()])
    with pytest.raises(requests.exceptions.HTTPError):
        fetch_city_day(12.9, 74.8, "2026-10-05")
    assert len(calls) == 1
    assert sleeps == []