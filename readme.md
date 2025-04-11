# MCP Codebase Browser
A Python-based Model Context Protocol (MCP) server that gives Claude full access to your codebase, allowing it to read, write, create, delete, and manage files and directories. This server was created with assistance from Claude 3.7 Sonnet.  
![MCP Server](https://private-user-images.githubusercontent.com/64335998/432573576-562915ad-c4d4-4855-9228-5a8c2834f608.png?jwt=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJnaXRodWIuY29tIiwiYXVkIjoicmF3LmdpdGh1YnVzZXJjb250ZW50LmNvbSIsImtleSI6ImtleTUiLCJleHAiOjE3NDQzMzgxNDIsIm5iZiI6MTc0NDMzNzg0MiwicGF0aCI6Ii82NDMzNTk5OC80MzI1NzM1NzYtNTYyOTE1YWQtYzRkNC00ODU1LTkyMjgtNWE4YzI4MzRmNjA4LnBuZz9YLUFtei1BbGdvcml0aG09QVdTNC1ITUFDLVNIQTI1NiZYLUFtei1DcmVkZW50aWFsPUFLSUFWQ09EWUxTQTUzUFFLNFpBJTJGMjAyNTA0MTElMkZ1cy1lYXN0LTElMkZzMyUyRmF3czRfcmVxdWVzdCZYLUFtei1EYXRlPTIwMjUwNDExVDAyMTcyMlomWC1BbXotRXhwaXJlcz0zMDAmWC1BbXotU2lnbmF0dXJlPTRkNzY3ZTkyOTZjMzU4OWMwMzExYTRlMjllYzUwNjUzOTg4MGRlNjMwNjEyNDBiNDU0N2I5N2FlZjFmMTIxMWImWC1BbXotU2lnbmVkSGVhZGVycz1ob3N0In0.sqTQO4Phm3T5vx1-q9IQmx_Yd_5Sfg_tNWoRTLHYpg4)
## Features
* File Browsing: List files and directories in your codebase
* File Reading: View the contents of any code file
* Code Search: Search for specific patterns across your codebase
* File Writing: Create new files or modify existing ones
* Directory Management: Create, delete, and organize folders
* File Operations: Move, copy, rename, and delete files
* Project Overview: Get a summary of your project structure
## Safety Features
* 1MB file size limit to prevent loading extremely large files
* Operations restricted to the configured codebase path
* Overwrite protection for existing files
* Warnings before deleting non-empty directories
## Requirements
* Windows
* Python 3.8 or higher
* Claude Desktop app with Pro subscription
## Installation
### Quick Install

Run setup.bat to automatically:

* Create a Python virtual environment
* Install required dependencies
* Configure the server
* Display Claude Desktop configuration instructions



### Manual Installation

Create a Python virtual environment:
```
python -m venv mcp_env
mcp_env\Scripts\activate
```
Install dependencies:
```
pip install mcp pathlib glob2
```
Configure Claude Desktop:

Open or create %AppData%\Claude\claude_desktop_config.json  
Add the following configuration (adjust paths as needed):
```
{
	"mcpServers": {
		"MCP_Codebase_Browser": {
			"command": "C:\path\to\your\mcp_env\Scripts\python.exe",
			"args": ["C:\path\to\your\codebase_server.py"]
		}
	}
}
```


Set your codebase path in the server script:

Open codebase_server.py  
Modify the CODEBASE_PATH variable to point to your project directory



## Usage

Place your entire codebase into the Project directory  
Add the configuration to Claude Desktop's `claude_desktop_config.json`  
Restart Claude Desktop  
Look for the hammer icon in the bottom right corner of the chat input box  
Ask Claude to perform tasks like:

* "List all files in the project"
* "Show me the content of src/main.py"
* "Create a new file called utils.js with the following content: [code]"
* "Search for all uses of 'import' in the codebase"
* "Rename file X to Y"
* "Create a new directory called 'models'"


![Claude will request permission to interact with your codebase](https://private-user-images.githubusercontent.com/64335998/432572069-7752f517-a0f4-40e9-b28c-3e2835e301ad.png?jwt=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJnaXRodWIuY29tIiwiYXVkIjoicmF3LmdpdGh1YnVzZXJjb250ZW50LmNvbSIsImtleSI6ImtleTUiLCJleHAiOjE3NDQzMzgxNDIsIm5iZiI6MTc0NDMzNzg0MiwicGF0aCI6Ii82NDMzNTk5OC80MzI1NzIwNjktNzc1MmY1MTctYTBmNC00MGU5LWIyOGMtM2UyODM1ZTMwMWFkLnBuZz9YLUFtei1BbGdvcml0aG09QVdTNC1ITUFDLVNIQTI1NiZYLUFtei1DcmVkZW50aWFsPUFLSUFWQ09EWUxTQTUzUFFLNFpBJTJGMjAyNTA0MTElMkZ1cy1lYXN0LTElMkZzMyUyRmF3czRfcmVxdWVzdCZYLUFtei1EYXRlPTIwMjUwNDExVDAyMTcyMlomWC1BbXotRXhwaXJlcz0zMDAmWC1BbXotU2lnbmF0dXJlPWRjNzk5ODViZTFiOTg4YTE0ODM5MWUwMDQxYmU5NTM2ZGM1ZDljZjVmN2Q0NGE3MjJlNjNiOTE2OWI2NWI4Y2YmWC1BbXotU2lnbmVkSGVhZGVycz1ob3N0In0.05DMlllK2LcU8_VRTu-Mac3yhRlSJyF3SX5maHWJLts)

![Claude can edit files directly](https://private-user-images.githubusercontent.com/64335998/432572071-8c0d2339-27c3-458b-826b-b8417ccfc041.png?jwt=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJnaXRodWIuY29tIiwiYXVkIjoicmF3LmdpdGh1YnVzZXJjb250ZW50LmNvbSIsImtleSI6ImtleTUiLCJleHAiOjE3NDQzMzgxNDIsIm5iZiI6MTc0NDMzNzg0MiwicGF0aCI6Ii82NDMzNTk5OC80MzI1NzIwNzEtOGMwZDIzMzktMjdjMy00NThiLTgyNmItYjg0MTdjY2ZjMDQxLnBuZz9YLUFtei1BbGdvcml0aG09QVdTNC1ITUFDLVNIQTI1NiZYLUFtei1DcmVkZW50aWFsPUFLSUFWQ09EWUxTQTUzUFFLNFpBJTJGMjAyNTA0MTElMkZ1cy1lYXN0LTElMkZzMyUyRmF3czRfcmVxdWVzdCZYLUFtei1EYXRlPTIwMjUwNDExVDAyMTcyMlomWC1BbXotRXhwaXJlcz0zMDAmWC1BbXotU2lnbmF0dXJlPThmY2NkOTcxNTgyZmExNzEwM2E4Yzg2YmY2YzUyZjMzNjQwMzdiYzYyNzMzZDJlY2I2ZjRkNWRjMzVkMGU3ZmUmWC1BbXotU2lnbmVkSGVhZGVycz1ob3N0In0.rmhw40fNOUWN15sM1qZETQPn5LtKXsmPaq3OtHgK7tM)

## Available Tools
Tool name       | Description
----------------|--------------------------------------------------
list_files      | List files in a directory of the codebase
read_file       | Read the contents of a file
search_code     | Search for specific patterns across files
write_file      | Create new files or modify existing ones
delete_file     | Remove files from the codebase
create_directory| Create new folders
delete_directory| Remove folders (empty or recursive)
move_file       | Move or rename files
copy_file       | Create copies of files
project_overview| Get a summary of the project structure

## Troubleshooting
* If Claude doesn't show the hammer icon, check that Claude Desktop is restarted
* Check Claude Desktop logs at %AppData%\Claude\logs\mcp*.log
* Ensure the paths in your configuration use double backslashes (\)
## License
MIT License