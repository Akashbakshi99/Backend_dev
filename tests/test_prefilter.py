from app.schemas import InboundForm
from app.services.prefilter import normalize, is_junk


def test_normalize_trims_whitespace():
    form = InboundForm(name="  Jane  ", email="jane@acme.com", message="  hi there  ")
    lead = normalize(form)
    assert lead.name == "Jane"
    assert lead.message == "hi there"


def test_is_junk_true_for_empty_message():
    form = InboundForm(name="Jane", email="jane@acme.com", message="   ")
    assert is_junk(normalize(form)) is True


def test_is_junk_false_for_real_message():
    form = InboundForm(name="Jane", email="jane@acme.com", message="I want a website")
    assert is_junk(normalize(form)) is False
