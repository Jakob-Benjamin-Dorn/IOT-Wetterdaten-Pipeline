import os
from functools import lru_cache


@lru_cache(maxsize=32)
def get_parameter(name: str, *, with_decryption: bool = True) -> str:
    import boto3

    client = boto3.client("ssm")
    response = client.get_parameter(
        Name=name,
        WithDecryption=with_decryption,
    )
    return response["Parameter"]["Value"]


def get_required_secret_from_parameter_env(env_name: str) -> str:
    parameter_name = os.getenv(env_name)
    if parameter_name is None or parameter_name.strip() == "":
        raise RuntimeError(f"Missing required environment variable: {env_name}")

    return get_parameter(parameter_name, with_decryption=True)


def get_required_string_from_parameter_env(env_name: str) -> str:
    parameter_name = os.getenv(env_name)
    if parameter_name is None or parameter_name.strip() == "":
        raise RuntimeError(f"Missing required environment variable: {env_name}")

    return get_parameter(parameter_name, with_decryption=False)
