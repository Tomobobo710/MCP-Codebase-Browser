from mcp.server.fastmcp import FastMCP
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

# Auto-detect CODEBASE_PATH relative to script location
CODEBASE_PATH = None  # Automatically determined relative to script

# Maximum result size in characters (serialized JSON)
MAX_RESULT_SIZE = 99000

def get_codebase_path():
    """
    Automatically determine the codebase path based on script location.
    
    Returns:
        str: The absolute path to the Project directory.
    """
    script_dir = Path(os.path.dirname(os.path.abspath(__file__)))
    project_dir = script_dir / "Project"
    
    # Create Project directory if it doesn't exist
    if not project_dir.exists():
        os.makedirs(project_dir)
        print(f"Created Project directory at: {project_dir}")
        # Add a README file to explain what to do
        with open(project_dir / "README.txt", "w") as f:
            f.write("Put your project files in this directory.\n")
            f.write("They will be automatically indexed by the MCP Codebase Browser.\n")
    
    return str(project_dir)

# Set up the codebase path
if CODEBASE_PATH is None:
    CODEBASE_PATH = get_codebase_path()

# Create an MCP server
mcp = FastMCP("MCP Codebase Browser")

def get_history_path():
    """Get the path to the history directory and ensure it exists."""
    script_dir = Path(os.path.dirname(os.path.abspath(__file__)))
    history_dir = script_dir / "History"
    history_dir.mkdir(exist_ok=True)
    return history_dir

def get_history_file():
    """Get the path to the history file and ensure it exists."""
    history_dir = get_history_path()
    history_file = history_dir / "commits.json"
    
    if not history_file.exists():
        # Create empty history file
        with open(history_file, 'w') as f:
            json.dump([], f)
    
    return history_file

def add_commit(operation, path, message):
    """Add a commit entry to the history file with FIFO management."""
    try:
        history_file = get_history_file()
        
        # Read existing history
        with open(history_file, 'r') as f:
            history = json.load(f)
        
        # Create new commit entry
        commit = {
            "timestamp": datetime.now().isoformat()[:16],  # Compact: 2023-12-15T14:30
            "operation": operation,
            "path": path or "",
            "message": message
        }
        
        # Add to beginning of list (newest first)
        history.insert(0, commit)
        
        # Keep only last 25 commits (FIFO)
        history = history[:25]
        
        # Write back to file
        with open(history_file, 'w') as f:
            json.dump(history, f, indent=2)
            
    except Exception as e:
        # Don't fail operations if history logging fails
        print(f"Warning: Could not log commit to history: {e}")

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
    """
    Check if the result is too large and return a warning message if it is.
    
    Args:
        result (dict): The result to check
        
    Returns:
        dict: The original result if it's not too large, or a warning message if it is.
    """
    # Serialize the result to JSON to get its approximate size
    result_json = json.dumps(result)
    result_size = len(result_json)
    
    # If the result is too large, return a warning message instead
    if result_size > MAX_RESULT_SIZE:
        op_type = result.get("operation_type", "operation")
        
        # Try to extract relevant metadata about what was being requested
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

