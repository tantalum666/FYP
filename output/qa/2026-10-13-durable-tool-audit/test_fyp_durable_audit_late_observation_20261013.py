from test_agent_runs import world as world, action, detail
from test_agent_browser_tools import browser_world as browser_world, browser_start, planner
from test_browser_jobs import hidden


def test_late_child_observation_after_parent_cancel(browser_world, monkeypatch):
    world, fake = browser_world
    runtime = world[0]
    planner(world)
    run = browser_start(world)
    runtime.agent_runs.advance_one()
    original = runtime.browser_jobs._validate_observation
    changed = []

    def validation(value):
        original(value)
        if not changed:
            changed.append(True)
            action(world, run, 'cancel')

    monkeypatch.setattr(runtime.browser_jobs, '_validate_observation', validation)
    runtime.agent_runs.advance_one()
    current = detail(world, run)['run']
    assert current['state'] == 'cancelled' and current['evidence'] == []
    with runtime.store.connection() as conn:
        row = conn.execute('SELECT * FROM browser_observations').fetchone()
    assert row['state'] != 'observed', dict(row)


def test_late_child_observation_after_private_hide(browser_world, monkeypatch):
    world, fake = browser_world
    runtime = world[0]
    planner(world)
    run = browser_start(world)
    runtime.agent_runs.advance_one()
    original = runtime.browser_jobs._validate_observation
    changed = []

    def validation(value):
        original(value)
        if not changed:
            changed.append(True)
            hidden(runtime, True)

    monkeypatch.setattr(runtime.browser_jobs, '_validate_observation', validation)
    runtime.agent_runs.advance_one()
    with runtime.store.connection() as conn:
        current = runtime.agent_runs._get(conn, run['id'])
        row = conn.execute('SELECT * FROM browser_observations').fetchone()
    assert current['state'] == 'blocked' and current['evidence'] == []
    assert row['state'] != 'observed', dict(row)
