"""Operator configuration is authority; remote metadata and model output are not."""

import ipaddress
import re
from typing import Literal
from urllib.parse import urlsplit

from pydantic import Field, field_validator, model_validator

from ..schemas import StrictModel
from .schema import ConnectorError, check_schema, digest

PROTOCOL_VERSION = "2025-11-25"


def validate_endpoint(endpoint):
    try:
        parsed = urlsplit(endpoint)
        host = parsed.hostname
        try:
            ipaddress.ip_address(host or "")
        except ValueError:
            pass
        else:
            raise ValueError()
        if (
            parsed.scheme != "https"
            or not host
            or parsed.username
            or parsed.password
            or parsed.query
            or parsed.fragment
            or parsed.port not in (None, 443)
            or not re.fullmatch(r"[a-z0-9.-]+", host)
            or host.endswith(".")
            or "." not in host
            or ".." in host
            or len(endpoint) > 1024
            or not re.fullmatch(r"/[A-Za-z0-9/_~.%-]*", parsed.path)
            or parsed.netloc != host
        ):
            raise ValueError()
    except ValueError:
        raise ConnectorError("CONNECTOR_ENDPOINT_DENIED", 422) from None
    return endpoint


class ToolGrant(StrictModel):
    tool_name: str = Field(pattern=r"^[A-Za-z0-9_.-]{1,128}$")
    descriptor_sha256: str = Field(pattern=r"^[a-f0-9]{64}$")
    effect: Literal["read", "write"]
    input_schema: dict
    destination_scope: str = Field(min_length=1, max_length=500)
    data_policy: Literal["public_or_synthetic"] = "public_or_synthetic"

    @field_validator("input_schema")
    @classmethod
    def bounded_schema(cls, value):
        check_schema(value)
        return value


class ConnectorConfig(StrictModel):
    id: str = Field(pattern=r"^[a-z][a-z0-9_-]{0,39}$")
    endpoint: str
    server_name: str = Field(min_length=1, max_length=128)
    server_version: str = Field(min_length=1, max_length=128)
    tools: list[ToolGrant] = Field(default_factory=list, max_length=32)

    @field_validator("endpoint")
    @classmethod
    def exact_https(cls, value):
        return validate_endpoint(value)

    @model_validator(mode="after")
    def unique_names(self):
        if len({t.tool_name for t in self.tools}) != len(self.tools):
            raise ValueError("Duplicate grant")
        return self

    def grant_id(self, grant):
        return f"mcp.{self.id}.{grant.tool_name}"

    def fingerprint(self, grant):
        return digest(
            {"connector": self.model_dump(exclude={"tools"}), "grant": grant.model_dump()}
        )


class ConnectorCall(StrictModel):
    arguments: dict
    public_only: Literal[True]

    @field_validator("public_only", mode="before")
    @classmethod
    def explicit_boolean(cls, value):
        if value is not True:
            raise ValueError("Explicit public/synthetic data acknowledgment required")
        return value


def load_connector_configs(path):
    """Read only an operator-supplied JSON file, without environment/auth substitution."""
    import os
    import stat
    from .schema import parse_json

    try:
        fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
        with os.fdopen(fd, "rb") as source:
            info = os.fstat(source.fileno())
            if (
                not stat.S_ISREG(info.st_mode)
                or info.st_nlink != 1
                or info.st_mode & 0o022
                or info.st_size > 65536
            ):
                raise ConnectorError("CONNECTOR_CONFIG_UNSAFE", 422)
            raw = source.read(65537)
        if len(raw) > 65536:
            raise ConnectorError("CONNECTOR_CONFIG_LIMIT", 422)
        values = parse_json(raw)
        if type(values) is not list or len(values) > 8:
            raise ConnectorError("CONNECTOR_CONFIG_INVALID", 422)
        return [ConnectorConfig.model_validate(value) for value in values]
    except OSError:
        raise ConnectorError("CONNECTOR_CONFIG_UNAVAILABLE", 422) from None
