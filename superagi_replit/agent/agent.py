"""
Core Agent implementation for SuperAGI.
"""
import json
import os
import time
from typing import List, Dict, Any, Optional, Tuple, Union, cast

from superagi_replit.lib.logger import logger
from superagi_replit.llms.gemini import GeminiProxy
from superagi_replit.tools.base_tool import BaseTool


class Agent:
    """
    Core Agent implementation for SuperAGI.
    
    This class represents an agent that can execute tasks using LLM and tools.
    """
    
    def __init__(self, name: str, description: str, goals: List[str], tools: Optional[List[BaseTool]] = None):
        """
        Initialize the agent.
        
        Args:
            name: Name of the agent
            description: Description of the agent
            goals: List of goals the agent should achieve
            tools: List of tools the agent can use
        """
        self.name = name
        self.description = description
        self.goals = goals
        self.tools = tools if tools is not None else []
        self.llm = GeminiProxy()  # Use Gemini proxy by default
        self.messages = []  # History of messages
        
    def add_tool(self, tool: BaseTool) -> None:
        """Add a tool to the agent."""
        self.tools.append(tool)
        
    def get_available_tools(self) -> List[Dict[str, Any]]:
        """Get the available tools as a list of dictionaries."""
        return [tool.get_tool_config() for tool in self.tools]
        
    def get_system_prompt(self) -> str:
        """Generate the system prompt for the agent."""
        tools_str = json.dumps([tool.get_tool_config() for tool in self.tools], indent=2)
        
        system_prompt = f"""
You are {self.name}, {self.description}
Your goals are:
{chr(10).join(f'- {goal}' for goal in self.goals)}

You have access to the following tools:
{tools_str}

To use a tool, respond with:
```
{{
    "thoughts": "your internal thoughts and reasoning process here",
    "tool": "tool_name",
    "tool_input": {{
        "param1": "value1",
        "param2": "value2"
    }}
}}
```

If you don't need to use a tool, respond with:
```
{{
    "thoughts": "your internal thoughts and reasoning process here",
    "response": "your response to the human"
}}
```

Always include "thoughts" to show your reasoning process. Be thorough in your thoughts but concise in your final responses.
Always try to make progress towards completing your goals.
"""
        return system_prompt
        
    def add_message(self, role: str, content: str) -> None:
        """
        Add a message to the agent's history.
        
        Args:
            role: Role of the message sender (user, assistant, system)
            content: Content of the message
        """
        self.messages.append({"role": role, "content": content})
        
    def get_chat_history(self) -> List[Dict[str, str]]:
        """Get the chat history."""
        return self.messages
        
    def run_tool(self, tool_name: str, tool_input: Dict[str, Any]) -> str:
        """
        Run a tool with the given input.
        
        Args:
            tool_name: Name of the tool to run
            tool_input: Input parameters for the tool
            
        Returns:
            Output of the tool execution
        """
        # Find the tool
        tool = next((t for t in self.tools if t.name == tool_name), None)
        
        if not tool:
            return f"Error: Tool '{tool_name}' not found."
        
        try:
            # Execute the tool with the input parameters
            result = tool.execute(**tool_input)
            return result
        except Exception as e:
            error_msg = f"Error executing tool '{tool_name}': {str(e)}"
            logger.error(error_msg)
            return error_msg
            
    def parse_llm_response(self, response: str) -> Tuple[str, Optional[str], Optional[Dict[str, Any]]]:
        """
        Parse the LLM response to extract thoughts, tool, and tool input.
        
        Args:
            response: Response from the LLM
            
        Returns:
            Tuple of (thoughts, tool_name, tool_input)
        """
        try:
            # Extract the JSON part of the response
            if "```" in response:
                json_str = response.split("```")[1].strip()
                if json_str.startswith("json"):
                    json_str = json_str[4:].strip()
            else:
                json_str = response.strip()
                
            # Parse the JSON
            response_dict = json.loads(json_str)
            
            thoughts = response_dict.get("thoughts", "")
            tool_name = response_dict.get("tool")
            tool_input = response_dict.get("tool_input")
            direct_response = response_dict.get("response")
            
            if tool_name:
                return thoughts, tool_name, tool_input
            else:
                return thoughts, None, direct_response
                
        except Exception as e:
            logger.error(f"Error parsing LLM response: {str(e)}")
            return "Error in parsing response.", None, {"error": f"Failed to parse response: {str(e)}"}
            
    def execute_step(self, user_input: str = None) -> str:
        """
        Execute a single step of the agent.
        
        Args:
            user_input: Optional user input to process
            
        Returns:
            Agent's response
        """
        # Add user input to messages if provided
        if user_input:
            self.add_message("user", user_input)
            
        # Get the system prompt if this is the first message
        if len(self.messages) == 0 or (len(self.messages) == 1 and self.messages[0]["role"] == "user"):
            system_prompt = self.get_system_prompt()
            self.add_message("system", system_prompt)
            
        # Get response from LLM
        try:
            llm_response = self.llm.chat_completion(self.messages)
            
            # Parse the response
            thoughts, tool_name, tool_output = self.parse_llm_response(llm_response)
            
            if tool_name:
                # Run the tool
                tool_result = self.run_tool(tool_name, tool_output)
                
                # Add the tool execution to the history
                self.add_message("assistant", llm_response)
                self.add_message("system", f"Tool {tool_name} result: {tool_result}")
                
                # Execute another step to get the agent's response after the tool execution
                return self.execute_step()
            else:
                # Direct response (no tool needed)
                self.add_message("assistant", llm_response)
                return tool_output  # This is the direct response
                
        except Exception as e:
            error_msg = f"Error in execute_step: {str(e)}"
            logger.error(error_msg)
            return error_msg
            
    def run(self, user_input: str) -> str:
        """
        Run the agent with the given user input.
        
        Args:
            user_input: User input to process
            
        Returns:
            Agent's final response
        """
        return self.execute_step(user_input)