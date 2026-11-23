"""Golden dataset as pytest cases (same dataset and checks as golden_dataset/runner.py).

LLM answers are stochastic: a failing case is retried twice before it counts.
Needs the agent running (`docker compose up adk-web`); skipped otherwise.

    cd agent && uv run pytest tests/test_golden.py -v
"""
from __future__ import annotations

from urllib.error import URLError
from urllib.request import urlopen

import pytest

from golden_dataset.runner import ADK_URL, ask, check, load_cases


def _agent_up() -> bool:
    try:
        with urlopen(f"{ADK_URL}/list-apps", timeout=3) as resp:
            return resp.status == 200
    except (URLError, OSError):
        return False


pytestmark = pytest.mark.skipif(
    not _agent_up(), reason=f"agent not reachable at {ADK_URL} — run `docker compose up adk-web`"
)


@pytest.mark.flaky(reruns=2, reruns_delay=3)
@pytest.mark.parametrize("case", load_cases(), ids=lambda c: c["id"])
def test_golden(case: dict) -> None:
    answer = ask(case["question"])
    errors = check(answer, case["expect"])
    assert not errors, f"{case['id']}: {'; '.join(errors)}\nanswer: {answer.text[:400]}"
