from random import Random

from engine.core.domain.rules.round import start_round
from engine.core.domain.state import RoundResult, Settings
from tests.engine.core.domain.rules.helpers import A, B, C


def test_first_is_whoever_started_fewest_rounds():
    results = (RoundResult(A, B), RoundResult(B, A), RoundResult(A, C))
    for s in range(20):
        r, _ = start_round(Settings(), (A, B, C), results, Random(s))
        assert r.first == r.active == C


def test_withdrawn_players_are_left_out():
    r, _ = start_round(Settings(), (A, C), (), Random(0))
    assert set(r.circle) == set(r.seats) == {A, C}
    assert all(s.health == r.start_health for s in r.seats.values())
