# Development

## Getting the code

```bash
git clone https://github.com/qiyascc/django-sightline
cd django-sightline
python -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
```

The `dev` extra installs `pytest`, `pytest-django` and `ruff`.

## Layout

```text
src/sightline/
    collector.py       the write path: batches in, rows out
    conf.py            settings and defaults
    middleware.py      tracker and overlay injection
    models.py          the seven tables
    utils.py           visitor key, device, bots, paths, grid
    views.py           collect, panel, heat data, visits, replay
    admin.py           read only admin pages and the panel link
    urls.py
    management/commands/sightline_prune.py
    management/commands/sightline_stats.py
    static/sightline/js/tracker.js   the recorder
    static/sightline/js/overlay.js   the live heatmap
    static/sightline/js/replay.js    the player
    static/sightline/css/sightline.css
    templates/sightline/
tests/
    settings.py        a minimal project for the test run
    urls.py
    test_sightline.py
docs/                  this documentation
```

## Running the tests

```bash
python -m pytest tests -q
```

The suite uses an in memory SQLite database and takes about a minute. It covers the collector, the rollups, the middleware rules, the overlay, the panel, the replay data, the visit list, user attribution and the prune.

To run against a specific Django version:

```bash
pip install "Django~=5.2.0"
python -m pytest tests -q
```

## CI

GitHub Actions runs the suite on every push and pull request, on this matrix:

| Python | Django |
| --- | --- |
| 3.10 | 4.2 |
| 3.11 | 5.0 |
| 3.12 | 5.1 |
| 3.13 | 5.2 |
| 3.12 | 6.0 |
| 3.13 | 6.1 |

## Building the documentation

```bash
pip install -r docs/requirements.txt
pip install -e .
sphinx-build -W -b html docs docs/_build/html
```

Open `docs/_build/html/index.html`. Read the Docs builds the same configuration from `.readthedocs.yaml` on every push.

## House rules

* Every behaviour change comes with a test. Tests lean towards the quiet failures: wrong counts, wrong people recorded, data shown to somebody who should not see it.
* No dependencies besides Django. The tracker, the overlay and the player are plain JavaScript on purpose.
* Nothing in the recorder may throw into the page it records.
* Nothing is recorded that a visitor would be surprised to learn was recorded. If in doubt, do not store it.
* No comments in the code.

## Reporting a problem

Open an issue at [github.com/qiyascc/django-sightline/issues](https://github.com/qiyascc/django-sightline/issues). Include the Django and Python versions, the relevant part of your `SIGHTLINE` settings and, for display problems, a screenshot.
