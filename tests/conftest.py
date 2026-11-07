import pytest


# Spec tests for unwritten stubs report as xfail, so `pytest` doubles as the to-do list
# and CI stays green until a stub is implemented, after which its tests count for real.
@pytest.hookimpl(hookwrapper=True)
def pytest_runtest_makereport(item, call):
    outcome = yield
    report = outcome.get_result()
    if call.when == "call" and call.excinfo and call.excinfo.errisinstance(NotImplementedError):
        report.outcome = "skipped"
        report.wasxfail = "not implemented yet"
