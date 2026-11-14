# Quickstart

This walk-through starts with an empty folder and ends with a heatmap drawn over a page you made. It takes about fifteen minutes. The commands are for Linux and macOS; on Windows CMD use `py` instead of `python3` and `.venv\Scripts\activate` instead of `source .venv/bin/activate`.

## 1. Create a project

```bash
mkdir sightline-demo
cd sightline-demo
python3 -m venv .venv
source .venv/bin/activate
pip install django django-cc-sightline
django-admin startproject mysite .
```

You now have `manage.py` and a `mysite/` package with `settings.py` and `urls.py`.

## 2. Make a page worth clicking on

Create `mysite/templates/home.html`:

```html
<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <title>Demo shop</title>
  <style>
    body { font-family: system-ui, sans-serif; margin: 0; }
    header, section { padding: 32px 8vw; }
    .hero { height: 360px; background: #f4ece2; }
    .btn { padding: 12px 20px; border: 0; border-radius: 999px; background: #6b3b1f; color: #fff; }
    .card { display: inline-block; width: 28%; margin-right: 3%; padding: 18px; border: 1px solid #ddd; }
  </style>
</head>
<body>
  <header><b>Demo shop</b> <a href="/">Home</a> <a href="#plans">Plans</a></header>
  <section class="hero">
    <h1>Fresh coffee every Friday</h1>
    <p>A page with a few things to click and something to scroll past.</p>
    <button class="btn" id="buy">Buy now</button>
  </section>
  <section id="plans">
    <div class="card"><h3>Starter</h3><button class="btn" id="starter">Choose</button></div>
    <div class="card"><h3>Regular</h3><button class="btn" id="regular">Choose</button></div>
    <div class="card"><h3>Office</h3><button class="btn" id="office">Choose</button></div>
  </section>
  <section style="height: 900px">Some long content so the page scrolls.</section>
</body>
</html>
```

Tell Django where the template lives. In `mysite/settings.py`, find `TEMPLATES` and set `DIRS`:

```python
TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR / "mysite" / "templates"],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]
```

## 3. Install Sightline into the project

Still in `mysite/settings.py`, add the app and the middleware:

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

Then replace `mysite/urls.py` with:

```python
from django.contrib import admin
from django.urls import include, path
from django.views.generic import TemplateView

urlpatterns = [
    path("admin/", admin.site.urls),
    path("sightline/", include("sightline.urls")),
    path("", TemplateView.as_view(template_name="home.html")),
]
```

## 4. Create the database and an admin account

```bash
python manage.py migrate
python manage.py createsuperuser
```

Pick any username and password. This account is staff, which matters in step 6.

## 5. Start the server

```bash
python manage.py runserver
```

Leave it running and use a second terminal for anything else.

## 6. Visit the page as a visitor, not as yourself

Open **a private window** and go to <http://127.0.0.1:8000/>.

This is the step people skip. Staff are not recorded by default, so if you open the page in a browser where you are signed in to the admin, nothing is recorded and the panel stays empty. A private window has no admin session, so you count as a normal visitor.

In that private window:

* move the pointer around for a few seconds,
* click **Buy now** a couple of times and one of the **Choose** buttons,
* click a few times on the heading text, which does nothing (that is a dead click),
* click four times quickly on the same spot of the beige hero area (that is a rage click),
* scroll down to the bottom of the page and back up.

The tracker sends its first batch about a second after the page loads, then every five seconds, and once more when you leave. Wait five seconds or close the private window.

## 7. Open the panel

In your normal window, sign in at <http://127.0.0.1:8000/admin/> with the account from step 4. In the sidebar, under **Sightline**, click **Sightline panel**.

```{image} ../_static/screenshots/panel.jpg
:alt: The Sightline panel with date and device filters, totals, the pages table and the list of recent visits
```

You see:

* filters for the date range and device at the top,
* a box to open the heatmap on any path,
* four totals: sessions, and how many had rage clicks, dead clicks and script errors,
* **Pages**, with views, clicks and average scroll depth per path,
* **Recent visits**, each with a **Replay** button.

## 8. Open the heatmap

Click **Open heatmap** next to `/`. A new tab opens your page with the overlay on top: heat where you clicked and a bar at the bottom.

* Switch the first select from **Clicks** to **Attention** to see where the pointer moved.
* Switch to **Scroll depth** to see how far down the page was seen.
* The range select starts at 30 days and the device select at all devices; change them to narrow the data.
* Drag the slider to change the opacity, and click **Close** to put the page back to normal.

## 9. Watch the replay

Back in the panel, click **Replay** on your visit. The page loads at the size of the private window you used, and **Play** moves a cursor through what you did: the scrolling, each click with a ripple, rage clicks in a different colour.

## Where to go next

* [How recording works](../guides/how-it-works.md) explains what was stored during step 6.
* [Custom events](../guides/custom-events.md) shows how to mark moments like "checkout started".
* [Retention](../guides/retention.md) explains the prune command you should schedule before going live.
