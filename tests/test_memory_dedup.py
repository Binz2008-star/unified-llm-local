import hashlib, re
def _fp(s): return hashlib.sha256(re.sub(r'\s+', ' ', s.strip()).encode()).hexdigest()
def test_fingerprint_normalizes_ws():
    assert _fp("hello   world") == _fp("hello world")
    assert _fp("  hello world  \n") == _fp("hello world")
    assert _fp("Hello World") != _fp("hello world")  # case-sensitive via ws only, but our impl is case-sensitive? adjust
def test_fingerprint_stable():
    a = "Task: hello\nPlan: foo"
    assert _fp(a) == _fp(a)
    assert len(_fp(a)) == 64
