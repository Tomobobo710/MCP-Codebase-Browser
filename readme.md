# MCP Codebase Browser
A Python-based Model Context Protocol (MCP) server that gives Claude full access to your codebase, allowing it to read, write, create, delete, and manage files and directories. This server was created with assistance from Claude 3.7 Sonnet.  
![MCP Server](https://private-user-images.githubusercontent.com/64335998/432573576-562915ad-c4d4-4855-9228-5a8c2834f608.png?jwt=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJnaXRodWIuY29tIiwiYXVkIjoicmF3LmdpdGh1YnVzZXJjb250ZW50LmNvbSIsImtleSI6ImtleTUiLCJleHAiOjE3NDQzMzgxNDIsIm5iZiI6MTc0NDMzNzg0MiwicGF0aCI6Ii82NDMzNTk5OC80MzI1NzM1NzYtNTYyOTE1YWQtYzRkNC00ODU1LTkyMjgtNWE4YzI4MzRmNjA4LnBuZz9YLUFtei1BbGdvcml0aG09QVdTNC1ITUFDLVNIQTI1NiZYLUFtei1DcmVkZW50aWFsPUFLSUFWQ09EWUxTQTUzUFFLNFpBJTJGMjAyNTA0MTElMkZ1cy1lYXN0LTElMkZzMyUyRmF3czRfcmVxdWVzdCZYLUFtei1EYXRlPTIwMjUwNDExVDAyMTcyMlomWC1BbXotRXhwaXJlcz0zMDAmWC1BbXotU2lnbmF0dXJlPTRkNzY3ZTkyOTZjMzU4OWMwMzExYTRlMjllYzUwNjUzOTg4MGRlNjMwNjEyNDBiNDU0N2I5N2FlZjFmMTIxMWImWC1BbXotU2lnbmVkSGVhZGVycz1ob3N0In0.sqTQO4Phm3T5vx1-q9IQmx_Yd_5Sfg_tNWoRTLHYpg4)

## Available Tools
Tool name       | Description
----------------|--------------------------------------------------
list_files      | Lists all files in the codebase
read_file       | Read the contents of a file
search_code     | Search for specific patterns
write_file      | Create new files
delete_file     | Remove files
create_directory| Create new folders
delete_directory| Remove folders
move_file       | Move or rename files
copy_file       | Create copies of files
read_lines      | Read a specific line or set of lines
edit_lines      | Edit a specific line or set of lines
backup_codebase | Backs up the entire Projects directory
list_backups    | Lists available backups
restore_codebase| Read a specific line or set of lines

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
Add a configuration (adjust paths as needed):
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

Edit codebase_server.py  
Modify the CODEBASE_PATH variable to point to your project directory

## Usage
Place your entire codebase into the Project directory  
Add the configuration to Claude Desktop's `claude_desktop_config.json`  
Restart Claude Desktop  
Look for the hammer icon in the bottom right corner of the chat input box  
When Claude trys to use the tool, he will ask for permission first  


![Claude will request permission to interact with your codebase](https://private-user-images.githubusercontent.com/64335998/432572069-7752f517-a0f4-40e9-b28c-3e2835e301ad.png?jwt=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJnaXRodWIuY29tIiwiYXVkIjoicmF3LmdpdGh1YnVzZXJjb250ZW50LmNvbSIsImtleSI6ImtleTUiLCJleHAiOjE3NDQzMzgxNDIsIm5iZiI6MTc0NDMzNzg0MiwicGF0aCI6Ii82NDMzNTk5OC80MzI1NzIwNjktNzc1MmY1MTctYTBmNC00MGU5LWIyOGMtM2UyODM1ZTMwMWFkLnBuZz9YLUFtei1BbGdvcml0aG09QVdTNC1ITUFDLVNIQTI1NiZYLUFtei1DcmVkZW50aWFsPUFLSUFWQ09EWUxTQTUzUFFLNFpBJTJGMjAyNTA0MTElMkZ1cy1lYXN0LTElMkZzMyUyRmF3czRfcmVxdWVzdCZYLUFtei1EYXRlPTIwMjUwNDExVDAyMTcyMlomWC1BbXotRXhwaXJlcz0zMDAmWC1BbXotU2lnbmF0dXJlPWRjNzk5ODViZTFiOTg4YTE0ODM5MWUwMDQxYmU5NTM2ZGM1ZDljZjVmN2Q0NGE3MjJlNjNiOTE2OWI2NWI4Y2YmWC1BbXotU2lnbmVkSGVhZGVycz1ob3N0In0.05DMlllK2LcU8_VRTu-Mac3yhRlSJyF3SX5maHWJLts)


Claude can now perform various codebase tasks when you ask him to, consider the following examples:

* "List all files in the project"
* "Read the content of src/main.py"
* "Create a new file called utils.js and move our utilities there"
* "Search for all uses of 'import' in the codebase"
* "Edit line 53 and increase the font size"
* "Show me all blocks of code with 'dogs' in them"
* "Rename file X to Y"
* "Create a new directory called 'models'"
* "Search for 'function' in the code"
* "Backup my codebase named 'my_project_backup'"
* "List our backed up projects'"
* "Restore 'my_project_backup'"

## Safety Features
* 1MB file size limit to prevent loading extremely large files
* Through abstraction of the actual filepath, Claude should be restricted to the codebase path
* Backups cannot be deleted by Claude

# WARNING
This tool will allow Claude to make changes to your files. He will probably break things.

![Uh oh](https://private-user-images.githubusercontent.com/64335998/433124637-d56f79b3-20e2-44a7-8bd9-a10ccc4337f8.png?jwt=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJnaXRodWIuY29tIiwiYXVkIjoicmF3LmdpdGh1YnVzZXJjb250ZW50LmNvbSIsImtleSI6ImtleTUiLCJleHAiOjE3NDQ1NDAzMjcsIm5iZiI6MTc0NDU0MDAyNywicGF0aCI6Ii82NDMzNTk5OC80MzMxMjQ2MzctZDU2Zjc5YjMtMjBlMi00NGE3LThiZDktYTEwY2NjNDMzN2Y4LnBuZz9YLUFtei1BbGdvcml0aG09QVdTNC1ITUFDLVNIQTI1NiZYLUFtei1DcmVkZW50aWFsPUFLSUFWQ09EWUxTQTUzUFFLNFpBJTJGMjAyNTA0MTMlMkZ1cy1lYXN0LTElMkZzMyUyRmF3czRfcmVxdWVzdCZYLUFtei1EYXRlPTIwMjUwNDEzVDEwMjcwN1omWC1BbXotRXhwaXJlcz0zMDAmWC1BbXotU2lnbmF0dXJlPWY1NWJmYzFiMjM1NzhjMDVmYjYwMzE0YTA4ZTdmNjU5YzNmNDExYzE5YWYxNjI0MTliOWE0MGUzYmZhYTQ5Y2YmWC1BbXotU2lnbmVkSGVhZGVycz1ob3N0In0.FingsDQG8XXKC350q4G2yFlh3cNwgwDswbFxW0Ofk-U)

This project is a WIP, I can't take responsibility for this tool losing your data, I reccomend asking Claude to make backups often.

## Troubleshooting
* If Claude doesn't show the hammer icon, check that Claude Desktop is restarted
* Check Claude Desktop logs at %AppData%\Claude\logs\mcp*.log
* Ensure the paths in your configuration use double backslashes (\)

## License
MIT License