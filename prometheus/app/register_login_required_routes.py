from typing import Set, Tuple

from fastapi import FastAPI
from fastapi.routing import APIRoute

# Set to store routes that require login
login_required_routes: Set[Tuple[str, str]] = set()


def register_login_required_routes(app: FastAPI):
    for route in app.routes:
        if isinstance(route, APIRoute):
            endpoint = route.endpoint
            if getattr(endpoint, "_require_login", False):
                for method in route.methods:
                    login_required_routes.add((method, route.path))
