import subprocess
import json
import asyncio
from typing import List, Dict, Any
from app.executors.base import BaseExecutor
from app.logger import logger

class ArgoCDExecutor(BaseExecutor):
    """ArgoCD executor for GitOps operations"""
    
    def __init__(self, config: Dict[str, Any] = None):
        super().__init__(config)
        self.server = self.config.get('server', 'localhost:8080')
        self.username = self.config.get('username', 'admin')
        self.password = self.config.get('password', '')
        self.token = self.config.get('token', '')
        
        # Safe ArgoCD commands
        self.safe_commands = [
            'app', 'proj', 'cluster', 'repo', 'account',
            'version', 'context'
        ]
        
        # ArgoCD app operations
        self.app_operations = [
            'get', 'list', 'create', 'delete', 'sync', 'history',
            'rollback', 'set', 'unset', 'patch', 'edit', 'logs',
            'wait', 'manifests', 'terminate-op', 'actions'
        ]
    
    def validate_command(self, command: str) -> bool:
        """Validate if ArgoCD command is safe to execute"""
        try:
            parts = command.split()
            if not parts or parts[0] != 'argocd':
                return False
            
            if len(parts) < 2:
                return False
            
            argocd_resource = parts[1]
            
            # Check if resource type is safe
            if argocd_resource in self.safe_commands:
                return True
            
            return False
        except Exception as e:
            logger.error(f"Error validating ArgoCD command: {str(e)}")
            return False
    
    async def execute_command(self, command: str, **kwargs) -> Dict[str, Any]:
        """Execute an ArgoCD command"""
        try:
            if not self.validate_command(command):
                return {
                    "success": False,
                    "error": "Invalid or unsafe ArgoCD command",
                    "command": command
                }
            
            # Add server and auth info if not present
            if '--server' not in command and self.server:
                command += f" --server {self.server}"
            
            if self.token and '--auth-token' not in command:
                command += f" --auth-token {self.token}"
            elif self.username and self.password and '--username' not in command:
                command += f" --username {self.username} --password {self.password}"
            
            # Add insecure flag for development
            if '--insecure' not in command:
                command += " --insecure"
            
            logger.info(f"Executing ArgoCD command: {command}")
            
            # Execute command asynchronously
            process = await asyncio.create_subprocess_shell(
                command,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            
            stdout, stderr = await process.communicate()
            
            result = {
                "success": process.returncode == 0,
                "command": command,
                "return_code": process.returncode,
                "stdout": stdout.decode('utf-8') if stdout else "",
                "stderr": stderr.decode('utf-8') if stderr else ""
            }
            
            # Try to parse JSON output if possible
            if result["success"] and result["stdout"]:
                try:
                    if '-o json' in command or '--output json' in command:
                        result["json_output"] = json.loads(result["stdout"])
                except json.JSONDecodeError:
                    pass
            
            return result
            
        except Exception as e:
            logger.error(f"Error executing ArgoCD command: {str(e)}")
            return {
                "success": False,
                "error": str(e),
                "command": command
            }
    
    async def execute_remediation_steps(self, steps: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Execute a list of ArgoCD remediation steps"""
        results = []
        
        for i, step in enumerate(steps):
            try:
                step_id = step.get('step_id', i + 1)
                command = step.get('command', '')
                description = step.get('description', '')
                
                logger.info(f"Executing ArgoCD step {step_id}: {description}")
                
                if not command:
                    results.append({
                        "step_id": step_id,
                        "success": False,
                        "error": "No command provided for step",
                        "description": description
                    })
                    continue
                
                # Execute the command
                result = await self.execute_command(command)
                result.update({
                    "step_id": step_id,
                    "description": description,
                    "expected_outcome": step.get('expected_outcome', '')
                })
                
                results.append(result)
                
                # If step failed and it's critical, stop execution
                if not result["success"] and step.get('critical', False):
                    logger.error(f"Critical ArgoCD step {step_id} failed, stopping execution")
                    break
                    
            except Exception as e:
                logger.error(f"Error executing ArgoCD step {i + 1}: {str(e)}")
                results.append({
                    "step_id": step.get('step_id', i + 1),
                    "success": False,
                    "error": str(e),
                    "description": step.get('description', '')
                })
        
        return results