"""
WebSocket CLI Commands - Admin tools for WebSocket management

Commands:
- aq ws inspect: Show compiled WS namespaces and controllers
- aq ws broadcast: Admin broadcast to namespace/room
- aq ws purge-room: Remove room state
- aq ws kick: Disconnect connection
- aq ws gen-client: Generate TypeScript client SDK
"""

import argparse
import json
import asyncio
from pathlib import Path
from typing import Optional
import sys


def cmd_ws_inspect(args: dict):
    """
    Inspect compiled WebSocket namespaces.
    
    Usage: aq ws inspect [--artifacts-dir artifacts]
    """
    artifacts_dir = Path(args.get("artifacts_dir", "artifacts"))
    ws_crous = artifacts_dir / "ws.crous"
    
    if not ws_crous.exists():
        print(f"Error: {ws_crous} not found. Run 'aq compile' first.")
        sys.exit(1)
    
    with open(ws_crous) as f:
        data = json.load(f)
    
    print(f"WebSocket Namespaces ({len(data['controllers'])} controllers)\n")
    
    for controller in data["controllers"]:
        print(f"Namespace: {controller['namespace']}")
        print(f"  Controller: {controller['class_name']}")
        print(f"  Module: {controller['module_path']}")
        print(f"  Path: {controller['path_pattern']}")
        print(f"  Events: {len(controller['events'])}")
        
        for event in controller["events"]:
            ack_str = " [ACK]" if event["ack"] else ""
            schema_str = " [SCHEMA]" if event["schema"] else ""
            print(f"    - {event['event']} → {event['handler_name']}{ack_str}{schema_str}")
        
        if controller["guards"]:
            print(f"  Guards: {', '.join(controller['guards'])}")
        
        config = controller["config"]
        if config.get("allowed_origins"):
            print(f"  Allowed Origins: {config['allowed_origins']}")
        if config.get("message_rate_limit"):
            print(f"  Rate Limit: {config['message_rate_limit']} msg/sec")
        
        print()


def cmd_ws_broadcast(args: dict):
    """
    Broadcast message to namespace or room.
    
    Usage: 
        aq ws broadcast --namespace /chat --room room1 --event message.receive --payload '{"text":"hi"}'
    """
    namespace = args.get("namespace")
    room = args.get("room")
    event = args.get("event")
    payload = args.get("payload", "{}")
    
    if not namespace or not event:
        print("Error: --namespace and --event are required")
        sys.exit(1)
    
    try:
        payload_dict = json.loads(payload)
    except json.JSONDecodeError as e:
        print(f"Error: Invalid JSON payload: {e}")
        sys.exit(1)
    
    print(f"Broadcasting to namespace={namespace}, room={room or 'all'}")
    print(f"Event: {event}")
    print(f"Payload: {payload_dict}")
    
    # TODO: Implement actual broadcast via adapter
    # This would require connecting to the runtime
    print("\n[Not yet implemented - requires runtime connection]")


def cmd_ws_purge_room(args: dict):
    """
    Purge room state from adapter.
    
    Usage: aq ws purge-room --namespace /chat --room room1
    """
    namespace = args.get("namespace")
    room = args.get("room")
    
    if not namespace or not room:
        print("Error: --namespace and --room are required")
        sys.exit(1)
    
    print(f"Purging room: {namespace}/{room}")
    
    # TODO: Implement actual purge via adapter
    print("[Not yet implemented - requires adapter connection]")


def cmd_ws_kick(args: dict):
    """
    Kick (disconnect) a connection.
    
    Usage: aq ws kick --conn <connection-id> --reason "violated rules"
    """
    conn_id = args.get("conn")
    reason = args.get("reason", "kicked by admin")
    
    if not conn_id:
        print("Error: --conn is required")
        sys.exit(1)
    
    print(f"Kicking connection: {conn_id}")
    print(f"Reason: {reason}")
    
    # TODO: Implement actual kick via runtime API
    print("[Not yet implemented - requires runtime API]")


def cmd_ws_gen_client(args: dict):
    """
    Generate TypeScript client SDK from artifacts.
    
    Usage: aq ws gen-client --lang ts --out clients/chat.ts
    """
    lang = args.get("lang", "ts")
    output_path = args.get("out")
    artifacts_dir = Path(args.get("artifacts_dir", "artifacts"))
    
    if lang != "ts":
        print(f"Error: Language {lang} not supported (only 'ts' currently)")
        sys.exit(1)
    
    if not output_path:
        print("Error: --out is required")
        sys.exit(1)
    
    ws_crous = artifacts_dir / "ws.crous"
    
    if not ws_crous.exists():
        print(f"Error: {ws_crous} not found. Run 'aq compile' first.")
        sys.exit(1)
    
    with open(ws_crous) as f:
        data = json.load(f)
    
    # Generate TypeScript client
    output = Path(output_path)
    output.parent.mkdir(parents=True, exist_ok=True)
    
    ts_code = _generate_typescript_client(data)
    
    with open(output, "w") as f:
        f.write(ts_code)
    
    print(f"Generated TypeScript client: {output}")


