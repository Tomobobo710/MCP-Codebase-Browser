import os
import sys
import shutil
import re
from fnmatch import fnmatch
from pathlib import Path
import glob
import traceback
import json
from datetime import datetime
import subprocess
from typing import Any

import mcp.server.stdio
import mcp.types as types
from mcp.server.lowlevel import Server

# Auto-detect CODEBASE_PATH relative to script location
script_dir = Path(os.path.dirname(os.path.abspath(__file__)))
CODEBASE_PATH = None

# CLI configuration
CLI_CONFIG = None

def load_cli_config():
    """Load CLI configuration from cli_config.json if it exists."""
    try:
        config_path = script_dir / "cli_config.json"
        if config_path.exists():
            with open(config_path, 'r') as f:
                return json.load(f)
    except Exception as e:
        print(f"Warning: Could not load CLI config: {e}", file=sys.stderr)
    return {}

def get_codebase_path():
    """Automatically determine the codebase path based on script location."""
    project_dir = script_dir / "Project"
    if not project_dir.exists():
        os.makedirs(project_dir)
        print(f"Created Project directory at: {project_dir}", file=sys.stderr)
        with open(project_dir / "README.txt", "w") as f:
            f.write("Put your project files in this directory.\n")
            f.write("They will be automatically indexed by the MCP Codebase Browser.\n")
    return str(project_dir)

# Set up the codebase path
if CODEBASE_PATH is None:
    CODEBASE_PATH = get_codebase_path()

# Load CLI config
CLI_CONFIG = load_cli_config()

# Maximum result size in characters (serialized JSON)
MAX_RESULT_SIZE = 99000

def get_history_path():
    """Get the path to the history directory and ensure it exists."""
    history_dir = script_dir / "History"
    history_dir.mkdir(exist_ok=True)
    return history_dir

def get_history_file():
    """Get the path to the history file and ensure it exists."""
    history_dir = get_history_path()
    history_file = history_dir / "commits.json"
    if not history_file.exists():
        with open(history_file, 'w') as f:
            json.dump([], f)
    return history_file

def add_commit(operation, path, message):
    """Add a commit entry to the history file with FIFO management."""
    try:
        history_file = get_history_file()
        with open(history_file, 'r') as f:
            history = json.load(f)
        commit = {
            "timestamp": datetime.now().isoformat()[:16],
            "operation": operation,
            "path": path or "",
            "message": message
        }
        history.insert(0, commit)
        history = history[:25]
        with open(history_file, 'w') as f:
            json.dump(history, f, indent=2)
    except Exception as e:
        print(f"Warning: Could not log commit to history: {e}", file=sys.stderr)

def is_file_locked(filepath):
    """Check if a file is locked by another process."""
    try:
        with open(filepath, 'r+'):
            return False
    except (PermissionError, OSError):
        return True

def should_skip_path(path_str):
    """Check if a path should be skipped (e.g., node_modules)."""
    path_parts = Path(path_str).parts
    return 'node_modules' in path_parts

def check_result_size(result):
    """Check if the result is too large and return a warning message if it is."""
    result_json = json.dumps(result)
    result_size = len(result_json)
    
    if result_size > MAX_RESULT_SIZE:
        op_type = result.get("operation_type", "operation")
        path = result.get("path", "")
        count = result.get("count", 0)
        detail = ""
        if path:
            detail += f" for '{path}'"
        if count:
            detail += f" ({count} items)"
        return {
            "error": f"Result too large ({result_size} characters)",
            "message": f"The {op_type} result{detail} exceeds the size limit of {MAX_RESULT_SIZE} characters. Try a more specific operation or request fewer items.",
            "suggestions": [
                "Use more specific paths",
                "Filter results with patterns",
                "Request fewer lines (use start_line and end_line)",
                "Use search with more specific terms",
                "Break your task into smaller operations"
            ]
        }
    return result

