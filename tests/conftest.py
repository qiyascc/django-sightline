###############
# Qiyas Sadıqov CC
###############

import os

import django
import pytest

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "tests.settings")
django.setup()


@pytest.fixture(autouse=True)
def _fresh_cache():
    """Throttle counters live in the cache; start every test from zero."""
    from django.core.cache import caches
    for cache in caches.all():
        cache.clear()
    yield