def _generate_typescript_client(data: dict) -> str:
    """Generate TypeScript client code."""
    lines = [
        "// Auto-generated WebSocket client for Aquilia",
        "// Do not edit manually",
        "",
        "export interface MessageEnvelope {",
        "  id?: string;",
        "  type: 'event' | 'ack' | 'system' | 'control';",
        "  event: string;",
        "  payload: any;",
        "  meta?: {",
        "    ts?: number;",
        "    trace_id?: string;",
        "  };",
        "  ack?: boolean;",
        "}",
        "",
    ]
    
    for controller in data["controllers"]:
        namespace = controller["namespace"]
        class_name = controller["class_name"]
        
        lines.append(f"// {class_name} ({namespace})")
        lines.append("")
        
        # Generate event payload types
        for event in controller["events"]:
            event_name = event["event"]
            type_name = _to_pascal_case(event_name) + "Payload"
            
            schema = event.get("schema")
            if schema and schema.get("spec"):
                lines.append(f"export interface {type_name} {{")
                for field, field_spec in schema["spec"].items():
                    ts_type = _python_type_to_ts(field_spec.get("type", "any"))
                    lines.append(f"  {field}: {ts_type};")
                lines.append("}")
            else:
                lines.append(f"export type {type_name} = any;")
            
            lines.append("")
        
        # Generate client class
        lines.extend([
            f"export class {class_name}Client {{",
            "  private ws: WebSocket;",
            "  private handlers: Map<string, (payload: any) => void> = new Map();",
            "",
            "  constructor(url: string, token?: string) {",
            f"    const fullUrl = token ? `${{url}}?token=${{token}}` : url;",
            "    this.ws = new WebSocket(fullUrl);",
            "    this.ws.onmessage = (event) => this.handleMessage(event);",
            "  }",
            "",
            "  private handleMessage(event: MessageEvent) {",
            "    const envelope: MessageEnvelope = JSON.parse(event.data);",
            "    const handler = this.handlers.get(envelope.event);",
            "    if (handler) {",
            "      handler(envelope.payload);",
            "    }",
            "  }",
            "",
        ])
        
        # Generate send methods
        for event in controller["events"]:
            if event["handler_type"] in ("event", "subscribe", "unsubscribe"):
                event_name = event["event"]
                method_name = _to_camel_case(event_name)
                type_name = _to_pascal_case(event_name) + "Payload"
                
                lines.extend([
                    f"  {method_name}(payload: {type_name}, ack: boolean = false): void {{",
                    "    const envelope: MessageEnvelope = {",
                    "      type: 'event',",
                    f"      event: '{event_name}',",
                    "      payload,",
                    "      ack,",
                    "    };",
                    "    this.ws.send(JSON.stringify(envelope));",
                    "  }",
                    "",
                ])
        
        # Generate listener methods
        for event in controller["events"]:
            event_name = event["event"]
            method_name = "on" + _to_pascal_case(event_name)
            type_name = _to_pascal_case(event_name) + "Payload"
            
            lines.extend([
                f"  {method_name}(handler: (payload: {type_name}) => void): void {{",
                f"    this.handlers.set('{event_name}', handler);",
                "  }",
                "",
            ])
        
        lines.extend([
            "  close(): void {",
            "    this.ws.close();",
            "  }",
            "}",
            "",
        ])
    
    return "\n".join(lines)


def _to_pascal_case(s: str) -> str:
    """Convert string to PascalCase."""
    return "".join(word.capitalize() for word in s.replace(".", "_").split("_"))


def _to_camel_case(s: str) -> str:
    """Convert string to camelCase."""
    parts = s.replace(".", "_").split("_")
    return parts[0].lower() + "".join(word.capitalize() for word in parts[1:])


def _python_type_to_ts(py_type: str) -> str:
    """Convert Python type to TypeScript type."""
    mapping = {
        "str": "string",
        "int": "number",
        "float": "number",
        "bool": "boolean",
        "dict": "object",
        "list": "any[]",
        "Any": "any",
    }
    return mapping.get(py_type, "any")


# Main dispatch

def main():
    """Main CLI entry point."""
    parser = argparse.ArgumentParser(description="Aquilia WebSocket CLI")
    subparsers = parser.add_subparsers(dest="command", help="Command to run")
    
    # inspect
    inspect_parser = subparsers.add_parser("inspect", help="Inspect compiled WebSocket namespaces")
    inspect_parser.add_argument("--artifacts-dir", default="artifacts", help="Artifacts directory")
    
    # broadcast
    broadcast_parser = subparsers.add_parser("broadcast", help="Broadcast message")
    broadcast_parser.add_argument("--namespace", required=True, help="Namespace")
    broadcast_parser.add_argument("--room", help="Room (optional)")
    broadcast_parser.add_argument("--event", required=True, help="Event name")
    broadcast_parser.add_argument("--payload", default="{}", help="JSON payload")
    
    # purge-room
    purge_parser = subparsers.add_parser("purge-room", help="Purge room state")
    purge_parser.add_argument("--namespace", required=True, help="Namespace")
    purge_parser.add_argument("--room", required=True, help="Room")
    
    # kick
    kick_parser = subparsers.add_parser("kick", help="Kick connection")
    kick_parser.add_argument("--conn", required=True, help="Connection ID")
    kick_parser.add_argument("--reason", default="kicked by admin", help="Reason")
    
    # gen-client
    gen_parser = subparsers.add_parser("gen-client", help="Generate client SDK")
    gen_parser.add_argument("--lang", default="ts", help="Language (ts)")
    gen_parser.add_argument("--out", required=True, help="Output file")
    gen_parser.add_argument("--artifacts-dir", default="artifacts", help="Artifacts directory")
    
    args = parser.parse_args()
    args_dict = vars(args)
    
    commands = {
        "inspect": cmd_ws_inspect,
        "broadcast": cmd_ws_broadcast,
        "purge-room": cmd_ws_purge_room,
        "kick": cmd_ws_kick,
        "gen-client": cmd_ws_gen_client,
    }
    
    command = args_dict.get("command")
    
    if command in commands:
        commands[command](args_dict)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
