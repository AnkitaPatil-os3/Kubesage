import subprocess
import json
import asyncio
from typing import List, Dict, Any
from app.executors.base import BaseExecutor
from app.logger import logger

class CrossplaneExecutor(BaseExecutor):
    """Crossplane executor for infrastructure operations"""
    
    def __init__(self, config: Dict[str, Any] = None):
        super().__init__(config)
        self.kubeconfig_path = self.config.get('kubeconfig_path', '~/.kube/config')
        self.namespace = self.config.get('namespace', 'crossplane-system')
        
        # Safe Crossplane operations (using kubectl for Crossplane resources)
        self.safe_operations = [
            'get', 'describe', 'logs', 'explain',
            'patch', 'annotate', 'label', 'apply'
        ]
        
        # Crossplane resource types
        self.crossplane_resources = [
            'compositions', 'compositeresourcedefinitions', 'providers',
            'providerconfigs', 'compositeresources', 'claims',
            'functions', 'environmentconfigs'
        ]
    
    def validate_command(self, command: str) -> bool:
        """Validate if Crossplane command is safe to execute"""
        try:
            parts = command.split()
            if not parts:
                return False
            
            # Crossplane operations are typically kubectl commands on Crossplane resources
            if parts[0] == 'kubectl':
                if len(parts) < 2:
                    return False
                
                kubectl_operation = parts[1]
                
                # Check if operation is safe
                if kubectl_operation in self.safe_operations:
                    return True
                
                # Special handling for Crossplane-specific operations
                if kubectl_operation == 'create' or kubectl_operation == 'apply':
                    # Allow create/apply for Crossplane resources
                    return True
            
            # Direct crossplane CLI commands
            elif parts[0] == 'crossplane':
                return True
            
            return False
        except Exception as e:
            logger.error(f"Error validating Crossplane command: {str(e)}")
            return False
    
    async def execute_command(self, command: str, **kwargs) -> Dict[str, Any]:
        """Execute a Crossplane command"""
        try:
            if not self.validate_command(command):
                return {
                    "success": False,
                    "error": "Invalid or unsafe Crossplane command",
                    "command": command
                }
            
            # Add kubeconfig if kubectl command and not present
            if command.startswith('kubectl') and '--kubeconfig' not in command and self.kubeconfig_path:
                command += f" --kubeconfig {self.kubeconfig_path}"
            
            # Add namespace for namespaced resources
            if command.startswith('kubectl') and '-n ' not in command and '--namespace' not in command:
                if any(op in command for op in ['get', 'describe', 'logs', 'delete', 'create', 'apply']):
                    # Check if it's a Crossplane system resource
                    if any(resource in command for resource in ['providers', 'compositions']):
                        command += f" -n {self.namespace}"
            
            logger.info(f"Executing Crossplane command: {command}")
            
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
            logger.error(f"Error executing Crossplane command: {str(e)}")
            return {
                "success": False,
                "error": str(e),
                "command": command
            }
    
    async def execute_remediation_steps(self, steps: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Execute a list of Crossplane remediation steps"""
        results = []
        
        for i, step in enumerate(steps):
            try:
                step_id = step.get('step_id', i + 1)
                command = step.get('command', '')
                description = step.get('description', '')
                
                logger.info(f"Executing Crossplane step {step_id}: {description}")
                
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
                    logger.error(f"Critical Crossplane step {step_id} failed, stopping execution")
                    break
                    
            except Exception as e:
                logger.error(f"Error executing Crossplane step {i + 1}: {str(e)}")
                results.append({
                    "step_id": step.get('step_id', i + 1),
                    "success": False,
                    "error": str(e),
                    "description": step.get('description', '')
                })
        
        return results