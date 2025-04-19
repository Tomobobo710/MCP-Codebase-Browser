from mcp.server.fastmcp import FastMCP
import os
import sys
import shutil
import re
from fnmatch import fnmatch
from pathlib import Path
import glob
import traceback
from diff_match_patch import diff_match_patch
import json

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

# Global in-memory chunk storage
_memory_chunks = {}

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
def codebase_browser(operation: str, path: str = None, options: dict = None):
    """
    All-in-one codebase browser tool for file management, editing, searching, and more.
    
    Parameters:
    - operation: (Required) Operation to perform, one of the following groups:
    
      1. FILE OPERATIONS: 
         - "read": Read file content (requires path)
         - "write": Write content to a file (requires path)
         - "append": Append content to a file (requires path)
         - "delete": Delete a file (requires path)
         - "move": Move a file or directory (requires path and destination)
         - "copy": Copy a file or directory (requires path and destination)
         - "list": List directory contents (requires path)
         - "mkdir": Create a directory (requires path)
         - "rmdir": Remove a directory (requires path)
      
      2. EDIT OPERATIONS:
         - "edit": Edit file content (requires path)
      
      3. SEARCH OPERATIONS:
         - "search": Search for content in files (requires search_term)
      
      4. BACKUP OPERATIONS:
         - "backup_create": Create a backup of the codebase (path not required)
         - "backup_list": List available backups (path not required)
         - "backup_restore": Restore from a backup (path not required, requires name)
      
      5. CHUNK OPERATIONS:
         - "chunk_create": Create an in-memory chunk (path not required)
         - "chunk_update": Update an in-memory chunk (path not required)
         - "chunk_list": List available chunks (path not required)
         - "chunk_merge": Merge chunks into a file (requires path)
         - "chunk_clear": Clear all chunks (path not required)
    
    - path: (Required for most operations) File or directory path to operate on
           Paths are relative to the codebase root directory
    
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
         - append: {
             "content": str (Required, text to append to the file)
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
             "operations": [ (Optional list of edit operations)
               {
                 "mode": str (Required, one of: "replace", "insert_after", "insert_before", "append", "prepend"),
                 "find": str (Required for replace/insert modes, text to find),
                 "replace": str (Required for replace mode, replacement text),
                 "content": str (Required for insert/append/prepend modes, content to insert),
                 "occurrence": int (Optional, which occurrence to modify, default: 1)
               },
               ...
             ],
             "new_content": str (Optional, complete replacement for file content. If provided, operations are ignored)
           }
      
      3. SEARCH OPERATIONS:
         - search: {
             "search_term": str (Required, text to search for),
             "file_pattern": str (Optional, glob pattern for filtering files, default: "**/*"),
             "case_sensitive": bool (Optional, whether search is case-sensitive, default: False),
             "max_results": int (Optional, maximum number of total matches to find, default: 100),
             "max_display_results": int (Optional, maximum number of code blocks to display, default: 5)
           }
      
      4. BACKUP OPERATIONS:
         - backup_create: {
             "name": str (Optional, custom name for the backup, default: timestamp-based name)
           }
         - backup_list: {} (No additional options required)
         - backup_restore: {
             "name": str (Required, name of the backup to restore)
           }
      
      5. CHUNK OPERATIONS:
         - chunk_create: {
             "chunk_name": str (Optional, name for the chunk, default: timestamp-based name),
             "content": str (Required, content for the chunk)
           }
         - chunk_update: {
             "chunk_name": str (Required, name of the chunk to update),
             "content": str (Required, new content for the chunk)
           }
         - chunk_list: {} (No additional options required)
         - chunk_merge: {
             "chunk_names": list[str] (Required, list of chunk names to merge),
             "mode": str (Optional, "create" or "append", default: "create")
           }
         - chunk_clear: {} (No additional options required)
    
    Returns:
        dict: Response varies by operation, but typically includes:
              - For successful operations: {"success": True, ...relevant data...}
              - For unsuccessful operations: {"error": "Error message"}
              - For read operations: {"content": str} or {"lines": list[dict]}
              - For list operations: {"files": list[str], "directories": list[str]}
              - For search operations: {"blocks": list[dict], "totalMatches": int, "filesWithMatches": int, ...}
              - For backup/chunk operations: Operation-specific status and data
    """
    options = options or {}
    
    # Track what operation is being performed for error messages
    result_metadata = {"operation_type": operation, "path": path}
    
    # GROUP 1: FILE OPERATIONS
    if operation in ["read", "write", "append", "delete", "move", "copy", "list", "mkdir", "rmdir"]:
        result = _handle_file_operations(operation, path, options)
        result.update(result_metadata)
        return check_result_size(result)
    
    # GROUP 2: EDIT OPERATIONS
    elif operation == "edit":
        result = _handle_edit_operations(path, options)
        result.update(result_metadata)
        return check_result_size(result)
    
    # GROUP 3: SEARCH OPERATIONS
    elif operation == "search":
        result = _handle_search_operations(options)
        result.update(result_metadata)
        return check_result_size(result)
    
    # GROUP 4: BACKUP OPERATIONS
    elif operation in ["backup_create", "backup_list", "backup_restore"]:
        result = _handle_backup_operations(operation.replace("backup_", ""), options)
        result.update(result_metadata)
        return check_result_size(result)
    
    # GROUP 5: CHUNK OPERATIONS
    elif operation in ["chunk_create", "chunk_update", "chunk_list", "chunk_merge", "chunk_clear"]:
        result = _handle_chunk_operations(operation.replace("chunk_", ""), options)
        result.update(result_metadata)
        return check_result_size(result)
    
    else:
        return {"error": f"Unknown operation: {operation}. See documentation for valid operations."}