def build_run_command_description():
    if not CLI_CONFIG:
        return """  COMMAND OPERATIONS:
  - run_command: {
      "command": str (required — shell command string to execute),
      "shell": "cmd" or "powershell" (optional, default: "cmd")
    }"""

    available_shells = CLI_CONFIG.get("available_shells", ["cmd"])
    ps_available = CLI_CONFIG.get("powershell_available", False)
    example_path = CLI_CONFIG.get("example_path", "C:\\Users\\username\\Desktop")
    home_dir = CLI_CONFIG.get("home_dir", "C:\\Users\\username")

    shells_str = " or ".join(f'"{s}"' for s in available_shells)

    cmd_example = f'dir "{example_path}"'
    ps_example = f'Get-ChildItem "{example_path}"'

    if ps_available:
        examples = f'cmd example:        "{cmd_example}"\n    PowerShell example: "{ps_example}"'
        chain_note = "cmd chains with &&, PowerShell chains with ;"
    else:
        examples = f'cmd example: "{cmd_example}"'
        chain_note = "Chain commands with &&"

    return f"""  COMMAND OPERATIONS:
  - run_command: {{
      "command": str (required — shell command string to execute),
      "shell": {shells_str} (optional, default: "cmd")
    }}
    You are on Windows. Home directory: {home_dir}
    Available shells: {", ".join(available_shells)}
    {chain_note}
    {examples}"""

# Create the low-level MCP server
server = Server("MCP Codebase Browser")

@server.list_tools()
async def list_tools() -> list[types.Tool]:
    """List available tools."""
    return [
        types.Tool(
            name="codebase_browser",
            description=f"""All-in-one codebase browser tool for file management, editing, searching, and more.

Parameters:
- operation: (Required) Operation to perform, one of the following groups:

  1. FILE OPERATIONS:
     - "read": Read file content (requires path)
     - "write": Write content to a file (requires path, options.content, and message)
     - "delete": Delete a file (requires path and message)
     - "move": Move a file or directory (requires path, options.destination, and message)
     - "copy": Copy a file or directory (requires path, options.destination, and message)
     - "list": List directory contents (requires path)
     - "mkdir": Create a directory (requires path and message)
     - "rmdir": Remove a directory (requires path and message)

  2. EDIT OPERATIONS:
     - "edit": Edit file content with targeted find/replace (requires path and message)

  3. SEARCH OPERATIONS:
     - "search": Search for text across all files (requires options.search_term)

  4. BACKUP OPERATIONS:
     - "backup_create": Create a backup of the codebase
     - "backup_list": List available backups
     - "backup_restore": Restore from a backup (requires options.name)
     - "browse_backup": Browse backup contents read-only (requires options.name)

  5. HISTORY OPERATIONS:
     - "read_recent_commits": Read recent commit history

  6. {build_run_command_description()}

- path: File or directory path, relative to the codebase root. NOT an absolute path.

- message: Required for all write/edit/delete/move/copy/mkdir/rmdir/run_command operations.
           Brief description of the change, e.g. "fix typo in error handler"

- options: Additional parameters depending on operation:

  FILE OPERATIONS:
  - read: {{
      "start_line": int (optional),
      "end_line": int (optional),
      "format": "text" or "lines" (optional, default: "text")
    }}
  - write: {{
      "content": str (required — full file content to write)
    }}
  - move / copy: {{
      "destination": str (required),
      "overwrite": bool (optional, default: false)
    }}
  - list: {{
      "pattern": str (optional glob pattern, default: "**/*")
    }}
  - rmdir: {{
      "recursive": bool (optional, default: false)
    }}

  EDIT OPERATIONS:
  - edit: Use either "operations" (targeted edits) or "new_content" (full replacement), not both.
    {{
      "operations": [
        {{
          "mode": "replace" (required),
          "find": str (required — exact text to find, including whitespace and indentation),
          "replace": str (required — replacement text),
          "occurrence": int (optional, which occurrence to replace, default: 1)
        }},
        ... (multiple operations are batched in a single call)
      ],
      "new_content": str (optional — replaces entire file content, ignores operations)
    }}

    IMPORTANT: "find" must match exactly, including indentation and newlines.
    If operations_applied returns 0, the find string did not match — read the file first to verify.

    BATCHING EXAMPLE — multiple edits in one call:
    {{
      "operations": [
        {{"mode": "replace", "find": "old_function_name", "replace": "new_function_name"}},
        {{"mode": "replace", "find": "version = '1.0'", "replace": "version = '1.1'"}}
      ]
    }}

  SEARCH OPERATIONS:
  - search: {{
      "search_term": str (required),
      "file_pattern": str (optional glob, default: "**/*"),
      "case_sensitive": bool (optional, default: false),
      "max_results": int (optional, default: 200),
      "max_display_results": int (optional, default: 25)
    }}

  BACKUP OPERATIONS:
  - backup_create: {{ "name": str (optional, default: timestamp-based) }}
  - backup_restore: {{ "name": str (required) }}
  - browse_backup: {{ "name": str (required), "path": str (optional) }}

Returns:
  - Success: {{"success": true, ...relevant data...}}
  - Error: {{"error": "message"}}
  - read: {{"content": str, "count": int}} or {{"lines": [...], "count": int}}
  - list: {{"files": [...], "directories": [...]}}
  - search: {{"matches": [...], "totalMatches": int, "filesWithMatches": int}}
  - edit: {{"success": true, "operations_applied": int}} — if operations_applied is 0, the find string did not match
  - run_command: {{"success": bool, "exit_code": int, "stdout": str, "stderr": str}}""",
            inputSchema={
                "type": "object",
                "properties": {
                    "operation": {
                        "type": "string",
                        "description": "Operation to perform. See tool description for full list and usage."
                    },
                    "path": {
                        "type": "string",
                        "description": "File or directory path, relative to codebase root. NOT an absolute path."
                    },
                    "options": {
                        "type": "object",
                        "description": "Additional parameters for the operation. See tool description for per-operation details."
                    },
                    "message": {
                        "type": "string",
                        "description": "Required for write operations. Brief description of the change being made."
                    }
                },
                "required": ["operation"]
            }
        )
    ]

