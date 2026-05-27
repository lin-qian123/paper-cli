from paper_cli.converters.mineru_jobs import resolve_local_jobs


def test_resolve_local_jobs_cli_overrides_config():
    assert resolve_local_jobs({"mineru": {"local_jobs": 1}}, cli_jobs=3, pending_count=10) == 3


def test_resolve_local_jobs_honors_config_integer():
    assert resolve_local_jobs({"mineru": {"local_jobs": 2}}, cli_jobs=None, pending_count=10) == 2


def test_resolve_local_jobs_auto_is_conservative():
    assert resolve_local_jobs({"mineru": {"local_jobs": "auto"}}, cli_jobs=None, pending_count=10) == 1


def test_resolve_local_jobs_never_exceeds_pending_count():
    assert resolve_local_jobs({"mineru": {"local_jobs": 10}}, cli_jobs=None, pending_count=2) == 2


def test_resolve_local_jobs_defaults_to_one_without_config():
    assert resolve_local_jobs({}, cli_jobs=None, pending_count=0) == 1
