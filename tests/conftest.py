import pytest

from backend_python.security import reset_security_state


@pytest.fixture(autouse=True)
def reset_security_state_between_tests() -> None:
    reset_security_state()
