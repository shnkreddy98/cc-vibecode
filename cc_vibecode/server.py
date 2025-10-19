import json
import os
import signal
import subprocess
import time

from cc_vibecode.logger import create_logger
from pathlib import Path

logger = create_logger("server")

def start_server_background(project_dir: str):
    """Start server in background and store PID"""
    # Convert to absolute path to avoid issues after chdir
    abs_project_dir = os.path.abspath(project_dir)
    os.chdir(abs_project_dir)
    pid_file = Path(abs_project_dir) / '.dev-server.pid'
    
    # Setup commands
    # NOTE: Migrations are already applied by the agent during development
    # Running them again causes permission errors and is unnecessary
    commands = [
        (['git', 'pull', 'origin', 'main'], 'Pull changes'),
        (['npm', 'install'], 'Install dependencies'),
    ]
    
    # Run setup commands
    for cmd, desc in commands:
        logger.info(f"{desc}...")
        subprocess.run(cmd, check=True)
        logger.info(f"{desc} complete")
    
    # Start server in background
    logger.info("Starting development server in background...")

    # Redirect output to log file to prevent buffer overflow
    log_file = Path(abs_project_dir) / '.dev-server.log'
    log_handle = open(log_file, 'w')

    process = subprocess.Popen(
        ['npm', 'run', 'dev'],
        stdout=log_handle,
        stderr=subprocess.STDOUT
    )
    
    # Wait a moment for server to start
    time.sleep(3)
    
    if process.poll() is None:
        # Store PID in file
        with open(pid_file, 'w') as f:
            f.write(str(process.pid))

        logger.info("Server started successfully!")
        logger.info(f"Process ID: {process.pid}")
        logger.info(f"PID saved to: {pid_file}")
        logger.info(f"Server logs: {log_file}")
        logger.info("Server should be running at http://localhost:3000")
    else:
        logger.error("Server failed to start")
        logger.error(f"Check logs at: {log_file}")
    
    return process

def stop_server(project_dir: str):
    """Stop the background server using stored PID"""
    # Convert to absolute path for consistency
    abs_project_dir = os.path.abspath(project_dir)
    pid_file = Path(abs_project_dir) / '.dev-server.pid'

    if not pid_file.exists():
        logger.debug("No PID file found. Server may not be running.")
        return False
    
    try:
        # Read PID from file
        with open(pid_file, 'r') as f:
            pid = int(f.read().strip())
        
        logger.info(f"Stopping server (PID: {pid})...")
        
        # Kill the process
        os.kill(pid, signal.SIGTERM)
        
        # Wait a moment and check if it's dead
        time.sleep(1)
        
        try:
            # Check if process still exists
            os.kill(pid, 0)
            # If we're here, process is still alive, force kill
            logger.info("Process still running, forcing shutdown...")
            os.kill(pid, signal.SIGKILL)
        except OSError:
            # Process is dead
            pass
        
        # Remove PID file
        pid_file.unlink()
        logger.info("Server stopped successfully")
        return True
        
    except (ValueError, ProcessLookupError, OSError) as e:
        logger.error(f"Error stopping server: {e}")
        # Clean up stale PID file
        if pid_file.exists():
            pid_file.unlink()
        return False

# Usage
if __name__ == "__main__":
    project_path = '/path/to/project'
    
    # Start server
    process = start_server_background(project_path)
    
    # Later, to stop:
    # stop_server(project_path)

def add_scripts_to_package_json(project_dir: str):
    package_json_path = os.path.join(project_dir, 'package.json')
    
    scripts_to_add = {
        "dev": "next dev",
        "build": "next build",
        "start": "next start",
        "postinstall": "prisma generate"
    }
    
    # Read existing package.json
    with open(package_json_path, 'r') as f:
        package_data = json.load(f)
    
    # Add or update scripts
    if 'scripts' not in package_data:
        package_data['scripts'] = {}
    
    package_data['scripts'].update(scripts_to_add)
    
    # Write back to package.json with proper formatting
    with open(package_json_path, 'w') as f:
        json.dump(package_data, f, indent=2)
        f.write('\n')  # Add newline at end of file
    
    logger.info(f"Scripts added to {package_json_path}")