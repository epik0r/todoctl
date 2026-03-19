from todoctl.resolver import resolve_month

def test_resolve_month_numeric():
    result = resolve_month("3")
    assert result.endswith("-03")

def test_resolve_month_full():
    assert resolve_month("2026-03") == "2026-03"
