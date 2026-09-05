from pathlib import Path


def test_application_and_infrastructure_share_non_cancelling_release_queue() -> None:
    workflows = Path(__file__).resolve().parents[3] / ".github" / "workflows"
    expected = (
        "concurrency:\n"
        "  group: application-deploy-${{ github.ref_name }}\n"
        "  cancel-in-progress: false\n"
        "  queue: max\n"
    )
    for name in ("application-cd.yml", "infrastructure-cd.yml"):
        source = (workflows / name).read_text(encoding="utf-8")
        assert expected in source, name