@mcp.tool()
def codebase_browser(operation: str, path: str = None, options: dict = None, message: str = None):
    """
    All-in-one codebase browser tool for file management, editing, searching, and more.
    
    Parameters:
    - operation: (Required) Operation to perform, one of the following groups:
    
      1. FILE OPERATIONS: 
         - "read": Read file content (requires path)
         - "write": Write content to a file (requires path and message)
         - "delete": Delete a file (requires path and message)
         - "move": Move a file or directory (requires path, destination, and message)
         - "copy": Copy a file or directory (requires path, destination, and message)
         - "list": List directory contents (requires path)
         - "mkdir": Create a directory (requires path and message)
         - "rmdir": Remove a directory (requires path and message)
      
      2. EDIT OPERATIONS:
         - "edit": Edit file content with replace operations (requires path and message)
      
      3. SEARCH OPERATIONS:
         - "search": Search for content in files (requires search_term)
      
      4. BACKUP OPERATIONS:
         - "backup_create": Create a backup of the codebase (path not required)
         - "backup_list": List available backups (path not required)
         - "backup_restore": Restore from a backup (path not required, requires name)
         - "browse_backup": Browse backup contents READ-ONLY (requires backup name)
      
      5. HISTORY OPERATIONS:
         - "read_recent_commits": Read recent commit history (no other parameters needed)
    
    - path: (Required for most operations) File or directory path to operate on
           Paths are relative to the codebase root directory
    
    - message: (Required for write operations) Brief description of the change being made
              Examples: "fixed typo in error message preventing proper user feedback"
                       "updated function signature in utils.py to accept optional timeout parameter"
                       "refactored database connection logic to use connection pooling"
    
    - options: (Optional) Additional parameters for specific operations:
    
      1. FILE OPERATIONS:
         - read: {
             "format": "text" or "lines" (Optional, default: "text"),
             "start_line": int (Optional, specifying line numbers will automatically use "lines" format),
             "end_line": int (Optional, defaults to start_line+1 if start_line is provided)
           }
         - write: {
             "content": str (Required, text to write to the file)
           }
         - move: {
             "destination": str (Required, destination path),
             "overwrite": bool (Optional, default: False)
           }
         - copy: {
             "destination": str (Required, destination path),
             "overwrite": bool (Optional, default: False)
           }
         - list: {
             "pattern": str (Optional, glob pattern for filtering, default: "**/*")
           }
         - rmdir: {
             "recursive": bool (Optional, whether to remove non-empty directories, default: False)
           }
      
      2. EDIT OPERATIONS:
         - edit: (Use either operations or new_content, not both)
           {
             "operations": [ (Optional list of replace operations - can batch multiple edits in one call)
               {
                 "mode": "replace" (Required),
                 "find": str (Required, text to find),
                 "replace": str (Required, replacement text),
                 "occurrence": int (Optional, which occurrence to modify, default: 1)
               },
               {
                 "mode": "replace",
                 "find": str (Another find/replace in the same file),
                 "replace": str,
                 "occurrence": int (Optional, default: 1)
               }
               ... (can include many operations to batch edits efficiently)
             ],
             "new_content": str (Optional, complete replacement for file content. If provided, operations are ignored)
           }
           
           BATCHING EXAMPLE - Multiple edits in one call:
           {
             "operations": [
               {"mode": "replace", "find": "old_function_name", "replace": "new_function_name"},
               {"mode": "replace", "find": "TODO: implement", "replace": "# Implemented"},
               {"mode": "replace", "find": "version = '1.0'", "replace": "version = '1.1'"}
             ]
           }
      
      3. SEARCH OPERATIONS:
         - search: {
             "search_term": str (Required, text to search for),
             "file_pattern": str (Optional, glob pattern for filtering files, default: "**/*"),
             "case_sensitive": bool (Optional, whether search is case-sensitive, default: False),
             "max_results": int (Optional, maximum number of total matches to find, default: 200),
             "max_display_results": int (Optional, maximum number of matches to display, default: 25)
           }
      
      4. BACKUP OPERATIONS:
         - backup_create: {
             "name": str (Optional, custom name for the backup, default: timestamp-based name)
           }
         - backup_list: {} (No additional options required)
         - backup_restore: {
             "name": str (Required, name of the backup to restore)
           }
         - browse_backup: {
             "name": str (Required, name of the backup to browse),
             "path": str (Optional, specific path within backup to browse, default: root)
           }
      
      5. HISTORY OPERATIONS:
         - read_recent_commits: {} (No additional options required)
    
    Returns:
        dict: Response varies by operation, but typically includes:
              - For successful operations: {"success": True, ...relevant data...}
              - For unsuccessful operations: {"error": "Error message"}
              - For read operations: {"content": str} or {"lines": list[dict]}
              - For list operations: {"files": list[str], "directories": list[str]}
              - For search operations: {"matches": list[dict], "totalMatches": int, "filesWithMatches": int, ...}
              - For backup operations: Operation-specific status and data
              - For history operations: {"commits": list[dict], ...}
    """
    options = options or {}
    
    # Track what operation is being performed for error messages
    result_metadata = {"operation_type": operation, "path": path}
    
    # GROUP 1: FILE OPERATIONS
    if operation in ["read", "write", "delete", "move", "copy", "list", "mkdir", "rmdir"]:
        result = _handle_file_operations(operation, path, options, message)
        result.update(result_metadata)
        return check_result_size(result)
    
    # GROUP 2: EDIT OPERATIONS
    elif operation == "edit":
        result = _handle_edit_operations(path, options, message)
        result.update(result_metadata)
        return check_result_size(result)
    
    # GROUP 3: SEARCH OPERATIONS
    elif operation == "search":
        result = _handle_search_operations(options)
        result.update(result_metadata)
        return check_result_size(result)
    
    # GROUP 4: BACKUP OPERATIONS
    elif operation in ["backup_create", "backup_list", "backup_restore", "browse_backup"]:
        result = _handle_backup_operations(operation.replace("backup_", ""), options)
        result.update(result_metadata)
        return check_result_size(result)
    
    # GROUP 5: HISTORY OPERATIONS
    elif operation == "read_recent_commits":
        result = _handle_history_operations()
        result.update(result_metadata)
        return check_result_size(result)
    
    else:
        return {"error": f"Unknown operation: {operation}. See documentation for valid operations."}


