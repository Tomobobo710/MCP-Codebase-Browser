import os
import sys
import shutil
from pathlib import Path
import glob
import traceback
import json
from datetime import datetime
import subprocess
from typing import Any

import mcp.types as types
from mcp.server.lowlevel import Server
from starlette.middleware.cors import CORSMiddleware
import uvicorn

# Auto-detect CODEBASE_PATH relative to script location
script_dir = Path(os.path.dirname(os.path.abspath(__file__)))
CODEBASE_PATH = None
CLI_CONFIG = None

def load_cli_config():
    try:
        config_path = script_dir / "cli_config.json"
        if config_path.exists():
            with open(config_path, 'r') as f:
                return json.load(f)
    except Exception as e:
        print(f"Warning: Could not load CLI config: {e}", file=sys.stderr)
    return {}

def load_env_config():
    try:
        from dotenv import load_dotenv
        load_dotenv(script_dir / ".env")
    except:
        pass
    return {
        "sse_port": int(os.getenv("SSE_PORT", "9051")),
        "sse_host": os.getenv("SSE_HOST", "0.0.0.0"),
        "log_level": os.getenv("LOG_LEVEL", "info"),
        "ssl_cert_path": os.getenv("SSL_CERT_PATH"),
        "ssl_key_path": os.getenv("SSL_KEY_PATH"),
        "cors_allow_all": os.getenv("CORS_ALLOW_ALL", "true").lower() == "true",
        "cors_allowed_origins": os.getenv("CORS_ALLOWED_ORIGINS", "").split(",") if os.getenv("CORS_ALLOWED_ORIGINS") else [],
    }

def get_codebase_path():
    project_dir = script_dir / "Project"
    if not project_dir.exists():
        os.makedirs(project_dir)
        with open(project_dir / "README.txt", "w") as f:
            f.write("Put your project files in this directory.\n")
    return str(project_dir)

if CODEBASE_PATH is None:
    CODEBASE_PATH = get_codebase_path()

ENV_CONFIG = load_env_config()
CLI_CONFIG = load_cli_config()

MAX_RESULT_SIZE = 99000

def get_history_file():
    history_dir = script_dir / "History"
    history_dir.mkdir(exist_ok=True)
    history_file = history_dir / "commits.json"
    if not history_file.exists():
        with open(history_file, 'w') as f:
            json.dump([], f)
    return history_file

def add_commit(operation, path, message):
    try:
        history_file = get_history_file()
        with open(history_file, 'r') as f:
            history = json.load(f)
        history.insert(0, {"timestamp": datetime.now().isoformat()[:16], "operation": operation, "path": path or "", "message": message})
        history = history[:25]
        with open(history_file, 'w') as f:
            json.dump(history, f, indent=2)
    except Exception as e:
        print(f"Warning: Could not log commit: {e}", file=sys.stderr)

def is_file_locked(filepath):
    try:
        with open(filepath, 'r+'): return False
    except (PermissionError, OSError): return True

def should_skip_path(path_str):
    return 'node_modules' in Path(path_str).parts

def check_result_size(result):
    result_json = json.dumps(result)
    if len(result_json) > MAX_RESULT_SIZE:
        return {"error": f"Result too large ({len(result_json)} characters)", "message": "Try a more specific operation."}
    return result

server = Server("MCP Codebase Browser")

@server.list_tools()
async def list_tools() -> list[types.Tool]:
    return [types.Tool(
        name="codebase_browser",
        description="All-in-one codebase browser tool for file management, editing, searching, and more.",
        inputSchema={
            "type": "object",
            "properties": {
                "operation": {"type": "string", "description": "Operation: read, write, delete, move, copy, list, mkdir, rmdir, edit, search, backup_create, backup_list, backup_restore, browse_backup, read_recent_commits, run_command"},
                "path": {"type": "string"},
                "options": {"type": "object"},
                "message": {"type": "string"}
            },
            "required": ["operation"]
        }
    )]

@server.call_tool()
async def call_tool(name: str, arguments: dict[str, Any]) -> list[types.TextContent]:
    if name != "codebase_browser":
        return [types.TextContent(type="text", text=json.dumps({"error": f"Unknown tool: {name}"}))]
    operation = arguments.get("operation")
    path = arguments.get("path")
    options = arguments.get("options", {})
    message = arguments.get("message")
    try:
        result_metadata = {"operation_type": operation, "path": path}
        if operation in ["read", "write", "delete", "move", "copy", "list", "mkdir", "rmdir"]:
            result = _handle_file_operations(operation, path, options, message)
        elif operation == "edit":
            result = _handle_edit_operations(path, options, message)
        elif operation == "search":
            result = _handle_search_operations(options)
        elif operation in ["backup_create", "backup_list", "backup_restore", "browse_backup"]:
            result = _handle_backup_operations(operation.replace("backup_", ""), options)
        elif operation == "read_recent_commits":
            result = _handle_history_operations()
        elif operation == "run_command":
            result = _handle_run_command_operations(options, message)
        else:
            result = {"error": f"Unknown operation: {operation}"}
        result.update(result_metadata)
        result = check_result_size(result)
        return [types.TextContent(type="text", text=json.dumps(result))]
    except Exception as e:
        return [types.TextContent(type="text", text=json.dumps({"error": str(e), "traceback": traceback.format_exc()}))]

