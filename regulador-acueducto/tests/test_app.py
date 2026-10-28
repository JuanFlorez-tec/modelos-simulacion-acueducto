from regulador import create_app


def test_app_disables_updating_title():
    app = create_app()
    assert app.config.update_title is None


def test_layout_builds():
    app = create_app()
    assert app.layout() is not None