def _handle_file_operations(operation, path, options, message):
    """
    Handle all file system operations.
    
    Args:
        operation (str): The file operation to perform.
        path (str): File or directory path to operate on.
        options (dict): Additional options for the operation.
        message (str): Commit message for write operations.
        
    Returns:
        dict: Operation result.
    """
    if path is None:
        return {"error": "Path is required for file operations"}
    
    # Check if message is required for write operations
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
            
            # Get files matching pattern, excluding node_modules
            files = []
            for f in glob.glob(str(dir_path / pattern), recursive=True):
                if os.path.isfile(f):
                    rel_path = str(Path(f).relative_to(dir_path))
                    if not should_skip_path(rel_path):
                        files.append(rel_path)
            
            # Get directories, excluding node_modules
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
            
            # Auto-switch to lines format if line filtering is requested
            if start_line is not None and format == "text":
                format = "lines"
            
            with open(full_path, 'r', encoding='utf-8', errors='replace') as f:
                content = f.read()
                
            # Check file size before processing - if it's too large, return early
            if len(content) > MAX_RESULT_SIZE:
                content_length = len(content)
                line_count = content.count('\n') + 1
                
                # If no line filtering is requested but the file is too large, 
                # provide guidance on using line filtering
                if start_line is None:
                    return {
                        "error": "File too large",
                        "message": f"The file ({path}) is {content_length} characters long with {line_count} lines, which exceeds the size limit. Use 'start_line' and 'end_line' to read specific portions.",
                        "file_size": content_length,
                        "line_count": line_count,
                        "max_size": MAX_RESULT_SIZE
                    }
                
            # Split content into lines for both formats if line filtering is requested
            if start_line is not None:
                lines = content.splitlines(True)
                start_idx = max(0, start_line - 1)
                end_idx = end_line if end_line is not None else start_idx + 1
                
                # Apply line filtering
                filtered_lines = lines[start_idx:end_idx]
                
                if format == "lines":
                    # Return structured line objects
                    structured_lines = []
                    for i, line in enumerate(filtered_lines):
                        structured_lines.append({
                            "lineNo": start_line + i,
                            "content": line
                        })
                        
                    return {
                        "lines": structured_lines,
                        "count": len(structured_lines)
                    }
                else:
                    # Return filtered text content
                    filtered_content = "".join(filtered_lines)
                    return {
                        "content": filtered_content,
                        "count": filtered_content.count('\n') + 1
                    }
            else:
                # No line filtering requested
                if format == "lines":
                    # Return all lines in structured format
                    structured_lines = []
                    lines = content.splitlines(True)
                    for i, line in enumerate(lines):
                        structured_lines.append({
                            "lineNo": i + 1,
                            "content": line
                        })
                        
                    return {
                        "lines": structured_lines,
                        "count": len(structured_lines)
                    }
                else:
                    # Return complete content
                    return {
                        "content": content,
                        "count": content.count('\n') + 1
                    }
                
        # WRITE FILE
        elif operation == "write":
            content = options.get("content")
            if content is None:
                return {"error": "content is required for write operation"}
            
            # Check if file is locked
            if full_path.exists() and is_file_locked(str(full_path)):
                return {
                    "error": "File is currently open",
                    "message": f"Cannot write to '{path}' because it appears to be open in another application. Please close the file and try again.",
                    "ai_instruction": "Cease all operations and INFORM THE USER before re-attempting ANY operation."
                }
                
            full_path.parent.mkdir(parents=True, exist_ok=True)
            
            with open(full_path, 'w', encoding='utf-8') as f:
                f.write(content)
            
            # Log to history
            add_commit(operation, path, message)
                
            return {"success": True}
            
        # DELETE FILE
        elif operation == "delete":
            if not full_path.exists():
                return {"error": "File not found"}
                
            if not full_path.is_file():
                return {"error": "Path is not a file"}
            
            # Check if file is locked
            if is_file_locked(str(full_path)):
                return {
                    "error": "File is currently open",
                    "message": f"Cannot delete '{path}' because it appears to be open in another application. Please close the file and try again.",
                    "ai_instruction": "Cease all operations and INFORM THE USER before re-attempting ANY operation."
                }
                
            os.remove(full_path)
            
            # Log to history
            add_commit(operation, path, message)
            
            return {"success": True}
                
        # MAKE DIRECTORY
        elif operation == "mkdir":
            full_path.mkdir(parents=True, exist_ok=True)
            
            # Log to history
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
                    os.rmdir(full_path)  # Will only work if directory is empty
            except OSError as e:
                if not recursive:
                    return {"error": "Directory is not empty. Use recursive=True to remove non-empty directories."}
                else:
                    return {
                        "error": "Could not remove directory",
                        "message": f"Directory removal failed: {str(e)}",
                        "ai_instruction": "Cease all operations and INFORM THE USER before re-attempting ANY operation."
                    }
            
            # Log to history
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
            
            # Check if source file is locked
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
            
            # Log to history
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
            
            # Log to history
            add_commit(operation, f"{path} -> {destination}", message)
            
            return {"success": True}
        
    except Exception as e:
        return {
            "error": f"Error during file operation: {str(e)}",
            "ai_instruction": "Cease all operations and INFORM THE USER before re-attempting ANY operation."
        }


