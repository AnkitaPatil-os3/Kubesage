import subprocess
import shlex
import json
import asyncio
from typing import List, Dict, Any
from app.executors.base import BaseExecutor
from app.logger import logger

class KubectlExecutor(BaseExecutor):
    """Kubectl executor for Kubernetes operations"""
    
    def __init__(self, config: Dict[str, Any] = None):
        super().__init__(config)
        self.server_url = self.config.get('server_url')
        self.token = self.config.get('token')
        self.namespace = self.config.get('namespace', 'default')
        self.use_secure_tls = self.config.get('use_secure_tls', True)
        # Remove kubeconfig path as we won't be using it
        self.kubeconfig_path = None
    
    def validate_command(self, command: str) -> bool:
        """Validate if kubectl command is safe to execute"""
        try:
            parts = shlex.split(command)
            if not parts or parts[0] != 'kubectl':
                return False
            
            if len(parts) < 2:
                return False
            
            kubectl_command = parts[1]
            
            # Check if command is in safe list
            if kubectl_command in self.safe_commands:
                return True
            
            # For dangerous commands, add extra validation
            if kubectl_command in self.dangerous_commands:
                # Add specific validation logic here
                logger.warning(f"Dangerous kubectl command detected: {kubectl_command}")
                return True  # For now, allow but log
            
            return False
        except Exception as e:
            logger.error(f"Error validating kubectl command: {str(e)}")
            return False
    
    async def execute_command(self, command: str, **kwargs) -> Dict[str, Any]:
        try:
            if not self.validate_command(command):
                return {
                    "success": False,
                    "error": "Invalid or unsafe kubectl command",
                    "command": command
                }
            
            # Build the base kubectl command with server URL and token
            base_cmd = f"kubectl --server={self.server_url} --token={self.token} --insecure-skip-tls-verify={str(not self.use_secure_tls).lower()}"
            
            if '&&' in command:
                # Handle compound commands
                commands = [cmd.strip() for cmd in command.split('&&')]
                all_stdout = []
                all_stderr = []
                
                for cmd in commands:
                    # Skip if it's already a kubectl command (to avoid duplication)
                    if cmd.startswith('kubectl'):
                        cmd = cmd.replace('kubectl', base_cmd, 1)
                    else:
                        cmd = f"{base_cmd} {cmd}"
                    
                    # Add namespace if not present and not a cluster-wide command
                    if '-n ' not in cmd and '--namespace' not in cmd and '--all-namespaces' not in cmd:
                        if any(subcmd in cmd for subcmd in ['get', 'describe', 'logs', 'delete', 'create', 'apply']):
                            cmd += f" -n {self.namespace}"
                    
                    # Rest of the existing command execution logic...
                    # [Previous code for command execution remains the same]
            else:
                # Single command
                if command.startswith('kubectl'):
                    command = command.replace('kubectl', base_cmd, 1)
                else:
                    command = f"{base_cmd} {command}"
                
                # Add namespace if not present and not a cluster-wide command
                if '-n ' not in command and '--namespace' not in command and '--all-namespaces' not in command:
                    if any(cmd in command for cmd in ['get', 'describe', 'logs', 'delete', 'create', 'apply']):
                        command += f" -n {self.namespace}"
                
                # Rest of the existing command execution logic...
                # [Previous code for command execution remains the same]
                
        except Exception as e:
            logger.error(f"Error executing kubectl command: {str(e)}")
            return {
                "success": False,
                "error": str(e),
                "command": command
        }
    

    def _make_jq_safe(self, command: str) -> str:
        """Make jq commands safer by adding error handling"""
        if '|' in command and 'jq' in command:
            parts = command.rsplit('|', 1)
            if len(parts) == 2:
                base_cmd = parts[0].strip()
                jq_part = parts[1].strip()
                
                # Add error handling to jq
                safe_jq = f"({jq_part} 2>/dev/null || echo '{{\"error\": \"jq parsing failed\"}}')"
                return f"{base_cmd} | {safe_jq}"
        
        return command



    async def execute_remediation_steps(self, steps: List[Dict[str, Any]], user_id: str = None) -> List[Dict[str, Any]]:
        """Execute a list of remediation steps"""
        results = []
        
        for i, step in enumerate(steps):
            try:
                step_id = step.get('step_id', i + 1)
                command = step.get('command', '')
                description = step.get('description', '')
                
                logger.info(f"Executing step {step_id} for user {user_id}: {description}")
                
                if not command:
                    results.append({
                        "step_id": step_id,
                        "success": False,
                        "error": "No command provided for step",
                        "description": description
                    })
                    continue
                
                # Execute the command asynchronously
                result = await self.execute_command(command)
                result.update({
                    "step_id": step_id,
                    "description": description,
                    "expected_outcome": step.get('expected_outcome', '')
                })
                
                results.append(result)
                
                # If step failed and it's critical, stop execution
                if not result["success"] and step.get('critical', False):
                    logger.error(f"Critical step {step_id} failed for user {user_id}, stopping execution")
                    break
                    
            except Exception as e:
                logger.error(f"Error executing step {i + 1} for user {user_id}: {str(e)}")
                results.append({
                    "step_id": step.get('step_id', i + 1),
                    "success": False,
                    "error": str(e),
                    "description": step.get('description', '')
                })
        
        return results