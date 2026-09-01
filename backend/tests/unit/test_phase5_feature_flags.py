from app.core.config import Settings


PHASE5_FLAGS = (
    "PHASE5_PILOT_INVITES_ENABLED",
    "PHASE5_FIRST_VALUE_ACTIVATION_ENABLED",
    "PHASE5_BRIEF_LIFECYCLE_ENABLED",
    "PHASE5_DECISION_PATHS_ENABLED",
    "PHASE5_NEW_UI_ENABLED",
    "PHASE5_PRODUCT_ANALYTICS_ENABLED",
)


def test_phase5_flags_fail_closed_by_default() -> None:
    settings = Settings(_env_file=None)

    assert all(getattr(settings, name) is False for name in PHASE5_FLAGS)


def test_phase5_flags_can_be_enabled_independently() -> None:
    settings = Settings(
        _env_file=None,
        PHASE5_PILOT_INVITES_ENABLED=True,
        PHASE5_DECISION_PATHS_ENABLED=True,
    )

    assert settings.PHASE5_PILOT_INVITES_ENABLED is True
    assert settings.PHASE5_DECISION_PATHS_ENABLED is True
    assert settings.PHASE5_FIRST_VALUE_ACTIVATION_ENABLED is False