@server.call_tool()
async def call_tool(name: str, arguments: dict[str, Any]) -> list[types.TextContent]:
    """Handle tool calls."""
    if name != "codebase_browser":
        return [types.TextContent(type="text", text=json.dumps({"error": f"Unknown tool: {name}"}))]
    
    operation = arguments.get("operation")
    path = arguments.get("path")
    options = arguments.get("options", {})
    message = arguments.get("message")
    
    try:
        result = {}
        result_metadata = {"operation_type": operation, "path": path}
        
        # FILE OPERATIONS
        if operation in ["read", "write", "delete", "move", "copy", "list", "mkdir", "rmdir"]:
            result = _handle_file_operations(operation, path, options, message)
        # EDIT OPERATIONS
        elif operation == "edit":
            result = _handle_edit_operations(path, options, message)
        # SEARCH OPERATIONS
        elif operation == "search":
            result = _handle_search_operations(options)
        # BACKUP OPERATIONS
        elif operation in ["backup_create", "backup_list", "backup_restore", "browse_backup"]:
            result = _handle_backup_operations(operation.replace("backup_", ""), options)
        # HISTORY OPERATIONS
        elif operation == "read_recent_commits":
            result = _handle_history_operations()
        # CLI OPERATIONS
        elif operation == "run_command":
            result = _handle_run_command_operations(options, message)
        else:
            result = {"error": f"Unknown operation: {operation}. See documentation for valid operations."}
        
        result.update(result_metadata)
        result = check_result_size(result)
        return [types.TextContent(type="text", text=json.dumps(result))]
        
    except Exception as e:
        error_result = {
            "error": f"Unexpected error: {str(e)}",
            "traceback": traceback.format_exc()
        }
        return [types.TextContent(type="text", text=json.dumps(error_result))]