def _handle_chunk_operations(operation, options):
    """
    Handle chunk-based file writing operations with in-memory storage.
    
    Args:
        operation (str): The chunk operation to perform.
        options (dict): Additional options for the operation.
        
    Returns:
        dict: Operation result.
    """
    global _memory_chunks
    
    # Create backup directory for archival purposes
    script_dir = Path(os.path.dirname(os.path.abspath(__file__)))
    chunks_dir = script_dir / "Backups" / "Chunks"
    if not chunks_dir.exists():
        chunks_dir.mkdir(parents=True, exist_ok=True)
    
    try:
        # Get current timestamp for file naming
        from datetime import datetime
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        if operation == "create":
            # Create a new chunk with specified content
            chunk_name = options.get("chunk_name")
            content = options.get("content")
            
            if content is None:
                return {"error": "content is required for chunk_create operation"}
            
            if not chunk_name:
                # Generate a name if none provided
                chunk_name = f"chunk_{timestamp}"
            
            # Store in memory
            _memory_chunks[chunk_name] = content
            
            # Create a timestamped backup filename
            backup_filename = f"{chunk_name}_{timestamp}.txt"
            chunk_path = chunks_dir / backup_filename
            
            # Save to disk as backup
            with open(chunk_path, 'w', encoding='utf-8') as f:
                f.write(content)
                
            return {
                "success": True,
                "chunk_name": chunk_name,
                "backup_file": backup_filename,
                "message": f"Chunk created and stored in memory (backup saved as {backup_filename})"
            }
        
        elif operation == "update":
            # Update an existing chunk
            chunk_name = options.get("chunk_name")
            content = options.get("content")
            
            if not chunk_name:
                return {"error": "chunk_name is required for chunk_update operation"}
            
            if content is None:
                return {"error": "content is required for chunk_update operation"}
            
            if chunk_name not in _memory_chunks:
                return {"error": f"Chunk '{chunk_name}' not found in memory"}
            
            # Update in memory
            _memory_chunks[chunk_name] = content
            
            # Create a timestamped backup filename for the update
            backup_filename = f"{chunk_name}_{timestamp}_updated.txt"
            chunk_path = chunks_dir / backup_filename
            
            # Save to disk as backup
            with open(chunk_path, 'w', encoding='utf-8') as f:
                f.write(content)
                
            return {
                "success": True,
                "backup_file": backup_filename,
                "message": f"Chunk '{chunk_name}' updated in memory (backup saved as {backup_filename})"
            }
        
        elif operation == "list":
            # List all available chunks from memory
            return {
                "chunks": list(_memory_chunks.keys()),
                "count": len(_memory_chunks)
            }
        
        elif operation == "merge":
            # Merge specified chunks into a file
            target_path = options.get("path")
            chunk_names = options.get("chunk_names", [])
            merge_mode = options.get("mode", "create")  # create, append
            
            if not target_path:
                return {"error": "path is required for chunk_merge operation"}
                
            if not chunk_names:
                return {"error": "chunk_names list is required for chunk_merge operation"}
            
            # Validate all chunks exist in memory
            missing_chunks = [name for name in chunk_names if name not in _memory_chunks]
            
            if missing_chunks:
                return {"error": f"Chunks not found in memory: {', '.join(missing_chunks)}"}
            
            # Determine output file path
            full_path = Path(CODEBASE_PATH) / target_path
            full_path.parent.mkdir(parents=True, exist_ok=True)
            
            # Merge the chunks from memory
            mode = 'w' if merge_mode == 'create' else 'a'
            with open(full_path, mode, encoding='utf-8') as outfile:
                for name in chunk_names:
                    outfile.write(_memory_chunks[name])
            
            # Also create a backup of the merged content
            merged_content = "".join(_memory_chunks[name] for name in chunk_names)
            backup_filename = f"merged_{Path(target_path).stem}_{timestamp}.txt"
            backup_path = chunks_dir / backup_filename
            
            with open(backup_path, 'w', encoding='utf-8') as f:
                f.write(merged_content)
            
            return {
                "success": True,
                "message": f"Merged {len(chunk_names)} chunks into {target_path}",
                "path": target_path,
                "chunks_used": chunk_names,
                "backup_file": backup_filename
            }
        
        elif operation == "clear":
            # Clear all chunks from memory
            chunk_count = len(_memory_chunks)
            _memory_chunks.clear()
            
            return {
                "success": True,
                "message": f"Cleared {chunk_count} chunks from memory"
            }
        
        else:
            return {"error": f"Unknown chunk operation: {operation}"}
            
    except Exception as e:
        return {"error": f"Error during chunk_{operation}: {str(e)}"}