def _handle_file_operations(operation, path, options, message):
    if path is None:
        return {"error": "Path is required"}
    write_ops = ["write", "delete", "move", "copy", "mkdir", "rmdir"]
    if operation in write_ops and not message:
        return {"error": f"Message required for {operation}"}
    full_path = Path(CODEBASE_PATH) / path
    try:
        if operation == "list":
            pattern = options.get("pattern", "**/*")
            if not full_path.exists(): return {"error": "Directory not found"}
            files = [str(Path(f).relative_to(full_path)) for f in glob.glob(str(full_path / pattern), recursive=True) if os.path.isfile(f) and not should_skip_path(str(Path(f).relative_to(full_path)))]
            dirs = [d.name + '/' for d in os.scandir(str(full_path)) if d.is_dir() and not should_skip_path(d.name)]
            return {"files": files, "directories": dirs, "path": path}
        elif operation == "read":
            if not full_path.exists(): return {"error": "File not found"}
            start_line = options.get("start_line")
            end_line = options.get("end_line")
            with open(full_path, 'r', encoding='utf-8', errors='replace') as f:
                content = f.read()
            if len(content) > MAX_RESULT_SIZE and start_line is None:
                return {"error": "File too large", "line_count": content.count('\n') + 1}
            if start_line is not None:
                lines = content.splitlines(True)
                start_idx = max(0, start_line - 1)
                end_idx = end_line if end_line is not None else start_idx + 1
                filtered = lines[start_idx:end_idx]
                if options.get("format") == "lines":
                    return {"lines": [{"lineNo": start_line + i, "content": l} for i, l in enumerate(filtered)], "count": len(filtered)}
                return {"content": "".join(filtered), "count": len(filtered)}
            return {"content": content, "count": content.count('\n') + 1}
        elif operation == "write":
            content = options.get("content")
            if content is None: return {"error": "content required"}
            if full_path.exists() and is_file_locked(str(full_path)): return {"error": "File is locked"}
            full_path.parent.mkdir(parents=True, exist_ok=True)
            with open(full_path, 'w', encoding='utf-8') as f: f.write(content)
            add_commit(operation, path, message)
            return {"success": True}
        elif operation == "delete":
            if not full_path.exists() or not full_path.is_file(): return {"error": "File not found"}
            if is_file_locked(str(full_path)): return {"error": "File is locked"}
            os.remove(full_path)
            add_commit(operation, path, message)
            return {"success": True}
        elif operation == "mkdir":
            full_path.mkdir(parents=True, exist_ok=True)
            add_commit(operation, path, message)
            return {"success": True}
        elif operation == "rmdir":
            if not full_path.exists() or not full_path.is_dir(): return {"error": "Directory not found"}
            try:
                shutil.rmtree(full_path) if options.get("recursive") else os.rmdir(full_path)
            except OSError: return {"error": "Directory not empty"}
            add_commit(operation, path, message)
            return {"success": True}
        elif operation == "move":
            destination = options.get("destination")
            if not destination or not full_path.exists(): return {"error": "Invalid move"}
            dest_path = Path(CODEBASE_PATH) / destination
            if dest_path.exists() and not options.get("overwrite"): return {"error": "Destination exists"}
            dest_path.parent.mkdir(parents=True, exist_ok=True)
            shutil.move(str(full_path), str(dest_path))
            add_commit(operation, f"{path} -> {destination}", message)
            return {"success": True}
        elif operation == "copy":
            destination = options.get("destination")
            if not destination or not full_path.exists(): return {"error": "Invalid copy"}
            dest_path = Path(CODEBASE_PATH) / destination
            if dest_path.exists() and not options.get("overwrite"): return {"error": "Destination exists"}
            dest_path.parent.mkdir(parents=True, exist_ok=True)
            shutil.copytree(str(full_path), str(dest_path)) if full_path.is_dir() else shutil.copy2(str(full_path), str(dest_path))
            add_commit(operation, f"{path} -> {destination}", message)
            return {"success": True}
    except Exception as e:
        return {"error": str(e), "traceback": traceback.format_exc()}

def _handle_edit_operations(path, options, message):
    if not path or not message: return {"error": "Path and message required"}
    full_path = Path(CODEBASE_PATH) / path
    new_content = options.get("new_content")
    operations = options.get("operations", [])
    try:
        if new_content is not None:
            full_path.parent.mkdir(parents=True, exist_ok=True)
            with open(full_path, 'w', encoding='utf-8') as f: f.write(new_content)
            add_commit("edit", path, message)
            return {"success": True}
        if not full_path.exists(): return {"error": "File not found"}
        with open(full_path, 'r', encoding='utf-8', errors='replace') as f:
            content = f.read()
        modified = content
        count = 0
        for op in operations:
            if op.get("mode") == "replace" and "find" in op and "replace" in op:
                if op["find"] in modified:
                    modified = modified.replace(op["find"], op["replace"], 1)
                    count += 1
        with open(full_path, 'w', encoding='utf-8') as f: f.write(modified)
        add_commit("edit", path, message)
        return {"success": True, "operations_applied": count}
    except Exception as e:
        return {"error": str(e)}

