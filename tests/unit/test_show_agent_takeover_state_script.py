from pathlib import Path


def test_show_agent_takeover_state_is_read_only_and_credential_value_safe() -> None:
    script = Path("scripts/dev/show_agent_takeover_state.ps1").read_text(encoding="utf-8")

    required = (
        "git branch --show-current",
        "git rev-parse HEAD",
        "git status --short",
        "git diff --cached --name-only",
        "git diff --name-only",
        "git ls-files --others --exclude-standard src tests scripts docs",
        "git ls-files runs",
        "active_implementation.md",
        "credential_variables_present",
    )
    forbidden = (
        "Set-Content",
        "Add-Content",
        "Out-File",
        "Remove-Item",
        "Move-Item",
        "Invoke-WebRequest",
        "Invoke-RestMethod",
        "algotrader.cli",
        "ALPACA_API_KEY=",
        "ALPACA_API_SECRET_KEY=",
        "ALPACA_SECRET_KEY=",
    )

    assert all(token in script for token in required)
    assert all(token not in script for token in forbidden)
