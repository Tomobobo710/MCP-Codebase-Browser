# MCP Codebase Browser
A Python-based Model Context Protocol (MCP) server that gives Claude full access to your codebase for file management, code editing, searching, and direct shell command execution.

This server was created with assistance from Claude and prioritizes simplicity and compatibility with Claude's natural working style.

![MCP Server](https://github.com/user-attachments/assets/e9b6d97d-e3d4-4f8f-9038-fa4224531e9d)

## Overview

The Codebase Browser is a lightweight MCP tool that combines file operations, code editing, search, backups, and **CLI command execution** into a single unified interface. It works with both Claude Desktop (via stdio) and browser-based Claude (via SSE/HTTP).

**Key Features:**
* File operations (read, write, delete, move, copy, mkdir, rmdir)
* Code editing with find/replace operations
* Full-text search across your codebase
* Automatic backups and restoration
* **Shell command execution with commit tracking** (new)
* Automatic operation history and commit tracking
* Two deployment modes: Claude Desktop (stdio) and Web/Browser (SSE)

## Requirements

### Core
* Python 3.8 or higher
* Claude Desktop app OR browser-based Claude with MCP support

### OS Support
* Windows, macOS, Linux
* Shell: cmd, PowerShell, bash, zsh (auto-detected)

## Installation

### Quick Install (Claude Desktop)

Run `setup.bat` (Windows) or the equivalent shell script to automatically:
* Create a Python virtual environment
* Install required dependencies
* Set up a Project directory
* Detect your OS and available shells
* Generate CLI configuration
* Display Claude Desktop configuration instructions

### Manual Installation

**Create virtual environment:**
```bash
python -m venv mcp_env
source mcp_env/bin/activate  # On Windows: mcp_env\Scripts\activate
```

**Install dependencies:**
```bash
pip install mcp
```

**Create Project directory:**
```bash
mkdir Project
```

**Configure Claude Desktop:**
Open `claude_desktop_config.json` and add:
```json
{
  "mcpServers": {
    "MCP_Codebase_Browser": {
      "command": "/path/to/your/mcp_env/bin/python",
      "args": ["/path/to/your/codebase_server.py"]
    }
  }
}
```

## Usage

### With Claude Desktop
1. Complete setup above
2. Place your codebase in the `Project` directory
3. Restart Claude Desktop
4. Look for the hammer icon in the chat input box
5. Claude can now manage your codebase

### File Operations Examples
* "List all files in the project"
* "Read the content of src/main.py"
* "Create a new file called utils.js"
* "Search for all uses of 'import' in the codebase"
* "Edit this function and add error handling"
* "Create a backup of my project"
* "Restore from the backup named 'my_project_backup'"

### CLI Command Examples (NEW)
* "Run `npm install` to set up dependencies"
* "Execute the test suite with `pytest`"
* "Compile the code using `gcc`"
* "Check the git status"
* "Build the project with `cargo build`"

When you ask Claude to run a command, he provides a message describing what he's doing, and the command is tracked in your operation history.

## Deployment Modes

### 1. Claude Desktop (stdio)
**Best for:** Local development with Claude Desktop app

- Direct connection via stdio
- Automatic shell detection
- No network exposure
- Simplest setup

**Use:** Follow the installation steps above

### 2. Web/Browser (SSE)
**Best for:** Browser-based Claude, remote access, multi-user scenarios

- HTTP/SSE protocol
- Can be tunneled for remote access
- Requires .env configuration
- Optional SSL/TLS support

**Setup:**
```bash
python codebase_server_sse.py
```
Then configure via `.env` (copy from `.env.example`)

## Configuration

### CLI Configuration (Auto-generated)
When you run `setup.bat`, a `cli_config.json` is created that tells Claude:
- Your OS type
- Available shells (cmd, PowerShell, bash, zsh, etc.)
- How to invoke commands

### SSE Configuration (.env)
For the SSE version, create a `.env` file from `.env.example`:
```bash
cp .env.example .env
# Edit .env with your settings
```

**Important:** Never commit `.env` to version control (it's in `.gitignore`)

## Safety & Best Practices

### File Size Limits
* Large files are read/returned with line number filtering to prevent context overflow
* Files over 10MB are skipped during search operations
* Result sizes are capped at ~99KB to maintain response efficiency

### Commit Tracking
* Every operation (file writes, edits, deletes, CLI commands) is logged with intent
* View operation history with: "Show me recent commits"
* Use backups before major operations

### Backups
* Create backups: "Backup my codebase named 'v1.0'"
* List backups: "Show me my backups"
* Restore: "Restore from backup named 'v1.0'"

# ⚠️ WARNING

This tool allows Claude to make changes to your files. He will probably break things.

![Uh oh](https://github.com/user-attachments/assets/8064f185-4fdd-43fd-9705-9ce27db07e43)

This is a powerful tool. **Always ask Claude to create backups before major changes.** The author takes no responsibility for data loss.

## Troubleshooting

* **Claude doesn't show the hammer icon:** Restart Claude Desktop and check that `claude_desktop_config.json` has correct paths
* **Command execution fails:** Check that your shell is in the detected shells (check `cli_config.json`)
* **Logs:** Check Claude Desktop logs at `%AppData%\Claude\logs\mcp*.log` (Windows) or `~/.claude/logs/` (macOS/Linux)
* **Path issues:** Ensure paths use forward slashes on macOS/Linux, backslashes on Windows
* **SSL errors (SSE):** Verify certificate paths in `.env` are correct

## Notes

* **Single unified tool:** Everything is one tool to minimize permission prompts
* **No artificial restrictions:** Claude works intuitively with the tool rather than against engineered limitations
* **Language agnostic:** Works with any programming language (JavaScript, Python, Java, Rust, Go, etc.)
* **Context efficiency:** File operations intelligently handle size to prevent context bloat
* **Operation history:** Every change is tracked for accountability and debugging

## Design Philosophy

This tool embraces Claude's strengths rather than fighting his weaknesses. 

Other MCP tools try to "teach" Claude through restrictive error messages or puzzles. In practice, Claude doesn't learn well from tool constraints—he just moves on to a different approach. Instead, this tool works *with* Claude's actual behavior:

- **Code awareness:** Claude maintains an excellent mental model of your code. The tool leverages this by accepting his descriptions of changes ("find X, replace with Y") rather than forcing line numbers.
- **Intent clarity:** Every operation requires a message describing intent. This makes changes auditable and helps Claude stay focused.
- **Simplicity:** No artificial barriers, just direct file access and command execution.
- **History:** Full commit tracking so you can understand what happened and why.

The result: minimal tool use failures and maximum productivity.

## License

MIT License - See LICENSE file for details
