"""
Base Tool class for SuperAGI.
"""
from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional, Type, get_type_hints

from pydantic import BaseModel


class BaseTool(ABC):
    """
    Base class for all tools in SuperAGI.
    
    All tools must extend this class and implement the required methods.
    """
    def __init__(self):
        self.name = ""
        self.description = ""
        # Initialized in child classes
        self.args_schema = None
    
    @abstractmethod
    def execute(self, *args, **kwargs) -> str:
        """
        Execute the tool with the given arguments.
        
        Args:
            *args: Positional arguments
            **kwargs: Keyword arguments
            
        Returns:
            String result of the tool execution
        """
        pass
    
    def get_tool_config(self) -> Dict[str, Any]:
        """
        Get the tool configuration.
        
        Returns:
            Dictionary containing tool configuration
        """
        config = {
            "name": self.name,
            "description": self.description
        }
        
        if hasattr(self, 'args_schema') and self.args_schema:
            config["args_schema"] = self.args_schema.schema()
        
        return config
        
    @classmethod
    def get_tool_schema(cls) -> Dict[str, Any]:
        """
        Get the tool schema.
        
        Returns:
            Dictionary containing tool schema
        """
        instance = cls()
        schema = {
            "name": instance.name,
            "description": instance.description
        }
        
        if hasattr(instance, 'args_schema') and instance.args_schema:
            schema["args_schema"] = instance.args_schema.schema()
            
        return schema