def _handle_file_operations(operation, path, options, message):
    """Handle all file system operations."""
    if path is None:
        return {"error": "Path is required for file operations"}
    
    write_operations = ["write", "delete", "move", "copy", "mkdir", "rmdir"]
    if operation in write_operations and not message:
        return {"error": f"Message parameter is required for {operation} operation. Provide a brief description of the change."}
        
    full_path = Path(CODEBASE_PATH) / path
    
    try:
        # LIST DIRECTORY
        if operation == "list":
            pattern = options.get("pattern", "**/*")
            dir_path = full_path
            
            if not dir_path.exists():
                return {"error": "Directory not found"}
            
            files = []
            for f in glob.glob(str(dir_path / pattern), recursive=True):
                if os.path.isfile(f):
                    rel_path = str(Path(f).relative_to(dir_path))
                    if not should_skip_path(rel_path):
                        files.append(rel_path)
            
            dirs = []
            for d in os.scandir(str(dir_path)):
                if d.is_dir() and not should_skip_path(d.name):
                    dirs.append(d.name + '/')
            
            return {
                "files": files,
                "directories": dirs,
                "path": path
            }
            
        # READ FILE
        elif operation == "read":
            if not full_path.exists():
                return {"error": "File not found"}
                
            format = options.get("format", "text")
            start_line = options.get("start_line")
            end_line = options.get("end_line")
            
            if start_line is not None and format == "text":
                format = "lines"
            
            with open(full_path, 'r', encoding='utf-8', errors='replace') as f:
                content = f.read()
                
            if len(content) > MAX_RESULT_SIZE:
                content_length = len(content)
                line_count = content.count('\n') + 1
                
                if start_line is None:
                    return {
                        "error": "File too large",
                        "message": f"The file ({path}) is {content_length} characters long with {line_count} lines, which exceeds the size limit. Use 'start_line' and 'end_line' to read specific portions.",
                        "file_size": content_length,
                        "line_count": line_count,
                        "max_size": MAX_RESULT_SIZE
                    }
                
            if start_line is not None:
                lines = content.splitlines(True)
                start_idx = max(0, start_line - 1)
                end_idx = end_line if end_line is not None else start_idx + 1
                filtered_lines = lines[start_idx:end_idx]
                
                if format == "lines":
                    structured_lines = []
                    for i, line in enumerate(filtered_lines):
                        structured_lines.append({"lineNo": start_line + i, "content": line})
                    return {"lines": structured_lines, "count": len(structured_lines)}
                else:
                    filtered_content = "".join(filtered_lines)
                    return {"content": filtered_content, "count": filtered_content.count('\n') + 1}
            else:
                if format == "lines":
                    structured_lines = []
                    lines = content.splitlines(True)
                    for i, line in enumerate(lines):
                        structured_lines.append({"lineNo": i + 1, "content": line})
                    return {"lines": structured_lines, "count": len(structured_lines)}
                else:
                    return {"content": content, "count": content.count('\n') + 1}
                
        # WRITE FILE
        elif operation == "write":
            content = options.get("content")
            if content is None:
                return {"error": "content is required for write operation"}
            
            if full_path.exists() and is_file_locked(str(full_path)):
                return {
                    "error": "File is currently open",
                    "message": f"Cannot write to '{path}' because it appears to be open in another application. Please close the file and try again.",
                    "ai_instruction": "Cease all operations and INFORM THE USER before re-attempting ANY operation."
                }
                
            full_path.parent.mkdir(parents=True, exist_ok=True)
            
            with open(full_path, 'w', encoding='utf-8') as f:
                f.write(content)
            
            add_commit(operation, path, message)
            return {"success": True}
            
        # DELETE FILE
        elif operation == "delete":
            if not full_path.exists():
                return {"error": "File not found"}
                
            if not full_path.is_file():
                return {"error": "Path is not a file"}
            
            if is_file_locked(str(full_path)):
                return {
                    "error": "File is currently open",
                    "message": f"Cannot delete '{path}' because it appears to be open in another application. Please close the file and try again.",
                    "ai_instruction": "Cease all operations and INFORM THE USER before re-attempting ANY operation."
                }
                
            os.remove(full_path)
            add_commit(operation, path, message)
            return {"success": True}
                
        # MAKE DIRECTORY
        elif operation == "mkdir":
            full_path.mkdir(parents=True, exist_ok=True)
            add_commit(operation, path, message)
            return {"success": True}
            
        # REMOVE DIRECTORY
        elif operation == "rmdir":
            if not full_path.exists():
                return {"error": "Directory not found"}
                
            if not full_path.is_dir():
                return {"error": "Path is not a directory"}
                
            recursive = options.get("recursive", False)
            
            try:
                if recursive:
                    shutil.rmtree(full_path)
                else:
                    os.rmdir(full_path)
            except OSError as e:
                if not recursive:
                    return {"error": "Directory is not empty. Use recursive=True to remove non-empty directories."}
                else:
                    return {
                        "error": "Could not remove directory",
                        "message": f"Directory removal failed: {str(e)}",
                        "ai_instruction": "Cease all operations and INFORM THE USER before re-attempting ANY operation."
                    }
            
            add_commit(operation, path, message)
            return {"success": True}
            
        # MOVE FILE/DIRECTORY
        elif operation == "move":
            destination = options.get("destination")
            if not destination:
                return {"error": "destination is required for move operation"}
                
            dest_path = Path(CODEBASE_PATH) / destination
            
            if not full_path.exists():
                return {"error": "Source path not found"}
                
            overwrite = options.get("overwrite", False)
            
            if dest_path.exists() and not overwrite:
                return {"error": "Destination already exists. Set overwrite=True to replace it."}
            
            if full_path.is_file() and is_file_locked(str(full_path)):
                return {
                    "error": "File is currently open",
                    "message": f"Cannot move '{path}' because it appears to be open in another application. Please close the file and try again.",
                    "ai_instruction": "Cease all operations and INFORM THE USER before re-attempting ANY operation."
                }
                
            dest_path.parent.mkdir(parents=True, exist_ok=True)
            
            try:
                shutil.move(str(full_path), str(dest_path))
            except OSError as e:
                return {
                    "error": "Move operation failed",
                    "message": f"Could not move '{path}' to '{destination}': {str(e)}",
                    "ai_instruction": "Cease all operations and INFORM THE USER before re-attempting ANY operation."
                }
            
            add_commit(operation, f"{path} -> {destination}", message)
            return {"success": True}
            
        # COPY FILE/DIRECTORY
        elif operation == "copy":
            destination = options.get("destination")
            if not destination:
                return {"error": "destination is required for copy operation"}
                
            dest_path = Path(CODEBASE_PATH) / destination
            
            if not full_path.exists():
                return {"error": "Source path not found"}
                
            overwrite = options.get("overwrite", False)
            
            if dest_path.exists() and not overwrite:
                return {"error": "Destination already exists. Set overwrite=True to replace it."}
                
            dest_path.parent.mkdir(parents=True, exist_ok=True)
            
            try:
                if full_path.is_dir():
                    shutil.copytree(str(full_path), str(dest_path))
                else:
                    shutil.copy2(str(full_path), str(dest_path))
            except OSError as e:
                return {
                    "error": "Copy operation failed",
                    "message": f"Could not copy '{path}' to '{destination}': {str(e)}",
                    "ai_instruction": "Cease all operations and INFORM THE USER before re-attempting ANY operation."
                }
            
            add_commit(operation, f"{path} -> {destination}", message)
            return {"success": True}
        
    except Exception as e:
        return {
            "error": f"Error during file operation: {str(e)}",
            "ai_instruction": "Cease all operations and INFORM THE USER before re-attempting ANY operation."
        }


