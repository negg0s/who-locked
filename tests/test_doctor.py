from who_locked.doctor import check_is_admin, check_restart_manager, run_diagnostics


def test_doctor_diagnostics_structure():
    data = run_diagnostics()
    assert "ready" in data
    assert "is_admin" in data
    assert "checks" in data
    assert "platform" in data["checks"]
    assert "restart_manager" in data["checks"]
    assert "privileges" in data["checks"]
    assert "context_menu" in data["checks"]


def test_restart_manager_check():
    # On Windows, restart manager check should return a boolean
    result = check_restart_manager()
    assert isinstance(result, bool)


def test_admin_check():
    result = check_is_admin()
    assert isinstance(result, bool)
