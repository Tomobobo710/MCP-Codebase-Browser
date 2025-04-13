from mcp.server.fastmcp import FastMCP
import os
import sys
import shutil
import re
from fnmatch import fnmatch
from pathlib import Path
import glob

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
def list_files(directory: str = "", pattern: str = "**/*"):
    """List files in a directory of the codebase"""
    dir_path = Path(CODEBASE_PATH) / directory
    
    try:
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
            "currentPath": directory
        }
    except Exception as e:
        return {"error": f"Error listing files: {str(e)}"}

@mcp.tool()
def read_file(file_path: str):
    """Read the contents of a file in the codebase"""
    full_path = Path(CODEBASE_PATH) / file_path
    
    try:
        if not full_path.exists():
            return {"error": "File not found"}
        
        # Check file size to avoid reading very large files
        file_size = full_path.stat().st_size
        if file_size > 1024 * 1024:  # 1MB limit
            return {
                "error": "File too large",
                "size": file_size,
                "sizeHuman": f"{file_size / 1024 / 1024:.2f}MB"
            }
        
        with open(full_path, 'r', encoding='utf-8', errors='replace') as f:
            content = f.read()
        
        return {
            "content": content,
            "filePath": file_path,
            "sizeBytes": file_size
        }
    except Exception as e:
        return {"error": f"Error reading file: {str(e)}"}

@mcp.tool()
def search_code(
    search_term: str, 
    file_pattern: str = "**/*",
    case_sensitive: bool = False,
    include_block_content: bool = False,
    max_results: int = 100
):
    """
    Search for text in code files with smart block detection
    
    Parameters:
    - search_term: Text to search for
    - file_pattern: File pattern to search (defaults to all files)
    - case_sensitive: Whether to perform case-sensitive matching
    - include_block_content: Whether to include the full text content of surrounding code blocks
    - max_results: Maximum number of matching lines to return
    """
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
        
        return {
            "results": results,
            "totalMatches": total_matches,
            "filesChecked": files_checked,
            "searchTerm": search_term,
            "options": {
                "caseSensitive": case_sensitive,
                "includeBlockContent": include_block_content
            }
        }
        
    except Exception as e:
        return {
            "error": f"Error searching codebase: {str(e)}"
        }

@mcp.tool()
def write_file(file_path: str, content: str, mode: str = "overwrite"):
    """
    Write content to a file in the codebase
    Mode can be 'overwrite' (replace entire file) or 'append' (add to end of file)
    """
    full_path = Path(CODEBASE_PATH) / file_path
    
    try:
        # Create parent directories if they don't exist
        full_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Write mode based on parameter
        write_mode = 'w' if mode == 'overwrite' else 'a'
        
        with open(full_path, write_mode, encoding='utf-8') as f:
            f.write(content)
        
        return {
            "success": True,
            "message": f"Successfully {'wrote to' if mode == 'overwrite' else 'appended to'} {file_path}",
            "filePath": file_path
        }
    except Exception as e:
        return {"error": f"Error writing to file: {str(e)}"}

@mcp.tool()
def delete_file(file_path: str):
    """Delete a file from the codebase"""
    full_path = Path(CODEBASE_PATH) / file_path
    
    try:
        if not full_path.exists():
            return {"error": "File not found"}
        
        if not full_path.is_file():
            return {"error": "Path is not a file"}
        
        os.remove(full_path)
        
        return {
            "success": True,
            "message": f"Successfully deleted {file_path}"
        }
    except Exception as e:
        return {"error": f"Error deleting file: {str(e)}"}

@mcp.tool()
def create_directory(dir_path: str):
    """Create a new directory in the codebase"""
    full_path = Path(CODEBASE_PATH) / dir_path
    
    try:
        full_path.mkdir(parents=True, exist_ok=True)
        
        return {
            "success": True,
            "message": f"Successfully created directory {dir_path}"
        }
    except Exception as e:
        return {"error": f"Error creating directory: {str(e)}"}

@mcp.tool()
def delete_directory(dir_path: str, recursive: bool = False):
    """
    Delete a directory from the codebase
    If recursive=False, will only delete if empty
    If recursive=True, will delete all contents too
    """
    full_path = Path(CODEBASE_PATH) / dir_path
    
    try:
        if not full_path.exists():
            return {"error": "Directory not found"}
        
        if not full_path.is_dir():
            return {"error": "Path is not a directory"}
        
        if recursive:
            shutil.rmtree(full_path)
        else:
            os.rmdir(full_path)  # Will only work if directory is empty
        
        return {
            "success": True,
            "message": f"Successfully deleted directory {dir_path}"
        }
    except OSError as e:
        if "Directory not empty" in str(e):
            return {"error": "Directory is not empty. Use recursive=True to delete non-empty directories."}
        else:
            return {"error": f"Error deleting directory: {str(e)}"}
    except Exception as e:
        return {"error": f"Error deleting directory: {str(e)}"}

