from pathlib import Path
import re


REPOSITORY_ROOT = Path(__file__).resolve().parents[3]


def test_managed_provider_secret_arns_are_wired_into_every_runtime_environment() -> (
    None
):
    expected = {
        "OPENAI_API_KEY_ARN": "openai_api_key",
        "GROQ_API_KEY_ARN": "groq_api_key",
        "RESEND_API_KEY_ARN": "resend_api_key",
        "GOOGLE_OAUTH_CREDENTIALS_ARN": "google_oauth_credentials",
        "LINKEDIN_OAUTH_CREDENTIALS_ARN": "linkedin_oauth_credentials",
    }

    for environment in ("staging", "prod"):
        source = (
            REPOSITORY_ROOT
            / "infrastructure"
            / "terraform"
            / "environments"
            / environment
            / "ecs.tf"
        ).read_text(encoding="utf-8")

        for variable, secret_name in expected.items():
            declaration = (
                rf'{variable}\s*=\s*module\.secrets\.secret_arns\["{secret_name}"\]'
            )
            assert len(re.findall(declaration, source)) == 1
