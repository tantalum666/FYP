from uuid import uuid4
import pytest
from desk.agent_run_schemas import AgentDecision
from desk.memory import MemoryAction
from test_agent_context import context_world as context_world, memory, selection
from test_agent_personal_context_integration import start, action


@pytest.mark.parametrize('change', ['cancel', 'forget'])
def test_change_after_context_projection_prevents_new_provider_dispatch(context_world, monkeypatch, change):
    world = context_world
    runtime = world['runtime']
    remembered = memory(world, 'PRIVATE_PRE_DISPATCH_MARKER')
    run = start(world, selection(remembered))
    original = runtime.agent_runs.context_bridge.project
    sent = []

    def projection(*args, **kwargs):
        value = original(*args, **kwargs)
        if change == 'cancel':
            action(world, run, 'cancel')
        else:
            runtime.memories.action(remembered['id'], MemoryAction(action='forget', expected_version=1), uuid4().hex)
        return value

    monkeypatch.setattr(runtime.agent_runs.context_bridge, 'project', projection)
    runtime.text_ai.generate = lambda system, context, schema, purpose: sent.append(context) or AgentDecision(action='plan', plan=['Read source'])
    runtime.agent_runs.advance_one()
    with runtime.store.connection() as conn:
        current = runtime.agent_runs._get(conn, run['id'])
    assert current['state'] == ('cancelled' if change == 'cancel' else 'blocked')
    assert sent == [], f'Provider dispatch still occurred after {change}: {sent}'


@pytest.mark.parametrize('change', ['cancel', 'forget'])
def test_change_after_http_serialization_prevents_transport(context_world, monkeypatch, change):
    import httpx
    import desk.text_ai as module
    world = context_world
    runtime = world['runtime']
    remembered = memory(world, 'PRIVATE_TRANSPORT_MARKER')
    run = start(world, selection(remembered))
    original = module._request_checkpoint
    sent = []

    def hook(request):
        if change == 'cancel':
            action(world, run, 'cancel')
        else:
            runtime.memories.action(remembered['id'], MemoryAction(action='forget', expected_version=1), uuid4().hex)
        original(request)

    monkeypatch.setattr(module, '_request_checkpoint', hook)
    runtime.text_ai.transport = httpx.MockTransport(lambda request: sent.append(request) or httpx.Response(500))
    runtime.agent_runs.advance_one()
    with runtime.store.connection() as conn:
        current = runtime.agent_runs._get(conn, run['id'])
        attempts = [row['state'] for row in conn.execute('SELECT state FROM agent_attempts WHERE run_id=?', (run['id'],))]
    assert current['state'] == ('cancelled' if change == 'cancel' else 'blocked')
    assert sent == []
    assert attempts == ['dispatch_refused']
    assert current['state_reason'] != 'RUN_PROVIDER_OUTCOME_UNKNOWN'


def test_projection_refusal_is_known_not_dispatched(context_world, monkeypatch):
    world = context_world
    runtime = world['runtime']
    remembered = memory(world, 'PRIVATE_PROJECTION_MARKER')
    run = start(world, selection(remembered))
    original = runtime.agent_runs.context_bridge.project
    sent = []

    def projection(*args, **kwargs):
        runtime.memories.action(remembered['id'], MemoryAction(action='forget', expected_version=1), uuid4().hex)
        return original(*args, **kwargs)

    monkeypatch.setattr(runtime.agent_runs.context_bridge, 'project', projection)
    runtime.text_ai.generate = lambda *args: sent.append(True)
    runtime.agent_runs.advance_one()
    with runtime.store.connection() as conn:
        current = runtime.agent_runs._get(conn, run['id'])
        attempts = [row['state'] for row in conn.execute('SELECT state FROM agent_attempts WHERE run_id=?', (run['id'],))]
    assert sent == []
    assert current['state_reason'] != 'RUN_PROVIDER_OUTCOME_UNKNOWN', current['state_reason']
    assert attempts == ['dispatch_refused']
