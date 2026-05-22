---
paths:
  - "conftest.py"
  - "utils/report_generator.py"
  - "utils/log_config.py"
---

# Test Report Generation Strategy

Applies to: `pytest_sessionfinish` report generation logic in `conftest.py`, and the `utils/report_generator.py` report utility.

---

## 🔴 P0 · Generate HTML Report Only on Failure

**Trigger**: pytest session ends, report generation logic executes.

**Rule**: Skip HTML report generation when all test cases pass; only generate a report when there are failures (failed / broken / teardown error). Avoids accumulating meaningless "all-green" report files after every test run.

**Implementation pattern**: Module-level marker variable + hook detection + sessionfinish conditional judgment.

### Marker Variable Setting

`_has_failures` must be set at **any phase** (setup / call / teardown) where `report.failed` is True — not limited to call/setup only. Screenshot logic and marker logic must be decoupled.

❌ Anti-pattern: Marker coupled with screenshot, missing teardown failures

```python
def pytest_runtest_makereport(item, call):
    global _has_failures
    outcome = yield
    report = outcome.get_result()
    if report.when in ("call", "setup") and report.failed:
        _has_failures = True          # teardown failure won't set the marker
        try:
            ...screenshot...
        except Exception:
            pass
```

✅ Best practice: Marker decoupled from screenshot, covers all phases

```python
def pytest_runtest_makereport(item, call):
    global _has_failures
    outcome = yield
    report = outcome.get_result()
    if report.failed:                 # failure at any phase sets the marker
        _has_failures = True
    if report.when in ("call", "setup") and report.failed:
        try:
            ...screenshot...          # screenshots only for call/setup
        except Exception:
            pass
```

### sessionfinish Conditional Judgment

The report generation condition check must come after domain printing, before report generation. Domain statistics should always be output regardless of pass/fail (useful for diagnosing network issues).

❌ Anti-pattern: Unconditionally generate report

```python
def pytest_sessionfinish(session, exitstatus):
    ...domain printing...
    report_path = generate_html_report(results_dir, output_dir, env)  # generates even when all green
```

✅ Best practice: Only generate on failure

```python
def pytest_sessionfinish(session, exitstatus):
    ...domain printing...

    if not _has_failures:
        print("\n✅ All test cases passed, skipping HTML report generation")
        return

    ...report generation logic...
```

---

## 🟡 P1 · Report File Auto-Rotation

**Trigger**: `utils/report_generator.py` executes cleanup logic after generating a report.

**Rule**: Keep at most **10** `report_*.html` files under `reports/html/`; when exceeded, delete the oldest reports sorted by filename.

**Implementation location**: An independent cleanup method in `utils/report_generator.py`.

```python
def _cleanup_old_reports(output_dir: Path, max_count: int = 10):
    reports = sorted(output_dir.glob("report_*.html"))
    while len(reports) > max_count:
        reports.pop(0).unlink()
```

**Call timing**: Call after `generate_html_report()` successfully writes the new report, decoupled from report generation (cleanup failure doesn't affect report writing).

❌ Anti-pattern: Clean up before report generation (may delete unread reports)

✅ Best practice: Generate new report first → then clean up reports that exceed the limit

---

## 🟡 P2 · Run Log Recording

**Trigger**: Each time a pytest session starts.

**Rule**: Each run generates an independent log file `logs/test_run_<timestamp>.log`, and maintains a `logs/latest.log` symlink pointing to the latest log. Keep at most **100** log files.

**Implementation location**: The `setup_logging()` function in `utils/log_config.py`.

```python
def setup_logging(log_dir: str = "logs", max_files: int = 100) -> str:
    log_path = Path(log_dir)
    log_path.mkdir(exist_ok=True)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    log_file = log_path / f"test_run_{timestamp}.log"

    # Configure logging handler
    handler = logging.FileHandler(log_file, encoding="utf-8")
    handler.setFormatter(logging.Formatter(
        "%(asctime)s [%(levelname)s] %(name)s: %(message)s"
    ))
    logging.root.addHandler(handler)

    # Symlink
    latest = log_path / "latest.log"
    if latest.exists() or latest.is_symlink():
        latest.unlink()
    latest.symlink_to(log_file.name)

    # Rotation
    logs = sorted(log_path.glob("test_run_*.log"))
    while len(logs) > max_files:
        logs.pop(0).unlink()

    return str(log_file)
```

**Call timing**: Call in `conftest.py`'s `pytest_configure` hook.

```python
def pytest_configure(config):
    from utils.log_config import setup_logging
    setup_logging()
```

❌ Anti-pattern: Call in `pytest_sessionstart` (too late; fixture-level logs are lost)

✅ Best practice: Call in `pytest_configure` (earliest available pytest hook)

---

## Extension Points (Notes)

For future needs requiring more granular control (e.g. generate only on broken, decide per module):
- Use `session.testsfailed` (pytest built-in attribute) instead of manual marker
- Inside `generate_html_report`, decide whether to write the file based on stats
