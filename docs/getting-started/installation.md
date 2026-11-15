# Installation

This page installs django-cc-sightline into an existing Django project, step by step. If you do not have a project yet, the [Quickstart](quickstart.md) creates one from scratch and ends with a working heatmap.

## Before you start

You need:

* Python 3.10 or newer. Check with `python --version` (on Windows, `py --version`).
* A Django project on Django 4.2 or newer. Django 6.0 and 6.1 need Python 3.12 or newer.
* `django.contrib.admin`, `django.contrib.auth`, `django.contrib.sessions` and `django.contrib.staticfiles` in `INSTALLED_APPS`. Almost every project has them already. The panel lives inside the admin, staff detection needs sessions and auth, and the tracker is served as a static file.

## Step 1: activate your virtual environment

Install the package into the same environment your project runs in. If your project already has one, activate it and skip to step 2.

::::{tab-set}

:::{tab-item} Linux and macOS

```bash
cd ~/projects/mysite
python3 -m venv .venv
source .venv/bin/activate
```

:::

:::{tab-item} Windows (CMD)

```bat
cd %USERPROFILE%\projects\mysite
py -m venv .venv
.venv\Scripts\activate
```

:::

::::

Your prompt now starts with `(.venv)`. Every command below assumes that.

## Step 2: install the package

::::{tab-set}

:::{tab-item} pip

```bash
pip install django-cc-sightline
```

:::

:::{tab-item} uv

```bash
uv pip install django-cc-sightline
```

or, in a project managed by uv:

```bash
uv add django-cc-sightline
```

:::

:::{tab-item} Poetry

```bash
poetry add django-cc-sightline
```

:::

:::{tab-item} requirements.txt

```text
django-cc-sightline>=0.3,<0.4
```

Then run `pip install -r requirements.txt`.

:::

::::

The only dependency is Django itself.

```{warning}
Do not install `django-sightline` from PyPI. That is a different project, and it also ships a top level `sightline` module, so installing both makes one overwrite the other. If you installed this project from git under the old name, see [Upgrading](upgrading.md).
```

Check that Python can find it:

```bash
python -c "import sightline; print(sightline.__version__)"
```

It prints the installed version, for example `0.2.0`.

## Step 3: add the app

Open your settings module and add `sightline` to `INSTALLED_APPS`. The position does not matter.

```python
INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "sightline",
]
```

## Step 4: add the middleware

The middleware is what puts the tracker into your pages. Add it at the **end** of `MIDDLEWARE`:

```python
MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
    "sightline.middleware.SightlineMiddleware",
]
```

Why last? Django runs middleware in list order on the way in and in reverse order on the way out. The last entry is the first to see the response your view returned, so it gets the plain HTML before anything above it compresses or rewrites it. Two practical consequences:

* It has to come **after** `AuthenticationMiddleware`, because it reads `request.user` to skip staff visits.
* It has to come **after** `GZipMiddleware` if you use it. Above GZip it would receive compressed bytes and find no `</body>` to insert the script in front of.

The middleware only touches responses that are HTML, have status 200, are not streamed and contain a closing `</body>` tag. JSON, files, redirects and error pages pass through untouched.

## Step 5: add the URLs

Include the app's URLs in your root `urls.py`. The prefix is up to you, `sightline/` is the conventional one.

```python
from django.contrib import admin
from django.urls import include, path

urlpatterns = [
    path("admin/", admin.site.urls),
    path("sightline/", include("sightline.urls")),
]
```

The URL names live in the `sightline` namespace (`sightline:collect`, `sightline:dashboard` and so on), so the prefix can be anything. If you choose a different one, add it to `EXCLUDE_PATHS` as described in step 8, so the recorder never records its own panel.

## Step 6: create the tables

```bash
python manage.py migrate sightline
```

This creates seven tables: `sightline_session`, `sightline_page`, `sightline_pageview`, `sightline_event`, `sightline_heatcell`, `sightline_scrollband` and `sightline_elementstat`. The [Data model](../reference/data-model.md) page describes each one.

## Step 7: collect static files

In production, run `collectstatic` so the tracker, the overlay and the player are served with the rest of your static files:

```bash
python manage.py collectstatic
```

During development with `DEBUG = True` and `runserver`, Django serves them for you and this step can wait.

## Step 8: settings (optional)

Everything works with the defaults. When you want to change something, add a `SIGHTLINE` dict to your settings. Only the keys you set are overridden:

```python
SIGHTLINE = {
    "SAMPLE_RATE": 1.0,
    "RETAIN_DAYS": 90,
    "EXCLUDE_PATHS": ["/admin/", "/static/", "/media/", "/sightline/"],
}
```

If you set `EXCLUDE_PATHS`, the list replaces the default one, so keep the admin, static, media and Sightline prefixes in it. The [Settings reference](../reference/settings.md) lists every key.

## Step 9: check that it works

Start the server:

```bash
python manage.py runserver
```

Open a page of your site **in a private window**, where you are not signed in, and view the page source. Near the end you should find:

```html
<script>window.__sightline = {"collect": "/sightline/collect/", ...};</script>
<script src="/static/sightline/js/tracker.js" defer></script>
```

Click around for a few seconds, then sign in to the admin in your normal window. The sidebar has a new **Sightline** section with a **Sightline panel** entry. Open it: the visit you just made is listed under **Recent visits**, and the page shows up under **Pages** with an **Open heatmap** button.

```{image} ../_static/screenshots/admin-index.jpg
:alt: The Django admin index with the Sightline section in the sidebar
```

### If the script is not in the page

Work down this list. The [FAQ](../reference/faq.md) has more.

1. **You are signed in as staff.** Staff are not recorded by default, so their pages carry no tracker. Use a private window, or set `SIGHTLINE = {"IGNORE_STAFF": False}` while testing.
2. **The path is excluded.** Anything under `/admin/`, `/static/`, `/media/` and `/sightline/` is skipped.
3. **Your browser sends Do Not Track.** With `RESPECT_DNT` on, a request with the `DNT: 1` header is not recorded.
4. **The request looks like a bot.** `curl`, `wget`, `python-requests` and headless Chrome are skipped on purpose, which is why `curl http://localhost:8000/` shows no tracker. Use a real browser.
5. **The response is not plain HTML.** A streamed response, a page without `</body>` or a non-200 status is left alone.
6. **The middleware sits above GZip** or above `AuthenticationMiddleware`. Move it to the end.

## Next steps

* Read [How recording works](../guides/how-it-works.md) to know exactly what is collected.
* Decide on [retention](../guides/retention.md) and schedule the prune command.
* Look at [Privacy](../guides/privacy.md) before you go live.