def _handle_edit_operations(path, options, message):
    """Handle file editing operations with simple string replacement."""
    if path is None:
        return {"error": "Path is required for edit operations"}
    
    if not message:
        return {"error": "Message parameter is required for edit operation. Provide a brief description of the change."}
        
    full_path = Path(CODEBASE_PATH) / path
    operations = options.get("operations", [])
    new_content = options.get("new_content")
    
    try:
        if new_content is not None:
            if full_path.exists() and is_file_locked(str(full_path)):
                return {
                    "error": "File is currently open",
                    "message": f"Cannot edit '{path}' because it appears to be open in another application. Please close the file and try again.",
                    "ai_instruction": "Cease all operations and INFORM THE USER before re-attempting ANY operation."
                }
                
            full_path.parent.mkdir(parents=True, exist_ok=True)
            
            with open(full_path, 'w', encoding='utf-8') as f:
                f.write(new_content)
            
            add_commit("edit", path, message)
            return {"success": True, "message": "File content replaced"}
            
        if not full_path.exists():
            return {"error": "File not found"}
        
        if is_file_locked(str(full_path)):
            return {
                "error": "File is currently open",
                "message": f"Cannot edit '{path}' because it appears to be open in another application. Please close the file and try again.",
                "ai_instruction": "Cease all operations and INFORM THE USER before re-attempting ANY operation."
            }
            
        with open(full_path, 'r', encoding='utf-8', errors='replace') as f:
            content = f.read()
            
        modified_content = content
        applied_operations = 0
        
        for op in operations:
            mode = op.get("mode", "")
            
            if mode == "replace" and "find" in op and "replace" in op:
                find_text = op["find"]
                replace_text = op["replace"]
                occurrence = op.get("occurrence", 1)
                
                if occurrence == 1:
                    if find_text in modified_content:
                        modified_content = modified_content.replace(find_text, replace_text, 1)
                        applied_operations += 1
                else:
                    start_pos = -1
                    for i in range(occurrence):
                        start_pos = modified_content.find(find_text, start_pos + 1)
                        if start_pos == -1:
                            break
                    
                    if start_pos != -1:
                        modified_content = (
                            modified_content[:start_pos] + 
                            replace_text + 
                            modified_content[start_pos + len(find_text):]
                        )
                        applied_operations += 1
        
        if applied_operations == 0 and operations:
            return {"success": False, "operations_applied": 0, "error": "No find strings matched. Read the file first to verify the exact text including whitespace and indentation."}

        with open(full_path, 'w', encoding='utf-8') as f:
            f.write(modified_content)
        
        add_commit("edit", path, message)
        return {"success": True, "operations_applied": applied_operations}
            
    except Exception as e:
        return {
            "error": f"Error during edit operation: {str(e)}",
            "ai_instruction": "Cease all operations and INFORM THE USER before re-attempting ANY operation."
        }


