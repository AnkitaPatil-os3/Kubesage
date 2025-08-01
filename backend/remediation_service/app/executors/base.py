from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional
import logging

logger = logging.getLogger(__name__)

class BaseExecutor(ABC):
    """Base class for all executors"""
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        self.config = config or {}
        self.name = self.__class__.__name__.lower().replace('executor', '')
    
    @abstractmethod
    async def execute_command(self, command: str, **kwargs) -> Dict[str, Any]:
        """Execute a single command"""
        pass
    
    @abstractmethod
    async def execute_remediation_steps(self, steps: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Execute a list of remediation steps"""
        pass
    
    @abstractmethod
    def validate_command(self, command: str) -> bool:
        """Validate if command is safe to execute"""
        pass
    
    def get_executor_info(self) -> Dict[str, Any]:
        """Get executor information"""
        return {
            "name": self.name,
            "type": self.__class__.__name__,
            "config": self.config
        }