from todoctl.parser import parse_month
from todoctl.models import Status

def test_parse_plain_line():
    doc = parse_month("Test task\n", "2026-03")
    assert len(doc.tasks) == 1
    assert doc.tasks[0].status == Status.OPEN

def test_parse_structured_line():
    doc = parse_month("[2] [DONE] Hello\n", "2026-03")
    assert doc.tasks[0].id == 2
    assert doc.tasks[0].status == Status.DONE