def _handle_search_operations(options):
    """Handle code search operations with simple match results."""
    search_term = options.get("search_term", "")
    file_pattern = options.get("file_pattern", "**/*")
    case_sensitive = options.get("case_sensitive", False)
    max_results = options.get("max_results", 200)
    max_display_results = options.get("max_display_results", 25)
    
    if not search_term:
        return {"error": "search_term is required for search operation"}
    
    matches = []
    total_matches = 0
    files_checked = 0
    files_with_matches = 0
    base_path = Path(CODEBASE_PATH)
    
    try:
        for root, _, files in os.walk(base_path):
            for filename in files:
                if total_matches >= max_results:
                    break
                    
                full_path = os.path.join(root, filename)
                rel_path = os.path.relpath(full_path, base_path)
                
                if should_skip_path(rel_path) or not fnmatch(rel_path, file_pattern):
                    continue
                
                files_checked += 1
                
                try:
                    if os.path.getsize(full_path) > 10 * 1024 * 1024:
                        continue
                        
                    with open(full_path, 'r', encoding='utf-8', errors='replace') as f:
                        lines = f.readlines()
                    
                    file_has_matches = False
                    
                    for line_idx, line in enumerate(lines):
                        clean_line = line.rstrip('\r\n\t ')
                        
                        if not clean_line:
                            continue
                            
                        if case_sensitive:
                            match_pos = clean_line.find(search_term)
                        else:
                            match_pos = clean_line.lower().find(search_term.lower())
                        
                        if match_pos != -1:
                            file_has_matches = True
                            
                            match_info = {
                                "file": rel_path,
                                "lineNumber": line_idx + 1,
                                "lineContent": clean_line,
                                "matchPosition": match_pos
                            }
                            
                            matches.append(match_info)
                            total_matches += 1
                            
                            if total_matches >= max_results:
                                break
                    
                    if file_has_matches:
                        files_with_matches += 1
                
                except Exception:
                    continue
        
        displayed_matches = matches[:max_display_results]
        truncated = len(matches) > max_display_results
        
        return {
            "matches": displayed_matches,
            "totalMatches": total_matches,
            "displayedMatches": len(displayed_matches),
            "filesWithMatches": files_with_matches,
            "filesChecked": files_checked,
            "searchTerm": search_term,
            "truncated": truncated,
            "message": f"Found {total_matches} matches in {files_with_matches} files. Showing {len(displayed_matches)} matches." if truncated else None,
            "options": {
                "filePattern": file_pattern,
                "caseSensitive": case_sensitive
            }
        }
        
    except Exception as e:
        return {"error": f"Error searching codebase: {str(e)}"}


