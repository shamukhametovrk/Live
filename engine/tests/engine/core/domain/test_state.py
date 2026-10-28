from engine.core.domain.ids import PlayerID
from engine.core.domain.state import Chamber, Shooting


def test_weight_counts_everyones_chips_plus_one():
    a, b = PlayerID(1), PlayerID(2)
    shooting = Shooting(
        chambers=(Chamber(False),) * 3,
        chips=frozendict({a: (2, 0, 1), b: (1, 0, 0)}),
        announced=1,
    )
    assert shooting.weights == (4, 1, 2)
