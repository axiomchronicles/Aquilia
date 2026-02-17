"""
Aquilia Benchmark – ASGI Entry Point
=====================================
Usage:
    uvicorn benchmark.apps.aquilia_app.main:app --host 0.0.0.0 --port 8000 --workers 4
"""
import os
import sys

# Ensure the project root is on the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", ".."))

from aquilia import Workspace, Module, Integration
from aquilia.server import AquiliaServer

workspace = (
    Workspace(name="aquilia-bench", version="1.0.0", description="Benchmark app")
    .module(
        Module("bench", version="1.0.0", description="Benchmark endpoints")
        .route_prefix("")
        .tags("benchmark")
        .register_controllers(
            "benchmark.apps.aquilia_app.controllers:BenchController"
        )
        .register_sockets(
            "benchmark.apps.aquilia_app.ws_controller:BenchSocketController"
        )
    )
    .integrate(Integration.routing(strict_matching=False, compression=False))
)

server = AquiliaServer(manifests=[workspace])
app = server.get_asgi_app()

if __name__ == "__main__":
    server.run(host="0.0.0.0", port=8000)