def _handle_backup_operations(operation, options):
    """Handle backup operations for the codebase."""
    try:
        backup_root = script_dir / "Backups"
        
        if not backup_root.exists() and operation != "list":
            backup_root.mkdir(parents=True)
            print(f"Created Backups directory at: {backup_root}", file=sys.stderr)
            
        if operation == "list":
            if not backup_root.exists():
                return {
                    "backups": [],
                    "count": 0,
                    "message": "No backups available yet. Use codebase_browser operation='backup_create' to create a backup."
                }
                
            backups = []
            for item in backup_root.iterdir():
                if item.is_dir():
                    try:
                        created_time = item.stat().st_ctime
                        created_time_str = datetime.fromtimestamp(created_time).strftime("%Y-%m-%d %H:%M:%S")
                        
                        size_bytes = sum(f.stat().st_size for f in item.glob('**/*') if f.is_file())
                        size_mb = size_bytes / (1024 * 1024)
                        
                        backups.append({
                            "name": item.name,
                            "created": created_time_str,
                            "size_mb": round(size_mb, 2)
                        })
                    except Exception:
                        backups.append({"name": item.name})
            
            backups.sort(key=lambda x: x.get("created", ""), reverse=True)
            
            return {
                "backups": backups,
                "count": len(backups),
                "backup_root": "Backups"
            }
            
        elif operation == "create":
            backup_name = options.get("name")
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            
            if backup_name is None:
                backup_name = f"backup_{timestamp}"
            else:
                clean_name = re.sub(r'[^\w\-\.]', '_', backup_name)
                backup_name = f"{clean_name}_{timestamp}"
            
            backup_path = backup_root / backup_name
            
            if backup_path.exists():
                return {
                    "success": False,
                    "error": f"Backup with name '{backup_name}' already exists. This shouldn't happen with timestamp suffix."
                }
            
            source_path = Path(CODEBASE_PATH)
            shutil.copytree(source_path, backup_path)
            
            return {
                "success": True,
                "message": f"Successfully created backup '{backup_name}'",
                "backup_name": backup_name
            }
            
        elif operation == "restore":
            backup_name = options.get("name")
            if not backup_name:
                return {"error": "name is required for backup_restore operation"}
                
            backup_path = backup_root / backup_name
            
            if not backup_path.exists() or not backup_path.is_dir():
                return {
                    "success": False,
                    "error": f"Backup '{backup_name}' not found. Use codebase_browser operation='backup_list' to see available backups."
                }
            
            target_path = Path(CODEBASE_PATH)
            
            locked_files = []
            for item in target_path.rglob('*'):
                if item.is_file() and is_file_locked(str(item)):
                    locked_files.append(str(item.relative_to(target_path)))
            
            if locked_files:
                return {
                    "error": "Files are currently open",
                    "message": f"Cannot restore because {len(locked_files)} files appear to be open in other applications. Please close all files and try again.",
                    "locked_files": locked_files[:5],
                    "ai_instruction": "Cease all operations and INFORM THE USER before re-attempting ANY operation."
                }
            
            try:
                if target_path.exists():
                    for item in target_path.iterdir():
                        if item.is_dir():
                            shutil.rmtree(item)
                        else:
                            os.remove(item)
                else:
                    target_path.mkdir(parents=True)
                
                for item in backup_path.iterdir():
                    if item.is_dir():
                        shutil.copytree(item, target_path / item.name)
                    else:
                        shutil.copy2(item, target_path / item.name)
            except Exception as e:
                return {
                    "error": "Restore operation failed",
                    "message": f"Could not restore from backup '{backup_name}': {str(e)}",
                    "ai_instruction": "Cease all operations and INFORM THE USER before re-attempting ANY operation."
                }
            
            return {
                "success": True,
                "message": f"Successfully restored codebase from backup '{backup_name}'",
                "backup_name": backup_name
            }
        
        elif operation == "browse":
            backup_name = options.get("name")
            browse_path = options.get("path", "")
            
            if not backup_name:
                return {"error": "name is required for browse_backup operation"}
                
            backup_path = backup_root / backup_name
            
            if not backup_path.exists() or not backup_path.is_dir():
                return {
                    "error": f"Backup '{backup_name}' not found. Use codebase_browser operation='backup_list' to see available backups."
                }
            
            full_browse_path = backup_path
            if browse_path:
                full_browse_path = backup_path / browse_path
                
            if not full_browse_path.exists():
                return {"error": f"Path '{browse_path}' not found in backup '{backup_name}'"}
            
            if full_browse_path.is_file():
                try:
                    with open(full_browse_path, 'r', encoding='utf-8', errors='replace') as f:
                        content = f.read()
                    return {
                        "type": "file",
                        "content": content,
                        "path": browse_path or full_browse_path.name,
                        "backup_name": backup_name,
                        "read_only": True,
                        "message": "This is a READ-ONLY view from backup. Use backup_restore to restore files for editing."
                    }
                except Exception as e:
                    return {"error": f"Could not read file: {str(e)}"}
            else:
                files = []
                dirs = []
                
                for item in full_browse_path.iterdir():
                    if item.is_file():
                        files.append(item.name)
                    elif item.is_dir():
                        dirs.append(item.name + "/")
                
                return {
                    "type": "directory",
                    "files": files,
                    "directories": dirs,
                    "path": browse_path,
                    "backup_name": backup_name,
                    "read_only": True,
                    "message": "This is a READ-ONLY view from backup. Use backup_restore to restore files for editing."
                }
            
        else:
            return {"error": f"Unknown backup operation: {operation}"}
            
    except Exception as e:
        return {"error": f"Error during backup_{operation}: {str(e)}"}


