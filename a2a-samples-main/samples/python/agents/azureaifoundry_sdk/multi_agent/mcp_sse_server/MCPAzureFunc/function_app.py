import azure.functions as func
import datetime
import json
import logging
import os
import tempfile
import git
import shutil
import threading
import time
import configparser
from pathlib import Path

app = func.FunctionApp(http_auth_level=func.AuthLevel.FUNCTION)

# Global variables for repository information
GLOBAL_REPO_CONFIG_FILE = os.path.join(os.path.expanduser("~"), ".mcptools", "repo_config.ini")
GLOBAL_REPO_PROGRESS = {}

def save_repo_path_to_config(repo_name, repo_path):
    """Save repository path to global configuration file.
    
    Args:
        repo_name (str): Name of the repository
        repo_path (str): Full path to the repository
    """
    try:
        # Ensure directory exists
        config_dir = os.path.dirname(GLOBAL_REPO_CONFIG_FILE)
        os.makedirs(config_dir, exist_ok=True)
        
        # Read existing config or create new one
        config = configparser.ConfigParser()
        if os.path.exists(GLOBAL_REPO_CONFIG_FILE):
            config.read(GLOBAL_REPO_CONFIG_FILE)
            
        # Ensure repositories section exists
        if 'repositories' not in config:
            config['repositories'] = {}
            
        # Save repository path
        config['repositories'][repo_name] = repo_path
        
        # Save timestamps section if it doesn't exist
        if 'timestamps' not in config:
            config['timestamps'] = {}
        
        # Update timestamp for this repository
        config['timestamps'][repo_name] = datetime.datetime.now().isoformat()
        
        # Write config to file
        with open(GLOBAL_REPO_CONFIG_FILE, 'w') as configfile:
            config.write(configfile)
            
        logging.info(f"Saved repository path to global config: {repo_name} -> {repo_path}")
        return True
    except Exception as ex:
        logging.error(f"Failed to save repository path to config: {str(ex)}")
        return False

def get_repo_path_from_config(repo_name):
    """Get repository path from global configuration file.
    
    Args:
        repo_name (str): Name of the repository
        
    Returns:
        str: Path to the repository or None if not found
    """
    try:
        if not os.path.exists(GLOBAL_REPO_CONFIG_FILE):
            return None
            
        config = configparser.ConfigParser()
        config.read(GLOBAL_REPO_CONFIG_FILE)
        
        if 'repositories' not in config or repo_name not in config['repositories']:
            return None
            
        return config['repositories'][repo_name]
    except Exception as ex:
        logging.error(f"Failed to get repository path from config: {str(ex)}")
        return None

# Custom progress handler for git clone
class GitProgressHandler(git.remote.RemoteProgress):
    def __init__(self, repo_name):
        super().__init__()
        self.repo_name = repo_name
        GLOBAL_REPO_PROGRESS[repo_name] = {
            'status': 'starting',
            'percent': 0,
            'current_operation': 'Preparing to clone',
            'bytes_transferred': 0,
            'total_objects': 0,
            'indexed_objects': 0,
            'received_objects': 0,
            'total_deltas': 0,
            'resolved_deltas': 0,
            'last_update': datetime.datetime.now().isoformat()
        }

    def update(self, op_code, cur_count, max_count=None, message=''):
        # Update progress information
        progress = GLOBAL_REPO_PROGRESS[self.repo_name]
        
        # Calculate percentage
        if max_count is not None and max_count > 0:
            progress['percent'] = int((cur_count / max_count) * 100)
        else:
            progress['percent'] = 0
            
        # Update stage information
        if op_code & git.remote.RemoteProgress.COUNTING:
            progress['status'] = 'counting'
            progress['current_operation'] = 'Counting objects'
        elif op_code & git.remote.RemoteProgress.COMPRESSING:
            progress['status'] = 'compressing'
            progress['current_operation'] = 'Compressing objects'
        elif op_code & git.remote.RemoteProgress.RECEIVING:
            progress['status'] = 'receiving'
            progress['current_operation'] = 'Receiving objects'
        elif op_code & git.remote.RemoteProgress.RESOLVING:
            progress['status'] = 'resolving'
            progress['current_operation'] = 'Resolving deltas'
        elif op_code & git.remote.RemoteProgress.WRITING:
            progress['status'] = 'writing'
            progress['current_operation'] = 'Writing objects'
        elif op_code & git.remote.RemoteProgress.FINDING_SOURCES:
            progress['status'] = 'finding_sources'
            progress['current_operation'] = 'Finding sources'
        elif op_code & git.remote.RemoteProgress.CHECKING_OUT:
            progress['status'] = 'checking_out'
            progress['current_operation'] = 'Checking out files'
            
        # Update counters
        progress['total_objects'] = self.total_objects
        progress['indexed_objects'] = self.indexed_objects
        progress['received_objects'] = self.received_objects
        progress['total_deltas'] = self.total_deltas
        progress['resolved_deltas'] = self.resolved_deltas
        
        # Add message if provided
        if message:
            progress['message'] = message
            
        # Update timestamp
        progress['last_update'] = datetime.datetime.now().isoformat()
        
        # Log progress
        logging.info(f"Clone progress for {self.repo_name}: {progress['current_operation']} - {progress['percent']}%")

