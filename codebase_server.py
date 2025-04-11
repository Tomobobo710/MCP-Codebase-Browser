from mcp.server.fastmcp import FastMCP
import os
import sys
import shutil
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
def search_code(search_term: str, file_pattern: str = "**/*.{py,js,ts,jsx,tsx,java,c,cpp,h,hpp,go,rs,rb}", max_results: int = 20):
    """Search for specific patterns in the codebase"""
    try:
        results = []
        base_path = Path(CODEBASE_PATH)
        
        # Expand the file pattern to include all matching files
        file_patterns = [p.strip() for p in file_pattern.split(',')]
        all_files = []
        for pattern in file_patterns:
            matches = glob.glob(str(base_path / pattern), recursive=True)
            all_files.extend([f for f in matches if os.path.isfile(f)])
        
        for full_path in all_files:
            if len(results) >= max_results:
                break
                
            try:
                file_size = os.path.getsize(full_path)
                if file_size > 1024 * 1024:  # Skip large files
                    continue
                
                rel_path = os.path.relpath(full_path, CODEBASE_PATH)
                
                with open(full_path, 'r', encoding='utf-8', errors='replace') as f:
                    lines = f.readlines()
                
                matching_lines = []
                for i, line in enumerate(lines):
                    if search_term in line:
                        matching_lines.append({
                            "lineNumber": i + 1,
                            "content": line.strip()
                        })
                
                if matching_lines:
                    results.append({
                        "file": rel_path,
                        "matches": matching_lines
                    })
            except Exception as e:
                print(f"Error processing file {full_path}: {str(e)}")
        
        return {
            "results": results,
            "totalMatches": sum(len(file_result["matches"]) for file_result in results),
            "searchTerm": search_term
        }
    except Exception as e:
        return {"error": f"Error searching codebase: {str(e)}"}

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

@mcp.resource("project://overview")
def project_overview():
    """Get an overview of the project structure and key files"""
    try:
        base_path = Path(CODEBASE_PATH)
        
        # Look for README files
        readme_content = ""
        readme_paths = list(base_path.glob("README*"))
        if readme_paths:
            with open(readme_paths[0], 'r', encoding='utf-8', errors='replace') as f:
                readme_content = f.read()
        
        # Look for package info files (package.json, pyproject.toml, etc.)
        package_info = {}
        package_json_path = base_path / "package.json"
        pyproject_path = base_path / "pyproject.toml"
        setup_py_path = base_path / "setup.py"
        
        if package_json_path.exists():
            import json
            with open(package_json_path, 'r') as f:
                package_info = json.load(f)
        elif pyproject_path.exists():
            # Just note it exists, we won't parse TOML format here
            package_info = {"name": "Python project with pyproject.toml"}
        elif setup_py_path.exists():
            package_info = {"name": "Python project with setup.py"}
        
        # Count files by extension
        all_files = list(base_path.glob("**/*"))
        all_files = [f for f in all_files if f.is_file()]
        
        file_types = {}
        for file_path in all_files:
            ext = file_path.suffix.lower()
            file_types[ext] = file_types.get(ext, 0) + 1
        
        # Get top-level directories
        top_level_dirs = [d.name for d in base_path.iterdir() if d.is_dir()]
        
        return {
            "projectName": package_info.get("name", base_path.name),
            "description": package_info.get("description", "No description available"),
            "readme": readme_content,
            "fileTypes": file_types,
            "topLevelDirs": top_level_dirs
        }
    except Exception as e:
        return {"error": f"Error generating project overview: {str(e)}"}

# Start the server when script is run directly
if __name__ == "__main__":
    print(f"MCP Codebase Browser running. Connect through Claude Desktop.")
    print(f"Serving codebase from: {CODEBASE_PATH}")
    mcp.run()