def _handle_history_operations():
    """Handle history operations."""
    try:
        history_file = get_history_file()
        
        with open(history_file, 'r') as f:
            history = json.load(f)
        
        if not history:
            return {
                "commits": [],
                "count": 0,
                "message": "No recent history found, this is normal. Any changes the AI makes to the project will create a history."
            }
        
        return {
            "commits": history,
            "count": len(history),
            "message": f"Showing {len(history)} recent commits (newest first)"
        }
        
    except Exception as e:
        return {
            "commits": [],
            "count": 0,
            "message": "No recent history found, this is normal. Any changes the AI makes to the project will create a history."
        }


def _handle_run_command_operations(options, message):
    """Handle CLI command execution operations."""
    command = options.get("command")
    shell = options.get("shell", "cmd").lower()

    if not command:
        return {"error": "command is required for run_command operation"}

    if not message:
        return {"error": "message is required for run_command operation to track intent"}

    if not CLI_CONFIG:
        return {
            "error": "CLI not configured",
            "message": "cli_config.json not found. Run setup.bat to generate it."
        }

    available_shells = [s.lower() for s in CLI_CONFIG.get("available_shells", ["cmd"])]
    if shell not in available_shells:
        return {"error": f"Shell '{shell}' is not available on this machine. Available: {', '.join(available_shells)}"}

    if shell == "powershell":
        full_command = ["powershell", "-NoProfile", "-NonInteractive", "-Command", command]
    else:
        full_command = ["cmd", "/c", command]

    try:
        result = subprocess.run(
            full_command,
            stdin=subprocess.DEVNULL,
            capture_output=True,
            text=True
        )
    except Exception as e:
        return {
            "error": f"Error executing command: {str(e)}",
            "traceback": traceback.format_exc(),
            "command": command
        }

    add_commit("run_command", command, message)

    return {
        "success": result.returncode == 0,
        "exit_code": result.returncode,
        "stdout": result.stdout,
        "stderr": result.stderr,
        "command": command,
        "shell_used": shell
    }


async def main():
    """Run the MCP server."""
    async with mcp.server.stdio.stdio_server() as streams:
        await server.run(streams[0], streams[1], server.create_initialization_options())


if __name__ == "__main__":
    import anyio
    anyio.run(main)