"""
WebSocket Compiler - Compile-time metadata extraction

Extracts WebSocket controller metadata and generates artifacts/ws.crous.
Integrated with `aq compile` command.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional, Type
from dataclasses import dataclass, asdict
from pathlib import Path
import inspect
import json
import logging

from .controller import SocketController
from .decorators import Socket
from .envelope import Schema

logger = logging.getLogger("aquilia.sockets.compile")


@dataclass
class EventMetadata:
    """Compiled event handler metadata."""
    event: str
    handler_name: str
    schema: Optional[Dict[str, Any]]
    ack: bool
    handler_type: str  # "event", "subscribe", "unsubscribe"


@dataclass
class SocketControllerMetadata:
    """Compiled controller metadata."""
    class_name: str
    module_path: str
    namespace: str
    path_pattern: str
    events: List[EventMetadata]
    guards: List[str]
    config: Dict[str, Any]


class SocketCompiler:
    """
    Compiler for WebSocket controllers.
    
    Extracts metadata without executing controller code.
    Generates artifacts/ws.crous for runtime and tooling.
    """
    
    def __init__(self):
        """Initialize compiler."""
        self.controllers: List[SocketControllerMetadata] = []
        self.namespaces: Dict[str, str] = {}  # namespace -> controller
    
    def compile_controller(
        self,
        controller_class: Type[SocketController],
    ) -> SocketControllerMetadata:
        """
        Compile controller to metadata.
        
        Args:
            controller_class: Controller class to compile
            
        Returns:
            Compiled metadata
        """
        # Extract @Socket metadata
        if not hasattr(controller_class, "__socket_metadata__"):
            raise ValueError(
                f"{controller_class.__name__} is missing @Socket decorator"
            )
        
        socket_meta = controller_class.__socket_metadata__
        
        namespace = socket_meta["path"]
        module_path = f"{controller_class.__module__}:{controller_class.__name__}"
        
        # Check for namespace conflicts
        if namespace in self.namespaces:
            raise ValueError(
                f"Namespace conflict: {namespace} already registered by "
                f"{self.namespaces[namespace]}"
            )
        
        self.namespaces[namespace] = module_path
        
        # Extract event handlers
        events = []
        guards = []
        
        for name, method in inspect.getmembers(controller_class, inspect.isfunction):
            if hasattr(method, "__socket_handler__"):
                handler_meta = method.__socket_handler__
                handler_type = handler_meta.get("type")
                
                if handler_type in ("event", "subscribe", "unsubscribe"):
                    event = handler_meta.get("event")
                    schema_obj = handler_meta.get("schema")
                    
                    # Serialize schema
                    schema_dict = None
                    if schema_obj and isinstance(schema_obj, Schema):
                        schema_dict = {
                            "spec": self._serialize_schema_spec(schema_obj.spec)
                        }
                    
                    events.append(EventMetadata(
                        event=event,
                        handler_name=name,
                        schema=schema_dict,
                        ack=handler_meta.get("ack", False),
                        handler_type=handler_type,
                    ))
                
                elif handler_type == "guard":
                    guards.append(name)
        
        # Build config
        config = {
            "allowed_origins": socket_meta.get("allowed_origins"),
            "max_connections": socket_meta.get("max_connections"),
            "message_rate_limit": socket_meta.get("message_rate_limit"),
            "max_message_size": socket_meta.get("max_message_size"),
            "compression": socket_meta.get("compression"),
            "subprotocols": socket_meta.get("subprotocols"),
        }
        
        metadata = SocketControllerMetadata(
            class_name=controller_class.__name__,
            module_path=module_path,
            namespace=namespace,
            path_pattern=socket_meta["path"],
            events=events,
            guards=guards,
            config=config,
        )
        
        self.controllers.append(metadata)
        
        logger.info(f"Compiled controller: {controller_class.__name__} ({namespace})")
        
        return metadata
    
    def _serialize_schema_spec(self, spec: Dict[str, Any]) -> Dict[str, Any]:
        """Serialize schema spec to JSON-compatible dict."""
        result = {}
        
        for key, value in spec.items():
            if isinstance(value, type):
                result[key] = {"type": value.__name__}
            elif isinstance(value, tuple):
                type_obj, constraints = value
                result[key] = {
                    "type": type_obj.__name__,
                    "constraints": constraints if isinstance(constraints, dict) else "callable",
                }
            else:
                result[key] = str(value)
        
        return result
    
    def generate_artifacts(self, output_path: Path):
        """
        Generate artifacts/ws.crous.
        
        Args:
            output_path: Output file path
        """
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Build artifact structure
        artifact = {
            "version": "1.0.0",
            "type": "websockets",
            "controllers": [
                {
                    "class_name": c.class_name,
                    "module_path": c.module_path,
                    "namespace": c.namespace,
                    "path_pattern": c.path_pattern,
                    "events": [
                        {
                            "event": e.event,
                            "handler_name": e.handler_name,
                            "schema": e.schema,
                            "ack": e.ack,
                            "handler_type": e.handler_type,
                        }
                        for e in c.events
                    ],
                    "guards": c.guards,
                    "config": c.config,
                }
                for c in self.controllers
            ],
            "namespaces": self.namespaces,
        }
        
        # Write to file
        with open(output_path, "w") as f:
            json.dump(artifact, f, indent=2)
        
        logger.info(f"Generated WebSocket artifacts: {output_path}")
    
    def validate(self) -> List[str]:
        """
        Validate compiled controllers.
        
        Returns:
            List of validation errors
        """
        errors = []
        
        # Check for duplicate event handlers
        for controller in self.controllers:
            event_handlers = {}
            
            for event in controller.events:
                key = (event.event, event.handler_type)
                
                if key in event_handlers:
                    errors.append(
                        f"{controller.class_name}: Duplicate handler for event "
                        f"{event.event} ({event.handler_type}): "
                        f"{event_handlers[key]} and {event.handler_name}"
                    )
                else:
                    event_handlers[key] = event.handler_name
        
        # Check for missing required handlers
        for controller in self.controllers:
            # Could add checks for required events
            pass
        
        return errors


def compile_socket_controllers(
    controller_classes: List[Type[SocketController]],
    output_dir: Path,
) -> Path:
    """
    Compile socket controllers to artifacts.
    
    Args:
        controller_classes: List of controller classes
        output_dir: Output directory for artifacts
        
    Returns:
        Path to generated artifact file
    """
    compiler = SocketCompiler()
    
    for controller_class in controller_classes:
        compiler.compile_controller(controller_class)
    
    # Validate
    errors = compiler.validate()
    if errors:
        for error in errors:
            logger.error(f"Validation error: {error}")
        raise ValueError(f"WebSocket compilation failed with {len(errors)} errors")
    
    # Generate artifacts
    artifact_path = output_dir / "ws.crous"
    compiler.generate_artifacts(artifact_path)
    
    return artifact_path
