"""API tests: minimal UI serving (static bundle at / and /ui/*)."""

from __future__ import annotations


def test_ui_index_served(client):
    """GET / serves the UI shell."""
    response = client.get("/")
    assert response.status == 200
    assert (response.header("content-type") or "").startswith("text/html")
    assert "AcheoConverter" in response.text
    assert 'src="/ui/app.js"' in response.text


def test_ui_assets_served(client):
    """JS and CSS assets are served with the right media types."""
    js = client.get("/ui/app.js")
    assert js.status == 200
    assert "javascript" in (js.header("content-type") or "")
    assert "AcheoConverter" in js.text

    css = client.get("/ui/style.css")
    assert css.status == 200
    assert "text/css" in (css.header("content-type") or "")


def test_ui_missing_asset_404(client):
    """Unknown static assets return 404."""
    assert client.get("/ui/nope.js").status == 404


def test_ui_path_traversal_blocked(client):
    """Path traversal attempts are neutralized (404, no file leak)."""
    response = client.get("/ui/..%2F..%2Fapp.py")
    assert response.status == 404


def test_ui_disabled_returns_404():
    """With ui_enabled=false the UI routes return 404."""
    from AcheoConverter.application import create_app
    from AcheoConverter.config import AppConfig
    from asgi_client import ASGIClient

    config = AppConfig()
    config.ui_enabled = False
    app = create_app(config, setup_app_logging=False)
    client = ASGIClient(app)
    assert client.get("/").status == 404
    assert client.get("/ui/app.js").status == 404
    # The API keeps working.
    assert client.get("/api/v1/meta").status == 200
