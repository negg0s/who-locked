import os
from who_locked.safety import is_safe_to_terminate


def test_safety_protected_pids():
    safe, msg = is_safe_to_terminate(0)
    assert safe is False
    assert "protected" in msg

    safe, msg = is_safe_to_terminate(4)
    assert safe is False
    assert "protected" in msg


def test_safety_current_pid():
    current_pid = os.getpid()
    safe, msg = is_safe_to_terminate(current_pid)
    assert safe is False
    assert "current who-locked" in msg


def test_safety_critical_names():
    safe, msg = is_safe_to_terminate(9999, "csrss.exe")
    assert safe is False
    assert "critical" in msg

    safe, msg = is_safe_to_terminate(9999, "lsass.exe")
    assert safe is False
    assert "critical" in msg


def test_safety_normal_process():
    safe, msg = is_safe_to_terminate(9999, "node.exe")
    assert safe is True
    assert msg is None
