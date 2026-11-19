"""``uvicorn hermes_fleet.main:app`` entry point."""

from hermes_fleet.app import create_app

app = create_app()