def _handle_edit_operations(path, options, message):
    """
    Handle file editing operations with simple string replacement.
    
    Args:
        path (str): Path to the file to edit.
        options (dict): Edit options including operations or new_content.
        message (str): Commit message for the edit.
        
    Returns:
        dict: Edit operation result.
    """
    if path is None:
        return {"error": "Path is required for edit operations"}
    
    if not message:
        return {"error": "Message parameter is required for edit operation. Provide a brief description of the change."}
        
    full_path = Path(CODEBASE_PATH) / path
    operations = options.get("operations", [])
    new_content = options.get("new_content")
    
    try:
        # Handle full file replacement
        if new_content is not None:
            # Check if file is locked
            if full_path.exists() and is_file_locked(str(full_path)):
                return {
                    "error": "File is currently open",
                    "message": f"Cannot edit '{path}' because it appears to be open in another application. Please close the file and try again.",
                    "ai_instruction": "Cease all operations and INFORM THE USER before re-attempting ANY operation."
                }
                
            # Create parent directories if they don't exist
            full_path.parent.mkdir(parents=True, exist_ok=True)
            
            with open(full_path, 'w', encoding='utf-8') as f:
                f.write(new_content)
            
            # Log to history
            add_commit("edit", path, message)
                
            return {"success": True, "message": "File content replaced"}
            
        # Check if file exists
        if not full_path.exists():
            return {"error": "File not found"}
        
        # Check if file is locked
        if is_file_locked(str(full_path)):
            return {
                "error": "File is currently open",
                "message": f"Cannot edit '{path}' because it appears to be open in another application. Please close the file and try again.",
                "ai_instruction": "Cease all operations and INFORM THE USER before re-attempting ANY operation."
            }
            
        # Read original content
        with open(full_path, 'r', encoding='utf-8', errors='replace') as f:
            content = f.read()
            
        modified_content = content
        applied_operations = 0
        
        # Apply each operation
        for op in operations:
            mode = op.get("mode", "")
            
            if mode == "replace" and "find" in op and "replace" in op:
                find_text = op["find"]
                replace_text = op["replace"]
                occurrence = op.get("occurrence", 1)
                
                # Handle occurrence-specific replacement
                if occurrence == 1:
                    # Replace first occurrence
                    if find_text in modified_content:
                        modified_content = modified_content.replace(find_text, replace_text, 1)
                        applied_operations += 1
                else:
                    # Find the nth occurrence
                    start_pos = -1
                    for i in range(occurrence):
                        start_pos = modified_content.find(find_text, start_pos + 1)
                        if start_pos == -1:
                            break
                    
                    if start_pos != -1:
                        # Replace at the specific position
                        modified_content = (
                            modified_content[:start_pos] + 
                            replace_text + 
                            modified_content[start_pos + len(find_text):]
                        )
                        applied_operations += 1
        
        # Write the modified content back to the file
        with open(full_path, 'w', encoding='utf-8') as f:
            f.write(modified_content)
        
        # Log to history
        add_commit("edit", path, message)
            
        return {"success": True, "operations_applied": applied_operations}
            
    except Exception as e:
        return {
            "error": f"Error during edit operation: {str(e)}",
            "ai_instruction": "Cease all operations and INFORM THE USER before re-attempting ANY operation."
        }


