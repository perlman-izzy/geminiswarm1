"""
A direct agent implementation that uses a mock LLM.
This allows testing of task completion in a real-world flow without external dependencies.
"""
import json
import time
import re
from typing import List, Dict, Any, Optional, Tuple, Union

from superagi_replit.agent.non_llm_task_validator import NonLLMTaskValidator
from superagi_replit.agent.mock_llm import MockLLM
from superagi_replit.lib.logger import logger
from superagi_replit.tools.base_tool import BaseTool


class DirectAgent:
    """
    Agent implementation that uses a mock LLM for testing task completion.
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
        self.llm = MockLLM()  # Use MockLLM
        self.messages = []  # History of messages
        
        # Initialize our non-LLM task completion validator
        self.task_validator = NonLLMTaskValidator()
        
    def add_tool(self, tool: BaseTool) -> None:
        """Add a tool to the agent."""
        self.tools.append(tool)
        
    def get_available_tools(self) -> List[Dict[str, Any]]:
        """Get the available tools as a list of dictionaries."""
        return [tool.get_tool_config() for tool in self.tools]
        
    def add_message(self, role: str, content: str) -> None:
        """
        Add a message to the agent's history.
        
        Args:
            role: Role of the message sender (user, assistant, system)
            content: Content of the message
        """
        self.messages.append({"role": role, "content": content})
        
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
            
    def parse_llm_response(self, response: str) -> Tuple[str, Optional[str], Dict[str, Any]]:
        """
        Parse the LLM response to extract tool usage.
        
        Args:
            response: Response from the LLM
            
        Returns:
            Tuple of (thoughts, tool_name, tool_input)
        """
        # Extract tool usage with a regex pattern
        tool_pattern = r'```\s*{\s*"tool":\s*"([^"]+)",\s*"tool_input":\s*({[^}]+})'
        match = re.search(tool_pattern, response, re.DOTALL)
        
        if match:
            tool_name = match.group(1)
            tool_input_str = match.group(2)
            
            # Clean up the JSON string
            tool_input_str = tool_input_str.replace("'", '"')
            try:
                tool_args = json.loads(tool_input_str)
                return "", tool_name, tool_args
            except json.JSONDecodeError:
                pass
                
        return "", None, {}
            
    def run(self, user_input: str, max_iterations: int = 10) -> Dict[str, Any]:
        """
        Run the agent with the given user input.
        
        Args:
            user_input: User input to process
            max_iterations: Maximum number of iterations to run
            
        Returns:
            Dictionary with results and metrics
        """
        # Reset state
        self.messages = []
        self.task_validator.reset()
        
        # Log the start of execution
        task_description = " ".join(self.goals) + " " + user_input
        logger.info(f"Starting direct agent execution with task: {task_description}")
        logger.info(f"Maximum iterations: {max_iterations}")
        
        iteration = 0
        responses = []
        final_response = None
        tool_used = None
        tool_args = None
        tool_uses = {}
        start_time = time.time()
        
        while iteration < max_iterations:
            # Generate a response using the mock LLM
            if iteration == 0:
                prompt = user_input
            else:
                # In a real agent, previous responses would influence the next prompt
                prompt = f"{user_input}\n\nConsider what you've found so far and continue the search."
                
            response = self.llm.generate(prompt)
            responses.append(response)
            
            # Extract tool usage from the response
            _, tool_name, tool_args = self.parse_llm_response(response)
            
            if tool_name:
                tool_uses[tool_name] = tool_uses.get(tool_name, 0) + 1
                self.task_validator.update_metrics(response, tool_name, tool_args)
                
                # Simulate running the tool (in this test we don't actually execute it)
                logger.info(f"Simulating tool execution: {tool_name} with args: {tool_args}")
            else:
                self.task_validator.update_metrics(response)
            
            # Update final response
            final_response = response
            
            # Check if task is complete
            is_complete, reason, confidence = self.task_validator.is_task_complete(task_description)
            
            # Log progress
            iteration += 1
            status = self.task_validator.get_status_report()
            logger.info(f"Completed iteration {iteration}/{max_iterations}")
            logger.info(f"Task status: Complete: {is_complete}, Reason: {reason}, Confidence: {confidence:.2f}")
            logger.info(f"Status report: information_patterns={status['information_patterns']}, tool_usages={status['tool_usages']}")
            
            if is_complete:
                logger.info(f"Task complete: {reason} (confidence: {confidence:.2f})")
                break
        
        end_time = time.time()
        execution_time = end_time - start_time
        
        # Compile results
        result = {
            "task": user_input,
            "goals": self.goals,
            "completed": is_complete,
            "reason": reason,
            "confidence": confidence,
            "iterations": iteration,
            "max_iterations": max_iterations,
            "execution_time": execution_time,
            "tool_uses": tool_uses,
            "responses": responses,
            "final_response": final_response,
            "status_report": self.task_validator.get_status_report()
        }
        
        return result