@app.generic_trigger(
    arg_name="context",
    type="mcpToolTrigger",
    tool_name="hello_mcp",
    description="Hello MCP tool",
    toolProperties="[]"
)
def hello_mcp(context) -> str:
    """Hello MCP tool trigger function.

    Args:
        context (func.Context): The function context.

    Returns:
        str: A greeting message.
    """
    logging.info("Hello MCP tool trigger function processed a request.")
    return "Hello MCP!"

@app.generic_trigger(
    arg_name="context",
    type="mcpToolTrigger",
    tool_name="open_vscode_mcp",
    description="Open project in Visual Studio Code",
    toolProperties="""[
        {
            "propertyName": "path", 
            "propertyType": "string", 
            "description": "The file or folder path to open in VS Code"
        }
    ]"""
)
def open_vscode_mcp(context) -> str:
    """Opens a file or folder in Visual Studio Code.

    This function supports Windows, macOS, and Linux operating systems.
    It checks if VS Code is installed before attempting to open the path.

    Args:
        context: The function context containing the input arguments.

    Returns:
        str: A message indicating the success or failure of the operation.
    """
    try:
        import platform
        import subprocess
        import shlex
        
        # Parse the context to get the input parameters
        content = json.loads(context)
        arguments = content.get("arguments", {})
        
        # Get the path parameter
        path = arguments.get("path")
        if not path:
            logging.error("No path provided")
            return json.dumps({
                "status": "error", 
                "message": "Error: No path provided to open in VS Code"
            }, indent=2)
        
        # Normalize path and check if it exists
        path = os.path.abspath(os.path.expanduser(path))
        if not os.path.exists(path):
            logging.error(f"Path does not exist: {path}")
            return json.dumps({
                "status": "error", 
                "message": f"Error: Path does not exist: {path}"
            }, indent=2)
        
        # Determine the operating system
        system = platform.system()
        
        # Set the command to check if VS Code is installed
        vscode_commands = {
            "Windows": ["where", "code"],
            "Darwin": ["which", "code"],  # macOS
            "Linux": ["which", "code"]
        }
        
        if system not in vscode_commands:
            return json.dumps({
                "status": "error", 
                "message": f"Error: Unsupported operating system: {system}"
            }, indent=2)
            
        # Check if VS Code is installed
        check_command = vscode_commands[system]
        try:
            result = subprocess.run(check_command, capture_output=True, text=True)
            if result.returncode != 0:
                # VS Code command-line isn't available; check for specific paths
                vscode_paths = {
                    "Windows": [
                        "C:\\Program Files\\Microsoft VS Code\\bin\\code",
                        "C:\\Program Files (x86)\\Microsoft VS Code\\bin\\code",
                        os.path.expanduser("~\\AppData\\Local\\Programs\\Microsoft VS Code\\bin\\code.cmd")
                    ],
                    "Darwin": [
                        "/Applications/Visual Studio Code.app/Contents/Resources/app/bin/code",
                        os.path.expanduser("~/Applications/Visual Studio Code.app/Contents/Resources/app/bin/code")
                    ],
                    "Linux": [
                        "/usr/bin/code",
                        "/usr/local/bin/code",
                        os.path.expanduser("~/.local/bin/code")
                    ]
                }
                
                vscode_found = False
                for vscode_path in vscode_paths.get(system, []):
                    if os.path.exists(vscode_path):
                        vscode_found = True
                        break
                
                if not vscode_found:
                    return json.dumps({
                        "status": "error", 
                        "message": "Error: Visual Studio Code is not installed or not in PATH"
                    }, indent=2)
        except Exception as ex:
            logging.error(f"Error checking for VS Code: {str(ex)}")
            return json.dumps({
                "status": "error", 
                "message": f"Error checking for VS Code: {str(ex)}"
            }, indent=2)
        
        # Set the command to open VS Code
        if system == "Windows":
            open_command = ["code", path]
        elif system == "Darwin":  # macOS
            open_command = ["open", "-a", "Visual Studio Code", path]
        else:  # Linux
            open_command = ["code", path]
        
        # Execute the command to open VS Code
        try:
            logging.info(f"Opening path in VS Code: {path}")
            
            if system == "Windows":
                process = subprocess.Popen(open_command, shell=True)
            else:
                # Use Popen with shell=False for better security on Unix systems
                process = subprocess.Popen(open_command)
            
            # Return success
            success_message = {
                "status": "success",
                "message": f"Successfully opened {path} in Visual Studio Code",
                "path": path,
                "os": system,
                "process_id": process.pid
            }
            
            logging.info(f"Successfully opened {path} in VS Code (PID: {process.pid})")
            return json.dumps(success_message, indent=2)
            
        except Exception as ex:
            logging.error(f"Error opening VS Code: {str(ex)}")
            return json.dumps({
                "status": "error", 
                "message": f"Error opening VS Code: {str(ex)}"
            }, indent=2)
            
    except Exception as ex:
        error_message = f"Error in open_vscode_mcp: {str(ex)}"
        logging.exception(error_message)
        return json.dumps({
            "status": "error", 
            "message": error_message
        }, indent=2)

