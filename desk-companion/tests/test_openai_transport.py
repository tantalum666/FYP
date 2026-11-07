import asyncio
from types import SimpleNamespace

import pytest

from desk.openai_transport import model_proxy, validate_openai_proxy
from desk.text_ai import TextConfig
from desk.voice import VoiceConfig
from scripts.pi.openai_connect import ConnectBridge
from scripts.pi.setup_openai_tunnel import authorize_openai, units


@pytest.mark.parametrize(
    "value",
    [
        "http://evil.test:17891",
        "http://localhost:17891",
        "http://127.0.0.1:80",
        "http://127.0.0.1:65536",
        "http://user@127.0.0.1:17891",
        "http://127.0.0.1:17891/",
        "https://127.0.0.1:17891",
        "http://127.0.0.2:17891",
        "http://127.0.0.1:17891\n",
    ],
)
def test_only_explicit_loopback_proxy_is_accepted(value):
    with pytest.raises(ValueError):
        validate_openai_proxy(value)


def test_scope_and_offline_transport_take_precedence():
    config = SimpleNamespace(provider="openai", proxy_url="http://127.0.0.1:17891")
    assert model_proxy(config) == config.proxy_url
    assert model_proxy(config, transport=object()) is None
    config.provider = "qwen"
    assert model_proxy(config) is None


def test_bad_transport_makes_both_openai_configs_unavailable(monkeypatch):
    monkeypatch.setenv("DESK_OPENAI_PROXY_URL", "http://elsewhere.test:1234")
    monkeypatch.setenv("OPENAI_API_KEY", "fake-test-key")
    monkeypatch.delenv("DESK_OPENAI_REGION_UNSUPPORTED", raising=False)
    monkeypatch.delenv("DESK_OPENAI_CREDENTIAL_FILE", raising=False)
    for config in [TextConfig.environment(), VoiceConfig.environment()]:
        assert config.configuration_error == "OPENAI_PROXY_INVALID" and not config.valid()


def test_vps_grant_preserves_identity_and_restricts_the_only_destination():
    before = 'restrict,port-forwarding,command="/bin/false",permitlisten="127.0.0.1:22073",permitopen="127.0.0.1:9" ssh-ed25519 AAAATEST dedicated-pi\n'
    after = authorize_openai(before)
    assert after.split(" ssh-ed25519 ")[1] == before.split(" ssh-ed25519 ")[1]
    assert 'permitopen="api.openai.com:443"' in after
    assert authorize_openai(after) == after
    with pytest.raises(ValueError):
        authorize_openai(before.replace("127.0.0.1:9", "unrelated.test:443"))
    with pytest.raises(ValueError):
        authorize_openai(before + before)
    config = units()
    forward = config["desk-openai-forward.service"]
    assert "-L 127.0.0.1:18443:api.openai.com:443" in forward
    assert "StrictHostKeyChecking=yes" in forward and "-D " not in forward
    assert "NoNewPrivileges=yes" in forward


@pytest.mark.parametrize("host", [b"api.openai.com:443", b"api.openai.com"])
def test_connect_bridge_rejects_other_hosts_and_passes_tls_bytes_unchanged(host):
    async def run():
        calls = []

        async def upstream(reader, writer):
            calls.append(True)
            data = await reader.read(100)
            writer.write(data)
            await writer.drain()
            writer.close()
            await writer.wait_closed()

        remote = await asyncio.start_server(upstream, "127.0.0.1", 0)
        bridge = ConnectBridge(remote.sockets[0].getsockname()[1])
        server = await asyncio.start_server(bridge.client, "127.0.0.1", 0, limit=8192)
        port = server.sockets[0].getsockname()[1]
        try:
            for request in [
                b"CONNECT example.com:443 HTTP/1.1\r\n\r\n",
                b"CONNECT api.openai.com:80 HTTP/1.1\r\n\r\n",
                b"GET https://api.openai.com/v1/models HTTP/1.1\r\n\r\n",
                b"CONNECT api.openai.com:443 HTTP/1.1\r\nHost: other.test\r\n\r\n",
            ]:
                reader, writer = await asyncio.open_connection("127.0.0.1", port)
                writer.write(request)
                await writer.drain()
                assert (await reader.read(512)).startswith(b"HTTP/1.1 403")
                writer.close()
                await writer.wait_closed()
            assert not calls
            reader, writer = await asyncio.open_connection("127.0.0.1", port)
            writer.write(b"CONNECT api.openai.com:443 HTTP/1.1\r\nHost: " + host + b"\r\n\r\n")
            await writer.drain()
            assert (await reader.readuntil(b"\r\n\r\n")).startswith(b"HTTP/1.1 200")
            opaque = b"\x16\x03\x01opaque-tls-record"
            writer.write(opaque)
            await writer.drain()
            assert await reader.readexactly(len(opaque)) == opaque
            writer.close()
            await writer.wait_closed()
            assert len(calls) == 1
        finally:
            server.close()
            remote.close()
            await server.wait_closed()
            await remote.wait_closed()

    asyncio.run(run())
