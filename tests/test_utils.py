from app import utils as test_module


def test_timer():
    with test_module.Timer() as timer:
        elapsed_1 = timer.elapsed
        elapsed_2 = timer.elapsed
    elapsed_3 = timer.elapsed
    elapsed_4 = timer.elapsed

    assert 0 < elapsed_1 < elapsed_2 < elapsed_3
    assert elapsed_3 == elapsed_4