@mcp.tool()
def move_file(source_path: str, destination_path: str, overwrite: bool = False):
    """
    Move or rename a file in the codebase
    Can also be used to move between directories
    """
    full_source = Path(CODEBASE_PATH) / source_path
    full_dest = Path(CODEBASE_PATH) / destination_path
    
    try:
        if not full_source.exists():
            return {"error": "Source file not found"}
        
        if full_dest.exists() and not overwrite:
            return {"error": "Destination file already exists. Set overwrite=True to replace it."}
        
        # Create parent directories if they don't exist
        full_dest.parent.mkdir(parents=True, exist_ok=True)
        
        shutil.move(str(full_source), str(full_dest))
        
        return {
            "success": True,
            "message": f"Successfully moved {source_path} to {destination_path}"
        }
    except Exception as e:
        return {"error": f"Error moving file: {str(e)}"}

@mcp.tool()
def copy_file(source_path: str, destination_path: str, overwrite: bool = False):
    """
    Copy a file in the codebase
    """
    full_source = Path(CODEBASE_PATH) / source_path
    full_dest = Path(CODEBASE_PATH) / destination_path
    
    try:
        if not full_source.exists():
            return {"error": "Source file not found"}
        
        if full_dest.exists() and not overwrite:
            return {"error": "Destination file already exists. Set overwrite=True to replace it."}
        
        # Create parent directories if they don't exist
        full_dest.parent.mkdir(parents=True, exist_ok=True)
        
        shutil.copy2(str(full_source), str(full_dest))
        
        return {
            "success": True,
            "message": f"Successfully copied {source_path} to {destination_path}"
        }
    except Exception as e:
        return {"error": f"Error copying file: {str(e)}"}

@mcp.tool()
def read_lines(file_path: str, start_line: int = None, end_line: int = None):
    """
    Read specific line(s) from a file
    
    Parameters:
    - file_path: Path to the file relative to the codebase
    - start_line: First line to read (1-indexed)
    - end_line: Last line to read (inclusive, 1-indexed)
    
    If start_line is None, returns the entire file
    If only start_line is specified, returns just that line
    If both are specified, returns that range of lines (inclusive)
    """
    full_path = Path(CODEBASE_PATH) / file_path
    
    try:
        if not full_path.exists():
            return {"error": "File not found"}
        
        with open(full_path, 'r', encoding='utf-8', errors='replace') as f:
            # If no line number is specified, return the whole file
            if start_line is None:
                content = f.read()
                return {
                    "content": content,
                    "lineCount": content.count('\n') + 1,
                    "type": "entire_file"
                }
            
            # Otherwise, read all lines and extract the requested ones
            lines = f.readlines()
            
            # Handle single line request
            if end_line is None:
                if start_line < 1 or start_line > len(lines):
                    return {"error": f"Line {start_line} is out of range (file has {len(lines)} lines)"}
                
                # Return just the requested line (adjust for 0-based indexing)
                return {
                    "content": lines[start_line - 1],
                    "lineNumber": start_line,
                    "type": "single_line"
                }
            
            # Handle line range request
            else:
                # Validate line numbers
                if start_line < 1:
                    start_line = 1
                if end_line > len(lines):
                    end_line = len(lines)
                if start_line > end_line:
                    return {"error": "Start line cannot be greater than end line"}
                
                # Extract the requested range (adjust for 0-based indexing)
                selected_lines = lines[start_line - 1:end_line]
                return {
                    "content": "".join(selected_lines),
                    "startLine": start_line,
                    "endLine": end_line,
                    "lineCount": len(selected_lines),
                    "type": "line_range"
                }
    except Exception as e:
        return {"error": f"Error reading lines: {str(e)}"}

