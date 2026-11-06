from src.controlplane.core import delivery_token as dt

# Fixed vector, duplicated in dispatcher/tests/test_tokens.py so both sides stay in sync.
VECTOR = "2000.a756970eede380d3133a3552653b6f6aca184e613f5cbc349f96f4464b609deb"


def test_roundtrip_and_binding():
    tok = dt.mint("s3cret", "sb-1", "m-1", ttl_seconds=60, now=1000)
    assert dt.verify("s3cret", tok, "sb-1", "m-1", now=1030)
    assert not dt.verify("s3cret", tok, "sb-2", "m-1", now=1030)  # wrong sandbox
    assert not dt.verify("s3cret", tok, "sb-1", "m-2", now=1030)  # wrong message
    assert not dt.verify("other", tok, "sb-1", "m-1", now=1030)  # wrong key


def test_expiry_and_garbage():
    tok = dt.mint("s3cret", "sb-1", "m-1", ttl_seconds=60, now=1000)
    assert not dt.verify("s3cret", tok, "sb-1", "m-1", now=1061)
    assert not dt.verify("s3cret", "nonsense", "sb-1", "m-1", now=1000)
    assert not dt.verify("", tok, "sb-1", "m-1", now=1030)  # unset secret fails closed


def test_fixed_vector():
    assert dt.mint("s3cret", "sb-1", "m-1", ttl_seconds=60, now=1940) == VECTOR
