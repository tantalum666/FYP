import pytest
from desk.store import DomainError
from desk.tasks import TaskInput
from test_agent_runs import world as world, start, drive


def make_required(world):
    run = start(world, mutation_requests=[{'tool': 'task_create_draft', 'arguments': {'title': 'REQUIRED_EXPECTED_TASK'}, 'required': True}])
    waiting = drive(world, run)
    assert waiting['state'] == 'waiting_review'
    return run, waiting['proposal_ids'][0]


def test_different_task_under_confirmation_key_cannot_satisfy_required_change(world):
    runtime = world[0]
    run, pid = make_required(world)
    with pytest.raises(DomainError, match='RUN_EFFECT_RECEIPT_CONFLICT'):
        runtime.tasks.create(TaskInput(title='UNRELATED_DIFFERENT_TASK'), 'assistant-confirm/' + pid)
    assert runtime.tasks.listing()['tasks'] == []


def test_existing_historical_mismatched_receipt_does_not_satisfy_required_change(world):
    runtime = world[0]
    run, pid = make_required(world)
    # Simulate an existing legacy receipt produced before the guard fix. No live I/O.
    guard = runtime.store.operation_guard
    runtime.store.operation_guard = None
    try:
        runtime.tasks.create(TaskInput(title='UNRELATED_DIFFERENT_TASK'), 'assistant-confirm/' + pid)
    finally:
        runtime.store.operation_guard = guard
    finished = drive(world, run)
    assert finished['state'] != 'succeeded', finished
    assert finished['effects'][0]['state'] == 'unknown'