def _handle_file_operations(operation, path, options):
    """
    Handle all file system operations.
    
    Args:
        operation (str): The file operation to perform.
        path (str): File or directory path to operate on.
        options (dict): Additional options for the operation.
        
    Returns:
        dict: Operation result.
    """
    if path is None and operation not in ["backup_create", "backup_list", "backup_restore"]:
        return {"error": "Path is required for file operations"}
        
    if path:
        full_path = Path(CODEBASE_PATH) / path
    
    try:
        # LIST DIRECTORY
        if operation == "list":
            pattern = options.get("pattern", "**/*")
            dir_path = full_path
            
            if not dir_path.exists():
                return {"error": "Directory not found"}
            
            # Get files matching pattern
            files = [str(Path(f).relative_to(dir_path)) 
                    for f in glob.glob(str(dir_path / pattern), recursive=True) 
                    if os.path.isfile(f)]
            
            # Get directories
            dirs = [d.name + '/' for d in os.scandir(str(dir_path)) if d.is_dir()]
            
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
                
            full_path.parent.mkdir(parents=True, exist_ok=True)
            
            with open(full_path, 'w', encoding='utf-8') as f:
                f.write(content)
                
            return {"success": True}
            
        # APPEND TO FILE
        elif operation == "append":
            content = options.get("content")
            if content is None:
                return {"error": "content is required for append operation"}
                
            full_path.parent.mkdir(parents=True, exist_ok=True)
            
            with open(full_path, 'a', encoding='utf-8') as f:
                f.write(content)
                
            return {"success": True}
            
        # DELETE FILE
        elif operation == "delete":
            if not full_path.exists():
                return {"error": "File not found"}
                
            if full_path.is_file():
                os.remove(full_path)
                return {"success": True}
            else:
                return {"error": "Path is not a file"}
                
        # MAKE DIRECTORY
        elif operation == "mkdir":
            full_path.mkdir(parents=True, exist_ok=True)
            return {"success": True}
            
        # REMOVE DIRECTORY
        elif operation == "rmdir":
            if not full_path.exists():
                return {"error": "Directory not found"}
                
            if not full_path.is_dir():
                return {"error": "Path is not a directory"}
                
            recursive = options.get("recursive", False)
            
            if recursive:
                shutil.rmtree(full_path)
            else:
                try:
                    os.rmdir(full_path)  # Will only work if directory is empty
                except OSError as e:
                    return {"error": "Directory is not empty. Use recursive=True to remove non-empty directories."}
                
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
                
            dest_path.parent.mkdir(parents=True, exist_ok=True)
            
            shutil.move(str(full_path), str(dest_path))
            
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
            
            if full_path.is_dir():
                shutil.copytree(str(full_path), str(dest_path))
            else:
                shutil.copy2(str(full_path), str(dest_path))
            
            return {"success": True}
        
    except Exception as e:
        return {"error": f"Error during file operation: {str(e)}"}


