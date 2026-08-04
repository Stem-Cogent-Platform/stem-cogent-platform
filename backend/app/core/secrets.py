import json
from functools import lru_cache
from typing import Any

from app.core.config import get_settings


class SecretConfigurationError(RuntimeError):
    """Raised when a managed secret does not match its runtime contract."""


def _secretsmanager_client(region_name: str) -> Any:
    # Import lazily so local-only commands that do not resolve managed secrets
    # can still load application configuration before dependencies are synced.
    import boto3

    return boto3.client("secretsmanager", region_name=region_name)


@lru_cache(maxsize=32)
def get_secret_string(secret_arn: str) -> str:
    """Fetch and cache one Secrets Manager value without exposing it to logs."""
    client = _secretsmanager_client(get_settings().AWS_REGION)
    response = client.get_secret_value(SecretId=secret_arn)
    secret_string = response.get("SecretString")
    if not isinstance(secret_string, str) or not secret_string:
        raise SecretConfigurationError("Secrets Manager value must be a non-empty string")
    return secret_string


@lru_cache(maxsize=16)
def get_json_secret(secret_arn: str) -> dict[str, Any]:
    """Resolve a JSON object secret and reject malformed scalar payloads."""
    try:
        value = json.loads(get_secret_string(secret_arn))
    except json.JSONDecodeError as error:
        raise SecretConfigurationError("Secrets Manager value must contain valid JSON") from error

    if not isinstance(value, dict):
        raise SecretConfigurationError("Secrets Manager JSON value must be an object")
    return value