@app.generic_trigger(
    arg_name="context",
    type="mcpToolTrigger",
    tool_name="clone_github_repo_mcp",
    description="Clone GitHub repository",
    toolProperties="""[
        {
            "propertyName": "repo_url", 
            "propertyType": "string", 
            "description": "The GitHub repository URL to clone"
        },
        {
            "propertyName": "branch", 
            "propertyType": "string", 
            "description": "Optional: The branch to clone (defaults to main if not specified)"
        },
        {
            "propertyName": "depth",
            "propertyType": "number",
            "description": "Optional: Create a shallow clone with a specified number of commits (defaults to full clone)"
        },
        {
            "propertyName": "include_submodules",
            "propertyType": "boolean",
            "description": "Optional: Whether to clone submodules (defaults to false)"
        },
        {
            "propertyName": "custom_path",
            "propertyType": "string",
            "description": "Optional: Custom path where the repository should be cloned"
        },
        {
            "propertyName": "retry_count",
            "propertyType": "number",
            "description": "Optional: Number of retry attempts if clone fails (defaults to 3)"
        }
    ]"""
)
def clone_github_repo_mcp(context) -> str:
    """Clone a GitHub repository.

    Args:
        context: The function context containing the input arguments.

    Returns:
        str: A message indicating the success or failure of the operation with repository details
             and the globally saved path.
    """
    try:
        # Parse the context to get the input parameters
        content = json.loads(context)
        arguments = content.get("arguments", {})
        
        # Get repository parameters
        repo_url = arguments.get("repo_url")
        branch = arguments.get("branch", "main")
        depth = arguments.get("depth", None)
        include_submodules = arguments.get("include_submodules", False)
        custom_path = arguments.get("custom_path", None)
        retry_count = int(arguments.get("retry_count", 3))  # Default to 3 retries
        
        if not repo_url:
            logging.error("No repository URL provided")
            return "Error: No repository URL provided"
        
        # Extract repo name from URL for logging
        repo_name = repo_url.split("/")[-1].replace(".git", "")
        
        # First check if repo already exists in global config and if the path still exists
        existing_path = get_repo_path_from_config(repo_name)
        if existing_path and os.path.exists(existing_path) and not custom_path:
            logging.info(f"Repository already exists at {existing_path}.")
            # Return the existing repository information
            try:
                repo = git.Repo(existing_path)
                current_branch = repo.active_branch.name
                commit_count = sum(1 for _ in repo.iter_commits())
                last_commit = repo.head.commit
                repo_files = os.listdir(existing_path)
                
                success_message = {
                    # "status": "exists",
                    # "repository": repo_name,
                    # "branch": current_branch,
                    # "commit_count": commit_count,
                    "folder": existing_path,  # Return the globally saved path
                    # "last_commit": {
                    #     "hash": last_commit.hexsha[:8],
                    #     "author": f"{last_commit.author.name} <{last_commit.author.email}>",
                    #     "date": last_commit.committed_datetime.isoformat(),
                    #     "message": last_commit.message.strip()
                    # },
                    # "files": repo_files
                }
                return json.dumps(success_message, indent=2)
            except Exception as ex:
                logging.warning(f"Error reading existing repository: {str(ex)}. Will clone again.")
                
        # Define the repository directory
        if custom_path:
            repo_base_dir = os.path.dirname(custom_path)
            repo_dir = custom_path
        else:
            # Updated default path to /Users/lokinfey/Repo
            repo_base_dir = "/Users/lokinfey/Repo"
            repo_dir = os.path.join(repo_base_dir, repo_name)
        
        # Create the base directory if it doesn't exist
        os.makedirs(repo_base_dir, exist_ok=True)
        
        # Remove the repo directory if it already exists
        if os.path.exists(repo_dir):
            logging.info(f"Repository directory already exists, removing: {repo_dir}")
            shutil.rmtree(repo_dir)
            
        logging.info(f"Cloning repository {repo_name} into directory {repo_dir}")
        
        # Initialize status for simple logging
        GLOBAL_REPO_PROGRESS[repo_name] = {
            'status': 'initializing'
        }
        
        # Prepare clone options
        clone_options = {
            "branch": branch
        }
        
        # Add depth parameter if specified
        if depth is not None:
            clone_options["depth"] = depth
        
        # Function to perform the clone with retries but without progress display
        def perform_clone_with_retries(retry_attempts):
            for attempt in range(1, retry_attempts + 1):
                try:
                    logging.info(f"Clone attempt {attempt} of {retry_attempts}")
                    
                    # Verify Git is installed and working
                    try:
                        git_version = git.cmd.Git().version()
                        logging.info(f"Git version: {git_version}")
                    except Exception as git_version_err:
                        logging.error(f"Git version check failed: {str(git_version_err)}")
                        raise Exception(f"Git command not available. Please ensure Git is installed: {str(git_version_err)}")
                    
                    # Verify repository URL format
                    if not (repo_url.startswith("https://") or repo_url.startswith("git@")):
                        error_msg = f"Invalid repository URL format: {repo_url}. URLs should start with 'https://' or 'git@'"
                        logging.error(error_msg)
                        raise ValueError(error_msg)
                    
                    # Clone the repository
                    repo = git.Repo.clone_from(repo_url, repo_dir, **clone_options)
                    
                    # Clone submodules if requested
                    if include_submodules:
                        repo.git.submodule('update', '--init', '--recursive')
                    
                    # Save repository path to global config
                    save_result = save_repo_path_to_config(repo_name, repo_dir)
                    
                    # Get repository information
                    current_branch = repo.active_branch.name
                    commit_count = sum(1 for _ in repo.iter_commits())
                    last_commit = repo.head.commit
                    
                    # List the files in the repository (top level only)
                    repo_files = os.listdir(repo_dir)
                    
                    # Return success message with repo details and emphasizing the globally saved path
                    success_message = {
                        "status": "success",
                        "repository": repo_name,
                        "branch": current_branch,
                        "commit_count": commit_count,
                        "file_path": repo_dir,  # Return the globally saved path as primary information
                        "global_config_file": GLOBAL_REPO_CONFIG_FILE,
                        "global_path_saved": save_result,
                        "last_commit": {
                            "hash": last_commit.hexsha[:8],
                            "author": f"{last_commit.author.name} <{last_commit.author.email}>",
                            "date": last_commit.committed_datetime.isoformat(),
                            "message": last_commit.message.strip()
                        },
                        "files": repo_files
                    }
                    
                    logging.info(f"Successfully cloned repository: {repo_name}")
                    logging.info(f"Global saved path: {repo_dir}")
                    
                    return {
                        "success": True,
                        "repo": repo,
                        "message": success_message
                    }
                    
                except git.GitCommandError as git_err:
                    # Log error information
                    error_info = {
                        "error_type": "GitCommandError",
                        "command": ' '.join(git_err.command) if isinstance(git_err.command, list) else git_err.command,
                        "status": git_err.status,
                        "stderr": git_err.stderr if hasattr(git_err, 'stderr') else '',
                        "stdout": git_err.stdout if hasattr(git_err, 'stdout') else ''
                    }
                    logging.error(f"Git clone error (attempt {attempt}): {error_info}")
                    
                    # Clean up any partial clone
                    if os.path.exists(repo_dir):
                        try:
                            shutil.rmtree(repo_dir)
                            logging.info(f"Cleaned up partial repository clone at {repo_dir}")
                        except Exception as cleanup_err:
                            logging.warning(f"Failed to clean up partial repository: {str(cleanup_err)}")
                    
                    # If we've exhausted our retries, re-raise the error
                    if attempt >= retry_attempts:
                        raise
                    
                    # Otherwise wait and retry
                    retry_delay = min(2 ** attempt, 30)  # Exponential backoff, max 30 seconds
                    logging.info(f"Retrying in {retry_delay} seconds...")
                    time.sleep(retry_delay)
            
            # If we reach here, all retries failed
            raise Exception("All clone attempts failed")
        
        # Perform the clone with retries
        try:
            result = perform_clone_with_retries(retry_count)
            return json.dumps(result["message"], indent=2)
            
        except git.GitCommandError as git_err:
            # Detailed error analysis for common git issues
            error_message = f"Git command error: {str(git_err)}"
            detailed_error = {
                "error_type": "GitCommandError",
                "command": ' '.join(git_err.command) if isinstance(git_err.command, list) else git_err.command,
                "status": git_err.status,
                "stderr": git_err.stderr if hasattr(git_err, 'stderr') else '',
                "stdout": git_err.stdout if hasattr(git_err, 'stdout') else ''
            }
            
            # Check for specific error conditions
            stderr = git_err.stderr if hasattr(git_err, 'stderr') else ''
            stderr_lower = stderr.lower() if stderr else ""
            
            if "could not resolve host" in stderr_lower:
                error_message = f"Network error: Could not resolve host. Please check your internet connection and the repository URL: {repo_url}"
            elif "authentication failed" in stderr_lower or "403" in stderr_lower:
                error_message = f"Authentication error: Failed to authenticate with GitHub. For private repositories, ensure you have the necessary permissions and are using the correct authentication."
            elif "repository not found" in stderr_lower or "404" in stderr_lower:
                error_message = f"Repository not found: The repository {repo_url} does not exist or is private without proper authentication."
            elif "already exists and is not an empty directory" in stderr_lower:
                error_message = f"Directory error: The target directory {repo_dir} already exists and is not empty. This should have been handled by the code."
            elif "ssl" in stderr_lower or "certificate" in stderr_lower:
                error_message = f"SSL Certificate error: There was an issue with the SSL certificate validation when connecting to GitHub."
            elif "exit code(128)" in stderr_lower:
                error_message = f"Git error (exit code 128): This could be due to permission issues, network problems, or repository access restrictions. Verify that the repository exists and you have permission to access it."
            
            logging.error(error_message)
            logging.error(f"Detailed git error: {detailed_error}")
            
            return json.dumps({
                "status": "error", 
                "message": error_message,
                "detailed_error": detailed_error
            }, indent=2)
        
    except Exception as ex:
        error_message = f"Error while cloning repository: {str(ex)}"
        logging.exception(error_message)
        
        # Return error
        response = {"status": "error", "message": error_message}
        return json.dumps(response, indent=2)
