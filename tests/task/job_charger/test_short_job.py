from unittest.mock import patch

from app.task.job_charger import short_job as test_module


@patch(f"{test_module.__name__}.charge_short_job")
async def test_periodic_short_job_charger_run_forever(mock_charge_short_job):
    task = test_module.PeriodicShortJobCharger(name="test-short-job-charger")
    await task.run_forever(limit=1)
    assert mock_charge_short_job.call_count == 1
    assert task.get_stats() == {
        "counter": 1,
        "success": 1,
        "failure": 0,
    }

    mock_charge_short_job.reset_mock()
    mock_charge_short_job.side_effect = Exception("Test error")
    task.reset_stats()
    await task.run_forever(limit=1)
    assert mock_charge_short_job.call_count == 1
    assert task.get_stats() == {
        "counter": 1,
        "success": 0,
        "failure": 1,
    }