def _handle_edit_operations(path, options):
    """
    Handle file editing operations.
    
    Args:
        path (str): Path to the file to edit.
        options (dict): Edit options including operations or new_content.
        
    Returns:
        dict: Edit operation result.
    """
    if path is None:
        return {"error": "Path is required for edit operations"}
        
    full_path = Path(CODEBASE_PATH) / path
    operations = options.get("operations", [])
    new_content = options.get("new_content")
    
    try:
        # Handle full file replacement
        if new_content is not None:
            # Create parent directories if they don't exist
            full_path.parent.mkdir(parents=True, exist_ok=True)
            
            with open(full_path, 'w', encoding='utf-8') as f:
                f.write(new_content)
            return {"success": True, "message": "File content replaced"}
            
        # Check if file exists
        if not full_path.exists():
            return {"error": "File not found"}
            
        # Read original content
        with open(full_path, 'r', encoding='utf-8', errors='replace') as f:
            content = f.read()
            
        # Create diff_match_patch instance for efficient patching
        dmp = diff_match_patch()
        modified_content = content
        applied_operations = 0
        
        # Apply each operation
        for op in operations:
            mode = op.get("mode", "")
            
            if mode == "replace" and "find" in op and "replace" in op:
                find_text = op["find"]
                replace_text = op["replace"]
                occurrence = op.get("occurrence", 1)
                
                # Find the specified occurrence
                start_pos = -1
                for i in range(occurrence):
                    start_pos = modified_content.find(find_text, start_pos + 1)
                    if start_pos == -1:
                        break
                
                if start_pos != -1:
                    # Create patches for this edit
                    new_content = (
                        modified_content[:start_pos] + 
                        replace_text + 
                        modified_content[start_pos + len(find_text):]
                    )
                    patches = dmp.patch_make(modified_content, new_content)
                    modified_content, _ = dmp.patch_apply(patches, modified_content)
                    applied_operations += 1
                    
            elif mode == "insert_after" and "find" in op and "content" in op:
                find_text = op["find"]
                insert_content = op["content"]
                occurrence = op.get("occurrence", 1)
                
                # Find the specified occurrence
                start_pos = -1
                for i in range(occurrence):
                    start_pos = modified_content.find(find_text, start_pos + 1)
                    if start_pos == -1:
                        break
                
                if start_pos != -1:
                    # Create patches for this edit
                    insert_pos = start_pos + len(find_text)
                    new_content = (
                        modified_content[:insert_pos] + 
                        insert_content + 
                        modified_content[insert_pos:]
                    )
                    patches = dmp.patch_make(modified_content, new_content)
                    modified_content, _ = dmp.patch_apply(patches, modified_content)
                    applied_operations += 1
                    
            elif mode == "insert_before" and "find" in op and "content" in op:
                find_text = op["find"]
                insert_content = op["content"]
                occurrence = op.get("occurrence", 1)
                
                # Find the specified occurrence
                start_pos = -1
                for i in range(occurrence):
                    start_pos = modified_content.find(find_text, start_pos + 1)
                    if start_pos == -1:
                        break
                
                if start_pos != -1:
                    # Create patches for this edit
                    new_content = (
                        modified_content[:start_pos] + 
                        insert_content + 
                        modified_content[start_pos:]
                    )
                    patches = dmp.patch_make(modified_content, new_content)
                    modified_content, _ = dmp.patch_apply(patches, modified_content)
                    applied_operations += 1
                    
            elif mode == "append" and "content" in op:
                append_content = op["content"]
                
                # Add a newline if the file doesn't end with one
                if modified_content and not modified_content.endswith('\n'):
                    append_content = '\n' + append_content
                    
                # Create patches for this edit
                new_content = modified_content + append_content
                patches = dmp.patch_make(modified_content, new_content)
                modified_content, _ = dmp.patch_apply(patches, modified_content)
                applied_operations += 1
                
            elif mode == "prepend" and "content" in op:
                prepend_content = op["content"]
                
                # Add a newline if the content doesn't end with one
                if prepend_content and not prepend_content.endswith('\n'):
                    prepend_content = prepend_content + '\n'
                    
                # Create patches for this edit
                new_content = prepend_content + modified_content
                patches = dmp.patch_make(modified_content, new_content)
                modified_content, _ = dmp.patch_apply(patches, modified_content)
                applied_operations += 1
        
        # Write the modified content back to the file
        with open(full_path, 'w', encoding='utf-8') as f:
            f.write(modified_content)
            
        return {"success": True, "operations_applied": applied_operations}
            
    except Exception as e:
        return {"error": f"Error during edit operation: {str(e)}"}


