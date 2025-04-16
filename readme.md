# MCP Codebase Browser
A Python-based Model Context Protocol (MCP) server that gives Claude full access to your codebase, allowing it to read, write, create, delete, edit, and manage files and directories.  

This server was created with assistance from Claude 3.7 Sonnet.  

I've tried a few other MCP tools and I found that they were just overwhelming with dependencies or complexities that I didn't want or need. So I tried to create a simple easy to setup MCP tool that would let Claude (and maybe other AI one day) just mess with files on my computer.  

It's currently not very advanced, but that's kinda the plan is to keep it simple. I've talked to Claude waayy too much and I feel like I know how he ticks, and this tool is created in a way to not go against the grain with Claude's typical behaviors.  


![MCP Server](https://private-user-images.githubusercontent.com/64335998/432573576-562915ad-c4d4-4855-9228-5a8c2834f608.png?jwt=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJnaXRodWIuY29tIiwiYXVkIjoicmF3LmdpdGh1YnVzZXJjb250ZW50LmNvbSIsImtleSI6ImtleTUiLCJleHAiOjE3NDQzMzgxNDIsIm5iZiI6MTc0NDMzNzg0MiwicGF0aCI6Ii82NDMzNTk5OC80MzI1NzM1NzYtNTYyOTE1YWQtYzRkNC00ODU1LTkyMjgtNWE4YzI4MzRmNjA4LnBuZz9YLUFtei1BbGdvcml0aG09QVdTNC1ITUFDLVNIQTI1NiZYLUFtei1DcmVkZW50aWFsPUFLSUFWQ09EWUxTQTUzUFFLNFpBJTJGMjAyNTA0MTElMkZ1cy1lYXN0LTElMkZzMyUyRmF3czRfcmVxdWVzdCZYLUFtei1EYXRlPTIwMjUwNDExVDAyMTcyMlomWC1BbXotRXhwaXJlcz0zMDAmWC1BbXotU2lnbmF0dXJlPTRkNzY3ZTkyOTZjMzU4OWMwMzExYTRlMjllYzUwNjUzOTg4MGRlNjMwNjEyNDBiNDU0N2I5N2FlZjFmMTIxMWImWC1BbXotU2lnbmVkSGVhZGVycz1ob3N0In0.sqTQO4Phm3T5vx1-q9IQmx_Yd_5Sfg_tNWoRTLHYpg4)

## Requirements
* Windows
* Python 3.8 or higher
* Claude Desktop app with Pro subscription

## Installation
### Quick Install

Run setup.bat to automatically:

* Create a Python virtual environment
* Install required dependencies
* Create a Project directory
* Display Claude Desktop configuration instructions


### Manual Installation
Create a Python virtual environment:
```
python -m venv mcp_env
mcp_env\Scripts\activate
```
Install dependencies:
```
pip install mcp pathlib glob2 diff_match_patch
```

Create a directory named `Project`  

Configure Claude Desktop:

Open claude_desktop_config.json  
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

## Usage
Complete the setup, make sure to add your custom configuration to Claude Desktop's `claude_desktop_config.json` 
Place your entire codebase into the `Project` directory  
Restart Claude Desktop  
Look for the hammer icon in the bottom right corner of the chat input box  
Claude can now perform various codebase tasks when you ask him to  
When Claude tries to use a tool, he will ask for permission first  

![Claude will request permission to interact with your codebase](https://private-user-images.githubusercontent.com/64335998/432572069-7752f517-a0f4-40e9-b28c-3e2835e301ad.png?jwt=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJnaXRodWIuY29tIiwiYXVkIjoicmF3LmdpdGh1YnVzZXJjb250ZW50LmNvbSIsImtleSI6ImtleTUiLCJleHAiOjE3NDQzMzgxNDIsIm5iZiI6MTc0NDMzNzg0MiwicGF0aCI6Ii82NDMzNTk5OC80MzI1NzIwNjktNzc1MmY1MTctYTBmNC00MGU5LWIyOGMtM2UyODM1ZTMwMWFkLnBuZz9YLUFtei1BbGdvcml0aG09QVdTNC1ITUFDLVNIQTI1NiZYLUFtei1DcmVkZW50aWFsPUFLSUFWQ09EWUxTQTUzUFFLNFpBJTJGMjAyNTA0MTElMkZ1cy1lYXN0LTElMkZzMyUyRmF3czRfcmVxdWVzdCZYLUFtei1EYXRlPTIwMjUwNDExVDAyMTcyMlomWC1BbXotRXhwaXJlcz0zMDAmWC1BbXotU2lnbmF0dXJlPWRjNzk5ODViZTFiOTg4YTE0ODM5MWUwMDQxYmU5NTM2ZGM1ZDljZjVmN2Q0NGE3MjJlNjNiOTE2OWI2NWI4Y2YmWC1BbXotU2lnbmVkSGVhZGVycz1ob3N0In0.05DMlllK2LcU8_VRTu-Mac3yhRlSJyF3SX5maHWJLts)

Consider the following examples:

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
* 1MB file size limit to prevent loading large files
* Through abstraction of the actual filepath, Claude should be restricted to the codebase path
* Unless he knows the full file path, Backups cannot be deleted by Claude

# WARNING
This tool will allow Claude to make changes to your files. He will probably break things.

![Uh oh](https://private-user-images.githubusercontent.com/64335998/433124637-d56f79b3-20e2-44a7-8bd9-a10ccc4337f8.png?jwt=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJnaXRodWIuY29tIiwiYXVkIjoicmF3LmdpdGh1YnVzZXJjb250ZW50LmNvbSIsImtleSI6ImtleTUiLCJleHAiOjE3NDQ1NDAzMjcsIm5iZiI6MTc0NDU0MDAyNywicGF0aCI6Ii82NDMzNTk5OC80MzMxMjQ2MzctZDU2Zjc5YjMtMjBlMi00NGE3LThiZDktYTEwY2NjNDMzN2Y4LnBuZz9YLUFtei1BbGdvcml0aG09QVdTNC1ITUFDLVNIQTI1NiZYLUFtei1DcmVkZW50aWFsPUFLSUFWQ09EWUxTQTUzUFFLNFpBJTJGMjAyNTA0MTMlMkZ1cy1lYXN0LTElMkZzMyUyRmF3czRfcmVxdWVzdCZYLUFtei1EYXRlPTIwMjUwNDEzVDEwMjcwN1omWC1BbXotRXhwaXJlcz0zMDAmWC1BbXotU2lnbmF0dXJlPWY1NWJmYzFiMjM1NzhjMDVmYjYwMzE0YTA4ZTdmNjU5YzNmNDExYzE5YWYxNjI0MTliOWE0MGUzYmZhYTQ5Y2YmWC1BbXotU2lnbmVkSGVhZGVycz1ob3N0In0.FingsDQG8XXKC350q4G2yFlh3cNwgwDswbFxW0Ofk-U)

This project is a WIP, I take no responsibility for this tool losing your data. I recommend asking Claude to make backups often.

## Troubleshooting
* If Claude doesn't show the hammer icon, check that Claude Desktop is restarted
* Check Claude Desktop logs at %AppData%\Claude\logs\mcp*.log
* Ensure the paths in your configuration use double backslashes (\)
* This has only been tested with Claude and Windows

## Useage notes
* I opted to put everything into a single tool, so you don't have to click the "allow tool" on Claude all the time, but this lets him just have full freedom instantly, it can be a good and bad thing
* Because there aren't many restrictions, Claude can get VERY carried away with this tool. He will just go hard and he has no regard for anything but the task at hand. Beware that he will inevitably change things you did not want him to change.
* Primarily the tool has been successful with JavaScript and Java projects so far, but it should extend to other languages pretty easily
* Sometimes there's a syntax error, something simple, like an extra bracket or whatever, check your code, it's not that often that it happens though
* There aren't any limits to what gets returned to Claude in many scenarios, meaning there can be high context useage on large files, I did try to limit search results to 5 results though

## Design thoughts
*I try to embrace and work with the behavior of Claude as much as I can. Other tools I've used might try to "teach" claude through error messages. For example, I've seen a text editor tool try to engineer a device to lock Claude out from doing subsequent edits to a file. In my experience, Claude sucks at calculating line numbers. If it's line editing, he'll insert stuff on lines that he didn't calculate to have been changed from a recent edit, so he breaks the files easily. The developer of the text editor tool obviously came to the same conlusion that I have. The solution in the text editing tool was to make a checksum based puzzle that Claude has to solve. In my experience with the tool Claude just gives up and tries to find a different avenue, he couldn't be bothered to try to solve the puzzle a large percentage of the time. I've learned that Claude stops paying attention after the tool reports "success" or "fail". The engineering of the puzzle tries to correct Claude's behavior, but if you work with Claude often you will realize that while you might sometimes be able to break his bad habits with enough in-context learning, it's a steep climb to success a lot of the time.
*What I'm getting at is that instead of trying to fight Claude's consistent bad behaviors, I try to lean into his good behaviors instead. He just doesn't learn through these tools, so I don't try to teach him or train him to use the tool in any special way. So for the example of editing text, I've found that Claude has an uncanny ability to keep an accurate mental construct of your code. The code in this intangible construct is very well maintained by Claude. To embrace this strength, I tried to engineer the tool to just let Claude write out what he THINKS needs to be patched, and the tool will match this and replace it with his replacement code, and it works without error most of the time because Claude is keeping very good track of the current state of the code he is working with, so the match almost always is there without Claude even needing to read the file more than once. We don't talk about line numbers, because we KNOW that Claude sucks at calculating accurate line numbers. There are no intentionally built pitfalls for Claude to get stuck in. This affords us very minimal tool use failures.

## License
MIT License