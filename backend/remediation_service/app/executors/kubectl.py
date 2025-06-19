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
        self.kubeconfig_path = self.config.get('kubeconfig_path', '~/.kube/config')
        self.namespace = self.config.get('namespace', 'default')
        
        # Safe kubectl commands
        self.safe_commands = [
            'get', 'describe', 'logs', 'top', 'explain',
            'scale', 'rollout', 'patch', 'annotate', 'label',
            'create', 'apply', 'replace', 'restart'
        ]
        
        # Dangerous commands that require extra validation
        self.dangerous_commands = ['delete', 'drain', 'cordon', 'uncordon']
    
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
        """Execute a kubectl command"""
        try:
            if not self.validate_command(command):
                return {
                    "success": False,
                    "error": "Invalid or unsafe kubectl command",
                    "command": command
                }
            
            # CHANGE: Handle compound commands with && operator
            if '&&' in command:
                # Split commands by && and execute them sequentially
                commands = [cmd.strip() for cmd in command.split('&&')]
                all_stdout = []
                all_stderr = []
                
                for cmd in commands:
                    # Add kubeconfig if not present
                    if '--kubeconfig' not in cmd and self.kubeconfig_path:
                        cmd += f" --kubeconfig {self.kubeconfig_path}"
                    
                    # Add namespace if not present and not a cluster-wide command
                    if '-n ' not in cmd and '--namespace' not in cmd and '--all-namespaces' not in cmd:
                        if any(subcmd in cmd for subcmd in ['get', 'describe', 'logs', 'delete', 'create', 'apply']):
                            cmd += f" -n {self.namespace}"
                    
                    logger.info(f"Executing kubectl command: {cmd}")
                    
                    # Execute individual command
                    process = await asyncio.create_subprocess_shell(
                        cmd,
                        stdout=asyncio.subprocess.PIPE,
                        stderr=asyncio.subprocess.PIPE
                    )
                    
                    stdout, stderr = await process.communicate()
                    
                    # If any command fails, return failure
                    if process.returncode != 0:
                        return {
                            "success": False,
                            "command": command,
                            "return_code": process.returncode,
                            "stdout": "\n".join(all_stdout) + stdout.decode('utf-8') if stdout else "\n".join(all_stdout),
                            "stderr": "\n".join(all_stderr) + stderr.decode('utf-8') if stderr else "\n".join(all_stderr)
                        }
                    
                    # Collect outputs
                    if stdout:
                        all_stdout.append(stdout.decode('utf-8'))
                    if stderr:
                        all_stderr.append(stderr.decode('utf-8'))
                
                # All commands succeeded
                result = {
                    "success": True,
                    "command": command,
                    "return_code": 0,
                    "stdout": "\n".join(all_stdout),
                    "stderr": "\n".join(all_stderr)
                }
                
            else:
                # EXISTING LOGIC: Single command execution
                # Add kubeconfig if not present
                if '--kubeconfig' not in command and self.kubeconfig_path:
                    command += f" --kubeconfig {self.kubeconfig_path}"
                
                # Add namespace if not present and not a cluster-wide command
                if '-n ' not in command and '--namespace' not in command and '--all-namespaces' not in command:
                    if any(cmd in command for cmd in ['get', 'describe', 'logs', 'delete', 'create', 'apply']):
                        command += f" -n {self.namespace}"
                
                logger.info(f"Executing kubectl command: {command}")
                
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
                    if '-o json' in command or '--output=json' in command:
                        result["json_output"] = json.loads(result["stdout"])
                except json.JSONDecodeError:
                    pass

            return result
            
        except Exception as e:
            logger.error(f"Error executing kubectl command: {str(e)}")
            return {
                "success": False,
                "error": str(e),
                "command": command
            }



    async def execute_remediation_steps(self, steps: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Execute a list of remediation steps"""
        results = []
        
        for i, step in enumerate(steps):
            try:
                step_id = step.get('step_id', i + 1)
                command = step.get('command', '')
                description = step.get('description', '')
                
                logger.info(f"Executing step {step_id}: {description}")
                
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
                    logger.error(f"Critical step {step_id} failed, stopping execution")
                    break
                    
            except Exception as e:
                logger.error(f"Error executing step {i + 1}: {str(e)}")
                results.append({
                    "step_id": step.get('step_id', i + 1),
                    "success": False,
                    "error": str(e),
                    "description": step.get('description', '')
                })
        
        return results