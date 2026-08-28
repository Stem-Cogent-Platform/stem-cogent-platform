from pathlib import Path


REPOSITORY_ROOT = Path(__file__).resolve().parents[3]


def test_managed_provider_secret_arns_are_wired_into_every_runtime_environment() -> None:
    expected = (
        'OPENAI_API_KEY_ARN          = module.secrets.secret_arns["openai_api_key"]',
        'GROQ_API_KEY_ARN            = module.secrets.secret_arns["groq_api_key"]',
        'RESEND_API_KEY_ARN          = module.secrets.secret_arns["resend_api_key"]',
    )

    for environment in ("staging", "prod"):
        source = (
            REPOSITORY_ROOT
            / "infrastructure"
            / "terraform"
            / "environments"
            / environment
            / "ecs.tf"
        ).read_text(encoding="utf-8")

        for declaration in expected:
            assert source.count(declaration) == 1
