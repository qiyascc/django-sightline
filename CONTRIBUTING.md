# Contributing

Small, focused changes are the easiest to review and the easiest to ship.

## Setup

```bash
python -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"
python -m pytest tests -q
```

## House rules

* Every behaviour change comes with a test. Tests here lean towards the
  quiet failures: wrong counts, wrong people recorded, data leaking to
  somebody who should not see it.
* Comments explain why, not what. The code already says what.
* No dependencies. The tracker is vanilla JavaScript on purpose and the
  package depends on Django alone.
* Nothing in the recorder may throw into the page it records.
* Nothing is recorded that a visitor would be surprised to learn was
  recorded. If in doubt, do not store it.

## Reporting

Include the Django and Python version, the relevant part of your
`SIGHTLINE` settings and, if it is a display problem, a screenshot.
