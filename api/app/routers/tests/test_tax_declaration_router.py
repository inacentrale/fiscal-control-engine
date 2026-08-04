from fastapi.routing import APIRoute

from app.routers.tax_declaration import router


def test_legacy_tax_declaration_routes_are_explicitly_deprecated() -> None:
    routes = tuple(route for route in router.routes if isinstance(route, APIRoute))

    assert routes
    assert all(route.deprecated is True for route in routes)
    assert router.tags == ["tax-declarations-experimental"]