def _handle_search_operations(options):
    """
    Handle code search operations with smart block detection.
    
    Args:
        options (dict): Search parameters.
        
    Returns:
        dict: Search results - showing exactly 5 individual code blocks as results.
    """
    search_term = options.get("search_term", "")
    file_pattern = options.get("file_pattern", "**/*")
    case_sensitive = options.get("case_sensitive", False)
    include_block_content = options.get("include_block_content", True)  # Always include block content
    max_results = options.get("max_results", 100)  # Still collect up to 100 for total count
    max_display_blocks = options.get("max_display_results", 5)  # Show 5 individual blocks max
    
    if not search_term:
        return {"error": "search_term is required for search operation"}
    
    all_blocks = []  # Flat list of all code blocks found
    total_matches = 0
    files_checked = 0
    files_with_matches = 0
    base_path = Path(CODEBASE_PATH)
    
    def detect_language(filename):
        """Determine if a file uses braces or indentation for blocks"""
        ext = os.path.splitext(filename.lower())[1]
        
        # Python and YAML use indentation
        if ext in ['.py', '.pyx', '.pyw', '.yml', '.yaml']:
            return 'indentation'
        
        # Most other languages use braces
        elif ext in ['.js', '.ts', '.jsx', '.tsx', '.java', '.c', '.cpp', '.cs', '.go', '.php', '.swift', '.kt', '.rs']:
            return 'braces'
            
        # Default to braces for unknown types
        else:
            return 'braces'
    
    def find_brace_block(lines, match_line_index):
        """Find the boundaries of a code block using braces"""
        # Default to showing just a few lines around the match if no block found
        start_line = max(0, match_line_index - 3)
        end_line = min(len(lines) - 1, match_line_index + 3)
        
        # Track brace nesting
        open_braces = 0
        close_braces = 0
        found_opening = False
        
        # First, check the line itself and count braces
        current_line = lines[match_line_index]
        open_count_current = current_line.count('{')
        close_count_current = current_line.count('}')
        
        # Search backwards for opening brace or function/class definition
        for i in range(match_line_index, -1, -1):
            line = lines[i]
            open_count = line.count('{')
            close_count = line.count('}')
            
            open_braces += open_count
            close_braces += close_count
            
            # Check for function/method definition or class definition
            if 'function ' in line or 'class ' in line or 'def ' in line or '= function' in line:
                start_line = i
                found_opening = True
                break
                
            if open_braces > close_braces:
                start_line = i
                found_opening = True
                break
        
        # Reset counters but account for braces on the current line
        open_braces = open_count_current
        close_braces = close_count_current
        
        # Only search for closing brace if we found an opening brace
        if found_opening:
            # Search forwards for closing brace
            for i in range(match_line_index + 1, len(lines)):
                line = lines[i]
                open_count = line.count('{')
                close_count = line.count('}')
                
                open_braces += open_count
                close_braces += close_count
                
                if close_braces > open_braces:
                    end_line = i
                    break
        
        return start_line, end_line
    
    def find_indentation_block(lines, match_line_index):
        """Find the boundaries of a code block using indentation (Python-style)"""
        # Default to showing just a few lines around the match
        start_line = max(0, match_line_index - 3)
        end_line = min(len(lines) - 1, match_line_index + 3)
        
        # Get the indentation of the matched line
        match_line = lines[match_line_index]
        match_indent = len(match_line) - len(match_line.lstrip())
        
        # Find the start of the block (line ending with : with less indentation)
        for i in range(match_line_index, -1, -1):
            line = lines[i]
            if not line.strip():  # Skip empty lines
                continue
                
            indent = len(line) - len(line.lstrip())
            
            # If we find a line with less indentation and ending with :, it's likely the start of our block
            if indent < match_indent and line.rstrip().endswith(':'):
                start_line = i
                block_indent = indent
                break
                
            # If we find a line with significantly less indentation, it could be a parent block
            if indent < match_indent and i > 0:
                # Check if there's a block start nearby
                for j in range(i, max(0, i-5), -1):
                    prev = lines[j]
                    if prev.rstrip().endswith(':'):
                        start_line = j
                        block_indent = len(prev) - len(prev.lstrip())
                        break
                break
        
        # Find the end of the block (first line with same or less indentation as block start)
        block_indent = len(lines[start_line]) - len(lines[start_line].lstrip())
        
        for i in range(match_line_index + 1, len(lines)):
            line = lines[i]
            if not line.strip():  # Skip empty lines
                continue
                
            indent = len(line) - len(line.lstrip())
            
            # If we find a line with same or less indentation than the block start, it's the end
            if indent <= block_indent:
                end_line = i - 1  # The line before this one was the last in the block
                break
        
        return start_line, end_line
    
    try:
        # Find all files recursively
        for root, _, files in os.walk(base_path):
            for filename in files:
                if total_matches >= max_results:
                    break
                    
                full_path = os.path.join(root, filename)
                rel_path = os.path.relpath(full_path, base_path)
                
                # Check if file matches pattern
                if not fnmatch(rel_path, file_pattern):
                    continue
                
                files_checked += 1
                
                try:
                    # Skip very large files
                    if os.path.getsize(full_path) > 10 * 1024 * 1024:  # 10MB
                        continue
                        
                    # Determine language type for block detection
                    lang_type = detect_language(filename)
                    
                    # Read the file line by line
                    with open(full_path, 'r', encoding='utf-8', errors='replace') as f:
                        lines = f.readlines()
                    
                    file_has_matches = False
                    
                    # Search each line
                    for i, line in enumerate(lines):
                        if (case_sensitive and search_term in line) or \
                           (not case_sensitive and search_term.lower() in line.lower()):
                            
                            file_has_matches = True
                            
                            # Always include the line info
                            match_info = {
                                "lineNumber": i + 1,
                                "matchLine": line.rstrip('\r\n'),
                                "file": rel_path,
                                "matchPosition": line.lower().find(search_term.lower()) if not case_sensitive else line.find(search_term)
                            }
                            
                            # Always include block boundaries
                            if lang_type == 'indentation':
                                start_idx, end_idx = find_indentation_block(lines, i)
                            else:
                                start_idx, end_idx = find_brace_block(lines, i)
                            
                            match_info["blockStart"] = start_idx + 1  # 1-indexed
                            match_info["blockEnd"] = end_idx + 1      # 1-indexed
                            match_info["language"] = lang_type
                            match_info["blockLines"] = end_idx - start_idx + 1
                            
                            # Always include the block content
                            block_lines = lines[start_idx:end_idx+1]
                            block_content = "".join(l.rstrip('\r\n') + '\n' for l in block_lines)
                            
                            # Check if block content is too large
                            if len(block_content) > MAX_RESULT_SIZE / 10:
                                # Only show a snippet with an ellipsis
                                snippet_size = 500
                                match_info["blockContent"] = (
                                    block_content[:snippet_size] + 
                                    f"\n... (block truncated, {len(block_content)} characters total) ...\n"
                                )
                                match_info["truncated"] = True
                            else:
                                match_info["blockContent"] = block_content
                            
                            # Add to our flat list of all blocks
                            all_blocks.append(match_info)
                            total_matches += 1
                            
                            if total_matches >= max_results:
                                break
                    
                    if file_has_matches:
                        files_with_matches += 1
                
                except Exception as e:
                    continue
        
        # Select the top N blocks to display
        displayed_blocks = all_blocks[:max_display_blocks]
        truncated = len(all_blocks) > max_display_blocks
        
        return {
            "blocks": displayed_blocks,
            "totalMatches": total_matches,
            "displayedMatches": len(displayed_blocks),
            "filesWithMatches": files_with_matches,
            "filesChecked": files_checked,
            "searchTerm": search_term,
            "truncated": truncated,
            "message": f"Found {total_matches} matches in {files_with_matches} files. Showing {len(displayed_blocks)} blocks." if truncated else None,
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
        operation (str): Backup operation to perform (create, list, restore).
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
                        from datetime import datetime
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
            if backup_name is None:
                from datetime import datetime
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                backup_name = f"backup_{timestamp}"
            else:
                # Sanitize the backup name to ensure it's a valid directory name
                backup_name = re.sub(r'[^\w\-\.]', '_', backup_name)
            
            # Create full backup path
            backup_path = backup_root / backup_name
            
            # Check if backup with this name already exists
            if backup_path.exists():
                return {
                    "success": False,
                    "error": f"Backup with name '{backup_name}' already exists. Choose a different name."
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
            
            return {
                "success": True,
                "message": f"Successfully restored codebase from backup '{backup_name}'",
                "backup_name": backup_name
            }
            
        else:
            return {"error": f"Unknown backup operation: {operation}"}
            
    except Exception as e:
        return {"error": f"Error during backup_{operation}: {str(e)}"}


# Start the server when script is run directly
if __name__ == "__main__":
    try:
        print(f"MCP Codebase Browser running. Connect through Claude Desktop.")
        print(f"Serving codebase from: {CODEBASE_PATH}")
        mcp.run()
    except Exception as e:
        print(f"ERROR: {str(e)}", file=sys.stderr)
        traceback.print_exc(file=sys.stderr)