def _handle_search_operations(options):
    search_term = options.get("search_term", "")
    if not search_term: return {"error": "search_term required"}
    matches = []
    base_path = Path(CODEBASE_PATH)
    try:
        for root, _, files in os.walk(base_path):
            for filename in files:
                full_path = os.path.join(root, filename)
                rel_path = os.path.relpath(full_path, base_path)
                if should_skip_path(rel_path): continue
                try:
                    with open(full_path, 'r', encoding='utf-8', errors='replace') as f:
                        for idx, line in enumerate(f):
                            if search_term.lower() in line.lower():
                                matches.append({"file": rel_path, "lineNumber": idx + 1, "lineContent": line.rstrip()})
                except: continue
        return {"matches": matches[:25], "totalMatches": len(matches), "searchTerm": search_term}
    except Exception as e:
        return {"error": str(e)}

def _handle_backup_operations(operation, options):
    backup_root = script_dir / "Backups"
    try:
        if operation == "list":
            if not backup_root.exists(): return {"backups": [], "count": 0}
            return {"backups": [{"name": item.name} for item in backup_root.iterdir() if item.is_dir()], "count": len(list(backup_root.iterdir()))}
        elif operation == "create":
            backup_root.mkdir(parents=True, exist_ok=True)
            backup_name = options.get("name") or f"backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
            shutil.copytree(CODEBASE_PATH, backup_root / backup_name)
            return {"success": True, "backup_name": backup_name}
        elif operation == "restore":
            backup_name = options.get("name")
            if not backup_name: return {"error": "name required"}
            backup_path = backup_root / backup_name
            if not backup_path.exists(): return {"error": "Backup not found"}
            shutil.rmtree(CODEBASE_PATH)
            shutil.copytree(str(backup_path), CODEBASE_PATH)
            return {"success": True}
        return {"error": f"Unknown backup operation: {operation}"}
    except Exception as e:
        return {"error": str(e)}

def _handle_history_operations():
    try:
        history_file = get_history_file()
        with open(history_file, 'r') as f:
            history = json.load(f)
        return {"commits": history, "count": len(history)}
    except:
        return {"commits": [], "count": 0}

def _handle_run_command_operations(options, message):
    command = options.get("command")
    if not command or not message or not CLI_CONFIG:
        return {"error": "command, message, and cli_config required"}
    try:
        result = subprocess.run(command, stdin=subprocess.DEVNULL, capture_output=True, text=True)
        add_commit("run_command", command, message)
        return {"success": result.returncode == 0, "exit_code": result.returncode, "stdout": result.stdout, "stderr": result.stderr}
    except Exception as e:
        return {"error": str(e), "traceback": traceback.format_exc()}

if __name__ == "__main__":
    from mcp.server.sse import SseServerTransport
    from starlette.applications import Starlette
    from starlette.routing import Mount, Route

    cors_origins = ["*"] if ENV_CONFIG["cors_allow_all"] else ENV_CONFIG["cors_allowed_origins"]

    transport = SseServerTransport("/messages/")

    async def handle_sse(request):
        async with transport.connect_sse(request.scope, request.receive, request._send) as streams:
            await server.run(streams[0], streams[1], server.create_initialization_options())

    app = Starlette(routes=[
        Route("/sse", endpoint=handle_sse),
        Mount("/messages/", app=transport.handle_post_message),
    ])

    app.add_middleware(
        CORSMiddleware,
        allow_origins=cors_origins,
        allow_methods=["*"],
        allow_headers=["*"],
        expose_headers=["Mcp-Session-Id"],
    )

    ssl_config = {}
    if ENV_CONFIG["ssl_cert_path"] and ENV_CONFIG["ssl_key_path"]:
        ssl_config = {"ssl_certfile": ENV_CONFIG["ssl_cert_path"], "ssl_keyfile": ENV_CONFIG["ssl_key_path"]}

    print(f"MCP Codebase Browser SSE on {ENV_CONFIG['sse_host']}:{ENV_CONFIG['sse_port']}", file=sys.stderr)
    print(f"Endpoint: http://{ENV_CONFIG['sse_host']}:{ENV_CONFIG['sse_port']}/sse", file=sys.stderr)
    print(f"Codebase: {CODEBASE_PATH}", file=sys.stderr)

    uvicorn.run(app, host=ENV_CONFIG["sse_host"], port=ENV_CONFIG["sse_port"], log_level=ENV_CONFIG["log_level"], **ssl_config)
