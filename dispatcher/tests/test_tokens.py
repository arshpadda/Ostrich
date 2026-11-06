from src.tokens import mint

# Same vector as backend/tests/test_delivery_token.py: both ends must agree.
VECTOR = "2000.a756970eede380d3133a3552653b6f6aca184e613f5cbc349f96f4464b609deb"


def test_matches_control_plane_vector():
    assert mint("s3cret", "sb-1", "m-1", ttl_seconds=60, now=1940) == VECTOR
