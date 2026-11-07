"""Fixed Pi-to-owned-VPS OpenAI transport configuration, no model credentials."""

import shlex


def authorize_openai(existing):
    lines = existing.splitlines(keepends=True)
    keys = [i for i, line in enumerate(lines) if " ssh-ed25519 " in line]
    if len(keys) != 1:
        raise ValueError("Review the dedicated Pi relay key before changing its scope")
    index = keys[0]
    options, public = lines[index].split(" ssh-ed25519 ", 1)
    for required in (
        "restrict,",
        "port-forwarding,",
        'command="/bin/false"',
        'permitlisten="127.0.0.1:22073"',
    ):
        if required not in options:
            raise ValueError("Unexpected relay key constraints")
    if options.count("permitopen=") != 1:
        raise ValueError("Unexpected existing forward grants")
    if 'permitopen="api.openai.com:443"' not in options:
        if 'permitopen="127.0.0.1:9"' not in options:
            raise ValueError("An unrelated forward grant must not be overwritten")
        options = options.replace('permitopen="127.0.0.1:9"', 'permitopen="api.openai.com:443"')
    lines[index] = options + " ssh-ed25519 " + public
    return "".join(lines)


def units():
    key_root = "/home/desk/.config/desk-companion/owner-relay"
    command = [
        "/usr/bin/ssh",
        "-N",
        "-T",
        "-a",
        "-F",
        "/dev/null",
        "-i",
        key_root + "/id_ed25519",
        "-p",
        "22422",
        "-o",
        "BatchMode=yes",
        "-o",
        "IdentitiesOnly=yes",
        "-o",
        "IdentityAgent=none",
        "-o",
        "StrictHostKeyChecking=yes",
        "-o",
        "CheckHostIP=no",
        "-o",
        "UserKnownHostsFile=" + key_root + "/known_hosts",
        "-o",
        "HostKeyAlias=desk-owner-relay-vps",
        "-o",
        "UpdateHostKeys=no",
        "-o",
        "ProxyCommand=none",
        "-o",
        "ExitOnForwardFailure=yes",
        "-o",
        "ConnectTimeout=10",
        "-o",
        "ServerAliveInterval=20",
        "-o",
        "ServerAliveCountMax=3",
        "-L",
        "127.0.0.1:18443:api.openai.com:443",
        "fyp-pi-relay@127.0.0.1",
    ]
    hardening = """Restart=on-failure
RestartSec=10
User=desk
Group=desk
NoNewPrivileges=yes
PrivateTmp=yes
ProtectSystem=strict
ProtectHome=read-only
RestrictAddressFamilies=AF_UNIX AF_INET AF_INET6
[Install]
WantedBy=multi-user.target
"""
    return {
        "desk-openai-forward.service": """[Unit]
Description=Fixed OpenAI forward through the existing owned VPS transport
Wants=network-online.target desk-relay-transport.service
After=network-online.target desk-relay-transport.service
StartLimitIntervalSec=0
[Service]
Type=simple
ExecStart="""
        + shlex.join(command)
        + "\n"
        + hardening,
        "desk-openai-connect.service": """[Unit]
Description=Loopback OpenAI-only CONNECT bridge
Wants=desk-openai-forward.service
After=desk-openai-forward.service
StartLimitIntervalSec=0
[Service]
Type=simple
ExecStart=/usr/bin/python3 /usr/local/lib/desk-openai-connect.py
"""
        + hardening,
    }
