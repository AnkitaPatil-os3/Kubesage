import asyncio
import subprocess
import shlex
import re
import time
from datetime import datetime
from app.logger import logger
from typing import Dict, Any

def sanitize_query(query: str) -> str:
    """Clean and normalize the input query"""
    # Remove extra whitespace and normalize
    sanitized = re.sub(r'\s+', ' ', query.strip())
    return sanitized

async def execute_command_async(command: str, timeout: int = 30) -> Dict[str, Any]:
    """Execute a kubectl command asynchronously with timeout"""
    start_time = time.time()
    start_datetime = datetime.utcnow().isoformat()
    
    # Prepare result structure
    result = {
        "metadata": {
            "start_time": start_datetime,
            "end_time": None,
            "duration_ms": 0.0,
            "success": False,
            "error_type": None,
            "error_code": None
        }
    }
    
    try:
        # Parse command safely
        args = shlex.split(command)
        
        # Create subprocess
        process = await asyncio.create_subprocess_exec(
            *args,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        
        # Wait for process with timeout
        try:
            stdout, stderr = await asyncio.wait_for(process.communicate(), timeout=timeout)
            
            # Process results
            if process.returncode == 0:
                result["execution_result"] = stdout.decode().strip()
                result["metadata"]["success"] = True
            else:
                result["execution_error"] = stderr.decode().strip()
                result["metadata"]["error_type"] = "command_error"
                result["metadata"]["error_code"] = process.returncode
                
        except asyncio.TimeoutError:
            # Handle timeout
            try:
                process.kill()
            except:
                pass
                
            result["execution_error"] = f"Command execution timed out after {timeout} seconds"
            result["metadata"]["error_type"] = "timeout"
            
    except Exception as e:
        # Handle other errors
        result["execution_error"] = f"Error executing command: {str(e)}"
        result["metadata"]["error_type"] = "execution_error"
    
    # Calculate duration and set end time
    end_time = time.time()
    result["metadata"]["duration_ms"] = (end_time - start_time) * 1000
    result["metadata"]["end_time"] = datetime.utcnow().isoformat()
    
    return result