def _handle_search_operations(options):
    """
    Handle code search operations with simple match results.
    
    Args:
        options (dict): Search parameters.
        
    Returns:
        dict: Search results - simple list of file/line matches.
    """
    search_term = options.get("search_term", "")
    file_pattern = options.get("file_pattern", "**/*")
    case_sensitive = options.get("case_sensitive", False)
    max_results = options.get("max_results", 200)  # Increased since results are smaller
    max_display_results = options.get("max_display_results", 25)  # Show more results
    
    if not search_term:
        return {"error": "search_term is required for search operation"}
    
    matches = []
    total_matches = 0
    files_checked = 0
    files_with_matches = 0
    base_path = Path(CODEBASE_PATH)
    
    try:
        # Find all files recursively
        for root, _, files in os.walk(base_path):
            for filename in files:
                if total_matches >= max_results:
                    break
                    
                full_path = os.path.join(root, filename)
                rel_path = os.path.relpath(full_path, base_path)
                
                # Skip node_modules and check pattern
                if should_skip_path(rel_path) or not fnmatch(rel_path, file_pattern):
                    continue
                
                files_checked += 1
                
                try:
                    # Skip very large files
                    if os.path.getsize(full_path) > 10 * 1024 * 1024:  # 10MB
                        continue
                        
                    # Read the file line by line
                    with open(full_path, 'r', encoding='utf-8', errors='replace') as f:
                        lines = f.readlines()
                    
                    file_has_matches = False
                    
                    # Search each line
                    for line_idx, line in enumerate(lines):
                        # Clean the line content - remove trailing whitespace and normalize
                        clean_line = line.rstrip('\r\n\t ')
                        
                        # Skip empty lines
                        if not clean_line:
                            continue
                            
                        # Check for match
                        if case_sensitive:
                            match_pos = clean_line.find(search_term)
                        else:
                            match_pos = clean_line.lower().find(search_term.lower())
                        
                        if match_pos != -1:
                            file_has_matches = True
                            
                            # Create simple match result
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
                
                except Exception as e:
                    continue
        
        # Return the requested number of results
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
    """
    Handle backup operations for the codebase.
    
    Args:
        operation (str): Backup operation to perform (create, list, restore, browse).
        options (dict): Additional options for the operation.
        
    Returns:
        dict: Operation result.
    """
    try:
        # Determine backup directory path
        script_dir = Path(os.path.dirname(os.path.abspath(__file__)))
        backup_root = script_dir / "Backups"
        
        # Ensure backup directory exists
        if not backup_root.exists() and operation != "list":
            backup_root.mkdir(parents=True)
            print(f"Created Backups directory at: {backup_root}")
            
        # LIST BACKUPS
        if operation == "list":
            if not backup_root.exists():
                return {
                    "backups": [],
                    "count": 0,
                    "message": "No backups available yet. Use codebase_browser operation='backup_create' to create a backup."
                }
                
            # Get all directories in the Backups folder
            backups = []
            for item in backup_root.iterdir():
                if item.is_dir():
                    # Get creation time for sorting/display
                    try:
                        created_time = item.stat().st_ctime
                        created_time_str = datetime.fromtimestamp(created_time).strftime("%Y-%m-%d %H:%M:%S")
                        
                        # Get size of backup
                        size_bytes = sum(f.stat().st_size for f in item.glob('**/*') if f.is_file())
                        size_mb = size_bytes / (1024 * 1024)
                        
                        backups.append({
                            "name": item.name,
                            "created": created_time_str,
                            "size_mb": round(size_mb, 2)
                        })
                    except Exception as e:
                        # If we can't get stats, just add the name
                        backups.append({"name": item.name})
            
            # Sort backups by creation time (newest first) if available
            backups.sort(key=lambda x: x.get("created", ""), reverse=True)
            
            return {
                "backups": backups,
                "count": len(backups),
                "backup_root": "Backups"  # Only show the folder name, not the full path
            }
            
        # CREATE BACKUP
        elif operation == "create":
            # Generate default backup name if none provided
            backup_name = options.get("name")
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            
            if backup_name is None:
                backup_name = f"backup_{timestamp}"
            else:
                # Sanitize the backup name to ensure it's a valid directory name
                clean_name = re.sub(r'[^\w\-\.]', '_', backup_name)
                backup_name = f"{clean_name}_{timestamp}"  # Always append timestamp
            
            # Create full backup path
            backup_path = backup_root / backup_name
            
            # Check if backup with this name already exists (shouldn't happen with timestamp)
            if backup_path.exists():
                return {
                    "success": False,
                    "error": f"Backup with name '{backup_name}' already exists. This shouldn't happen with timestamp suffix."
                }
            
            # Copy the entire codebase to the backup location
            source_path = Path(CODEBASE_PATH)
            shutil.copytree(source_path, backup_path)
            
            return {
                "success": True,
                "message": f"Successfully created backup '{backup_name}'",
                "backup_name": backup_name
            }
            
        # RESTORE BACKUP
        elif operation == "restore":
            backup_name = options.get("name")
            if not backup_name:
                return {"error": "name is required for backup_restore operation"}
                
            backup_path = backup_root / backup_name
            
            # Validate backup exists
            if not backup_path.exists() or not backup_path.is_dir():
                return {
                    "success": False,
                    "error": f"Backup '{backup_name}' not found. Use codebase_browser operation='backup_list' to see available backups."
                }
            
            # Get target directory (codebase path)
            target_path = Path(CODEBASE_PATH)
            
            # Check for locked files before starting restore
            locked_files = []
            for item in target_path.rglob('*'):
                if item.is_file() and is_file_locked(str(item)):
                    locked_files.append(str(item.relative_to(target_path)))
            
            if locked_files:
                return {
                    "error": "Files are currently open",
                    "message": f"Cannot restore because {len(locked_files)} files appear to be open in other applications. Please close all files and try again.",
                    "locked_files": locked_files[:5],  # Show first 5 locked files
                    "ai_instruction": "Cease all operations and INFORM THE USER before re-attempting ANY operation."
                }
            
            try:
                # Remove current codebase contents
                if target_path.exists():
                    # Remove all contents but keep the directory
                    for item in target_path.iterdir():
                        if item.is_dir():
                            shutil.rmtree(item)
                        else:
                            os.remove(item)
                else:
                    # Create target directory if it doesn't exist
                    target_path.mkdir(parents=True)
                
                # Copy backup contents to codebase directory
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
        
        # BROWSE BACKUP
        elif operation == "browse":
            backup_name = options.get("name")
            browse_path = options.get("path", "")
            
            if not backup_name:
                return {"error": "name is required for browse_backup operation"}
                
            backup_path = backup_root / backup_name
            
            # Validate backup exists
            if not backup_path.exists() or not backup_path.is_dir():
                return {
                    "error": f"Backup '{backup_name}' not found. Use codebase_browser operation='backup_list' to see available backups."
                }
            
            # Construct full browse path
            full_browse_path = backup_path
            if browse_path:
                full_browse_path = backup_path / browse_path
                
            if not full_browse_path.exists():
                return {"error": f"Path '{browse_path}' not found in backup '{backup_name}'"}
            
            if full_browse_path.is_file():
                # Read file content
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
                # List directory contents
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
    """
    Handle history operations.
    
    Returns:
        dict: History operation result.
    """
    try:
        history_file = get_history_file()
        
        # Read history
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


# Start the server when script is run directly
if __name__ == "__main__":
    try:
        print(f"MCP Codebase Browser running. Connect through Claude Desktop.")
        print(f"Serving codebase from: {CODEBASE_PATH}")
        mcp.run()
    except Exception as e:
        print(f"ERROR: {str(e)}", file=sys.stderr)
        traceback.print_exc(file=sys.stderr)
