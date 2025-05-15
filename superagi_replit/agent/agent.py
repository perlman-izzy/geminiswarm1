"""
Core Agent implementation for SuperAGI.
"""
import json
import os
import time
from typing import List, Dict, Any, Optional, Tuple, Union, cast

from superagi_replit.agent.non_llm_task_validator import NonLLMTaskValidator
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
        
        # Initialize our non-LLM task completion validator
        self.task_validator = NonLLMTaskValidator()
        
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
            
    def parse_llm_response(self, response: str) -> Tuple[str, Optional[str], Union[Dict[str, Any], str]]:
        """
        Parse the LLM response to extract thoughts, tool, and tool input.
        
        Args:
            response: Response from the LLM
            
        Returns:
            Tuple of (thoughts, tool_name, tool_input_or_response)
            where tool_input_or_response is either a dict (tool input) or str (direct response)
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
            tool_input = response_dict.get("tool_input", {})
            direct_response = response_dict.get("response", "")
            
            if tool_name:
                return thoughts, tool_name, tool_input
            else:
                return thoughts, None, direct_response
                
        except Exception as e:
            logger.error(f"Error parsing LLM response: {str(e)}")
            return "Error in parsing response.", None, f"Failed to parse response: {str(e)}"
            
    def execute_step(self, user_input: Optional[str] = None) -> str:
        """
        Execute a single step of the agent.
        
        Args:
            user_input: Optional user input to process
            
        Returns:
            Agent's response
        """
        # Add user input to messages if provided
        if user_input is not None:
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
            
            if tool_name is not None:
                # Run the tool with the tool input (which should be a dict at this point)
                if isinstance(tool_output, dict):
                    tool_result = self.run_tool(tool_name, tool_output)
                else:
                    # Convert to dict if needed
                    tool_result = self.run_tool(tool_name, {})
                
                # Add the tool execution to the history
                self.add_message("assistant", llm_response)
                self.add_message("system", f"Tool {tool_name} result: {tool_result}")
                
                # Execute another step to get the agent's response after the tool execution
                return self.execute_step()
            else:
                # Direct response (no tool needed)
                self.add_message("assistant", llm_response)
                
                # Convert tool_output to string if it's not already
                if isinstance(tool_output, str):
                    return tool_output  # This is the direct response
                else:
                    return str(tool_output)
                
        except Exception as e:
            error_msg = f"Error in execute_step: {str(e)}"
            logger.error(error_msg)
            return error_msg
            
    def run(self, user_input: str, max_iterations: int = 10) -> str:
        """
        Run the agent with the given user input, using non-LLM validation for task completion.
        
        Args:
            user_input: User input to process
            max_iterations: Maximum number of iterations to run
            
        Returns:
            Agent's final response
        """
        # Reset state for a new run
        if not self.messages:
            self.messages = []
            self.task_validator.reset()
            
        # Add initial user input
        self.add_message("user", user_input)
        
        # Run agent until completion or max iterations
        iteration = 0
        final_response = None
        tool_used = None
        tool_args = None
        
        # Log the start of execution
        task_description = " ".join(self.goals) + " " + user_input
        logger.info(f"Starting agent execution with task: {task_description}")
        logger.info(f"Maximum iterations: {max_iterations}")
        
        while iteration < max_iterations:
            # Execute a step and get the response
            response = self.execute_step()
            final_response = response  # Update the final response
            
            # Update the validator with the latest response and tool information
            self.task_validator.update_metrics(
                latest_response=response,
                used_tool=tool_used,
                tool_args=tool_args
            )
            
            # Reset tool information for next iteration
            tool_used = None
            tool_args = None
            
            # Check if the task is complete using our non-LLM validator
            is_complete, reason, confidence = self.task_validator.is_task_complete(
                task_description=task_description,
                max_iterations=max_iterations
            )
            
            # Log progress
            iteration += 1
            status = self.task_validator.get_status_report()
            logger.info(f"Completed iteration {iteration}/{max_iterations}")
            logger.info(f"Task status: information_patterns={status['information_patterns']}, tool_usages={status['tool_usages']}")
            
            if is_complete:
                logger.info(f"Task complete: {reason} (confidence: {confidence:.2f})")
                
                # If we have a low confidence completion but still have iterations left,
                # ask for a final summary to ensure completeness
                if confidence < 0.8 and iteration < max_iterations - 1:
                    logger.info("Low confidence completion, requesting final summary")
                    summary_prompt = f"Provide a final summary of all the information gathered for the user's question: '{user_input}'"
                    self.add_message("system", summary_prompt)
                    final_summary = self.execute_step()
                    return final_summary
                    
                return final_response
                
            # Parse response to see if a tool was used for the next iteration
            try:
                if "```" in response and ('"tool":' in response or "'tool':" in response):
                    # Extract the JSON part
                    json_part = response.split("```")[1].strip()
                    if json_part.startswith("json"):
                        json_part = json_part[4:].strip()
                        
                    data = json.loads(json_part)
                    if "tool" in data:
                        tool_used = data["tool"]
                        tool_args = data.get("tool_input", {})
            except Exception as e:
                logger.warning(f"Error parsing tool usage: {str(e)}")
        
        # If we reach max iterations without completion
        logger.info(f"Reached maximum iterations ({max_iterations}) without completion")
        
        # Generate a final summary if we hit the limit
        if final_response is not None:
            logger.info("Generating final summary after reaching iteration limit")
            summary_prompt = f"Provide a concise summary of all findings for the user's question: '{user_input}'"
            self.add_message("system", summary_prompt)
            final_summary = self.execute_step()
            return final_summary
            
        return final_response if final_response is not None else "The task could not be completed within the allotted iterations."