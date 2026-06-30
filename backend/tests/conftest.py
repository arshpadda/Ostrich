import os

import pytest
from tortoise.contrib.test import finalizer, initializer

os.environ["PROJECT_ID"] = "test"
os.environ["DATABASE_URL"] = "sqlite://:memory:"
os.environ["GENERATE_SCHEMAS"] = "True"


@pytest.fixture(scope="session", autouse=True)
def initialize_tests(request):
    initializer(modules=["src.controlplane.database.models"], db_url="sqlite://:memory:")
    request.addfinalizer(finalizer)