@mcp.tool()
def edit_lines(file_path: str, start_line: int, end_line: int = None, new_content: str = None, mode: str = "replace"):
    """
    Edit line(s) in a file with several operation modes
    
    Parameters:
    - file_path: Path to the file relative to the codebase
    - start_line: First line to edit (1-indexed)
    - end_line: Last line to edit (inclusive, 1-indexed), only needed for replace/delete modes
    - new_content: New content to write (required for replace/insert modes)
    - mode: Operation mode - "replace", "insert", or "delete"
      - replace: Replace lines from start_line to end_line with new_content
      - insert: Insert new_content at start_line (end_line is ignored)
      - delete: Delete lines from start_line to end_line (new_content is ignored)
    """
    full_path = Path(CODEBASE_PATH) / file_path
    
    try:
        if not full_path.exists():
            return {"error": "File not found"}
        
        # Validate parameters based on mode
        if mode not in ["replace", "insert", "delete"]:
            return {"error": f"Invalid mode: {mode}. Must be 'replace', 'insert', or 'delete'"}
        
        if mode in ["replace", "insert"] and new_content is None:
            return {"error": f"New content must be provided for {mode} mode"}
        
        if mode in ["replace", "delete"] and end_line is None:
            end_line = start_line  # Default to single line operation
        
        # Read the file
        with open(full_path, 'r', encoding='utf-8', errors='replace') as f:
            lines = f.readlines()
        
        # Validate line numbers
        file_length = len(lines)
        if start_line < 1:
            start_line = 1
        
        # Adjust for 0-based indexing
        start_idx = start_line - 1
        
        # Perform the requested operation
        if mode == "replace":
            if end_line > file_length:
                end_line = file_length
            if start_line > end_line:
                return {"error": "Start line cannot be greater than end line"}
            
            end_idx = end_line - 1
            
            # Convert new_content to a list of lines with proper line endings
            if not new_content.endswith('\n'):
                new_content += '\n'
            new_lines = new_content.splitlines(True)
            
            # Replace the specified lines
            updated_lines = lines[:start_idx] + new_lines + lines[end_idx + 1:]
            
            operation_desc = f"Replaced lines {start_line}-{end_line}"
            
        elif mode == "insert":
            # Convert new_content to a list of lines with proper line endings
            if not new_content.endswith('\n'):
                new_content += '\n'
            new_lines = new_content.splitlines(True)
            
            # Handle insertion at the end of the file
            if start_idx > file_length:
                start_idx = file_length
            
            # Insert the new content
            updated_lines = lines[:start_idx] + new_lines + lines[start_idx:]
            
            operation_desc = f"Inserted at line {start_line}"
            
        elif mode == "delete":
            if end_line > file_length:
                end_line = file_length
            if start_line > end_line:
                return {"error": "Start line cannot be greater than end line"}
            
            end_idx = end_line - 1
            
            # Delete the specified lines
            updated_lines = lines[:start_idx] + lines[end_idx + 1:]
            
            operation_desc = f"Deleted lines {start_line}-{end_line}"
        
        # Write the updated content back to the file
        with open(full_path, 'w', encoding='utf-8') as f:
            f.writelines(updated_lines)
        
        return {
            "success": True,
            "message": f"{operation_desc} in {file_path}",
            "newLineCount": len(updated_lines)
        }
    except Exception as e:
        return {"error": f"Error editing lines: {str(e)}"}
        
@mcp.tool()
def backup_codebase(backup_name: str = None):
    """
    Create a backup of the entire codebase
    
    Parameters:
    - backup_name: Optional custom name for the backup (default: timestamp-based name)
    """
    try:
        # Determine backup directory path (one level above script directory)
        script_dir = Path(os.path.dirname(os.path.abspath(__file__)))
        backup_root = script_dir / "Backups"
        
        # Create Backups directory if it doesn't exist
        if not backup_root.exists():
            backup_root.mkdir(parents=True)
            print(f"Created Backups directory at: {backup_root}")
        
        # Generate default backup name if none provided
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
    except Exception as e:
        return {"error": f"Error creating backup: {str(e)}"}

@mcp.tool()
def list_backups():
    """List all available backups of the codebase"""
    try:
        # Determine backup directory path
        script_dir = Path(os.path.dirname(os.path.abspath(__file__)))
        backup_root = script_dir / "Backups"
        
        # Check if Backups directory exists
        if not backup_root.exists():
            return {
                "backups": [],
                "count": 0,
                "message": "No backups available yet. Use backup_codebase to create a backup."
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
    except Exception as e:
        return {"error": f"Error listing backups: {str(e)}"}

@mcp.tool()
def restore_codebase(backup_name: str, confirm: bool = False):
    """
    Restore the codebase from a backup
    
    Parameters:
    - backup_name: Name of the backup to restore from
    - confirm: Must be set to True to confirm the restoration (this will delete current codebase)
    """
    try:
        # Require explicit confirmation
        if not confirm:
            return {
                "success": False,
                "error": "Restoration requires confirmation. Set confirm=True to proceed. Warning: This will replace your current codebase."
            }
        
        # Determine backup directory path
        script_dir = Path(os.path.dirname(os.path.abspath(__file__)))
        backup_root = script_dir / "Backups"
        backup_path = backup_root / backup_name
        
        # Validate backup exists
        if not backup_path.exists() or not backup_path.is_dir():
            return {
                "success": False,
                "error": f"Backup '{backup_name}' not found. Use list_backups to see available backups."
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
    except Exception as e:
        return {"error": f"Error restoring backup: {str(e)}"}

# Start the server when script is run directly
if __name__ == "__main__":
    print(f"MCP Codebase Browser running. Connect through Claude Desktop.")
    print(f"Serving codebase from: {CODEBASE_PATH}")
    mcp.run()
