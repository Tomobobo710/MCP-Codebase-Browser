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

# Auto-detect CODEBASE_PATH relative to script location
CODEBASE_PATH = None  # Automatically determined relative to script

def get_codebase_path():
    """Automatically determine the codebase path based on script location"""
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

@mcp.tool()
def codebase_browser(operation: str, path: str = None, options: dict = None):
    """
    All-in-one codebase browser tool
    
    Parameters:
    - operation: Operation to perform - one of:
      * File operations: "read", "write", "append", "delete", "move", "copy", "list", "mkdir", "rmdir"
      * Edit operations: "edit"
      * Search operations: "search"
      * Backup operations: "backup_create", "backup_list", "backup_restore"
    
    - path: File or directory path to operate on (not needed for some operations)
    
    - options: Additional options based on operation:
      * File operations:
        - write/append: {"content": "text to write"}
        - move/copy: {"destination": "new/path", "overwrite": bool}
        - rmdir: {"recursive": bool}
        - list: {"pattern": "**/*.js"} 
        - read: {"format": "text"/"lines", "start_line": int, "end_line": int}
      
      * Edit operations:
        - edit: {
            "operations": [
              {
                "mode": "replace",
                "find": "text to find",
                "replace": "replacement text",
                "occurrence": 1
              },
              ...
            ],
            "new_content": "alternative complete replacement for file"
          }
      
      * Search operations:
        - search: {
            "search_term": "text to search for",
            "file_pattern": "**/*.js", 
            "case_sensitive": bool,
            "include_block_content": bool,
            "max_results": int
          }
      
      * Backup operations:
        - backup_create: {"name": "optional_custom_name"}
        - backup_list: {}
        - backup_restore: {"name": "backup_name"}
    """
    options = options or {}
    
    # GROUP 1: FILE OPERATIONS
    if operation in ["read", "write", "append", "delete", "move", "copy", "list", "mkdir", "rmdir"]:
        return _handle_file_operations(operation, path, options)
    
    # GROUP 2: EDIT OPERATIONS
    elif operation == "edit":
        return _handle_edit_operations(path, options)
    
    # GROUP 3: SEARCH OPERATIONS
    elif operation == "search":
        return _handle_search_operations(options)
    
    # GROUP 4: BACKUP OPERATIONS
    elif operation in ["backup_create", "backup_list", "backup_restore"]:
        return _handle_backup_operations(operation.replace("backup_", ""), options)
    
    else:
        return {"error": f"Unknown operation: {operation}"}


def _handle_file_operations(operation, path, options):
    """Handle all file system operations"""
    if path is None:
        return {"error": "Path is required for file operations"}
        
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
            
            with open(full_path, 'r', encoding='utf-8', errors='replace') as f:
                content = f.read()
                
            if format == "lines":
                lines = content.splitlines(True)
                structured_lines = []
                
                # Handle line selection if specified
                if start_line is not None:
                    start_idx = max(0, start_line - 1)
                    end_idx = end_line if end_line is not None else start_idx + 1
                    lines = lines[start_idx:end_idx]
                
                for i, line in enumerate(lines):
                    line_number = start_line + i if start_line is not None else i + 1
                    structured_lines.append({
                        "lineNo": line_number,
                        "content": line
                    })
                    
                return {
                    "lines": structured_lines,
                    "count": len(structured_lines)
                }
            else:
                return {
                    "content": content,
                    "count": content.count('\n') + 1
                }
                
        # WRITE FILE
        elif operation == "write":
            content = options.get("content", "")
            full_path.parent.mkdir(parents=True, exist_ok=True)
            
            with open(full_path, 'w', encoding='utf-8') as f:
                f.write(content)
                
            return {"success": True}
            
        # APPEND TO FILE
        elif operation == "append":
            content = options.get("content", "")
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
                os.rmdir(full_path)  # Will only work if directory is empty
                
            return {"success": True}
            
        # MOVE FILE/DIRECTORY
        elif operation == "move":
            destination = options.get("destination")
            if not destination:
                return {"error": "Destination path is required"}
                
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
                return {"error": "Destination path is required"}
                
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
        return {"error": f"{str(e)}"}


def _handle_edit_operations(path, options):
    """Handle file editing operations"""
    if path is None:
        return {"error": "Path is required for edit operations"}
        
    full_path = Path(CODEBASE_PATH) / path
    operations = options.get("operations", [])
    new_content = options.get("new_content")
    
    try:
        # Handle full file replacement
        if new_content is not None:
            with open(full_path, 'w', encoding='utf-8') as f:
                f.write(new_content)
            return {"success": True}
            
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
            
        return {"success": True, "count": applied_operations}
            
    except Exception as e:
        return {"error": f"{str(e)}"}


def _handle_search_operations(options):
    """Handle code search operations with smart block detection"""
    search_term = options.get("search_term", "")
    file_pattern = options.get("file_pattern", "**/*")
    case_sensitive = options.get("case_sensitive", False)
    include_block_content = options.get("include_block_content", False)
    max_results = options.get("max_results", 100)
    max_display_results = options.get("max_display_results", 5)  # New parameter for display limit
    
    if not search_term:
        return {"error": "Search term is required"}
    
    results = []
    total_matches = 0
    files_checked = 0
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
                    
                    file_matches = []
                    
                    # Search each line
                    for i, line in enumerate(lines):
                        if (case_sensitive and search_term in line) or \
                           (not case_sensitive and search_term.lower() in line.lower()):
                            
                            # Always include the line info
                            match_info = {
                                "lineNumber": i + 1,
                                "content": line.rstrip('\r\n')
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
                            
                            # Only include the full block content if requested
                            if include_block_content:
                                block_lines = lines[start_idx:end_idx+1]
                                match_info["blockContent"] = "".join(l.rstrip('\r\n') + '\n' for l in block_lines)
                            
                            file_matches.append(match_info)
                            total_matches += 1
                            
                            if total_matches >= max_results:
                                break
                    
                    if file_matches:
                        results.append({
                            "file": rel_path,
                            "matches": file_matches,
                            "matchCount": len(file_matches)
                        })
                
                except Exception as e:
                    continue
        
        final_results = results
        truncated = False
        
        if len(results) > max_display_results:
            final_results = results[:max_display_results]
            truncated = True
        
        return {
            "results": final_results,
            "totalMatches": total_matches,
            "filesChecked": files_checked,
            "searchTerm": search_term,
            "truncated": truncated,
            "totalFiles": len(results),
            "displayedFiles": len(final_results),
            "message": f"Showing {len(final_results)} of {len(results)} files with matches" if truncated else None,
            "options": {
                "filePattern": file_pattern,
                "caseSensitive": case_sensitive,
                "includeBlockContent": include_block_content
            }
        }
        
    except Exception as e:
        return {"error": f"Error searching codebase: {str(e)}"}


def _handle_backup_operations(operation, options):
    """Handle backup operations"""
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
                return {"error": "Backup name is required for restore operation"}
                
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
        return {"error": f"Error during backup {operation}: {str(e)}"}


# Start the server when script is run directly
if __name__ == "__main__":
    try:
        print(f"MCP Codebase Browser running. Connect through Claude Desktop.")
        print(f"Serving codebase from: {CODEBASE_PATH}")
        mcp.run()
    except Exception as e:
        print(f"ERROR: {str(e)}", file=sys.stderr)
        traceback.print_exc(file=sys.stderr)