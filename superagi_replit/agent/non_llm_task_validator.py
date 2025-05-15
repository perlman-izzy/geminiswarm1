"""
Non-LLM Task Completion Validator for SuperAGI.

This module provides evaluation methods for determining task completion
without relying on the LLM's self-assessment. It uses metrics, patterns,
and heuristics to determine objectively when a task is complete.
"""
import re
import time
from typing import List, Dict, Any, Tuple, Set, Optional


class NonLLMTaskValidator:
    """
    Evaluates task completion using non-LLM methods to avoid
    the agent marking its own work as complete.
    """
    
    def __init__(self):
        """Initialize the task validator."""
        self.iteration_count = 0
        self.response_history = []
        self.tool_uses = {}
        self.last_activity_time = time.time()
        self.informational_patterns = {}
        self.repetition_count = 0
        self.task_specific_metrics = {}
        
    def reset(self):
        """Reset the validator state."""
        self.__init__()
        
    def update_metrics(self, 
                     latest_response: str, 
                     used_tool: Optional[str] = None,
                     tool_args: Optional[Dict[str, Any]] = None) -> None:
        """
        Update metrics based on the latest response and tool usage.
        
        Args:
            latest_response: The latest response from the agent
            used_tool: The name of the tool used, if any
            tool_args: The arguments passed to the tool, if any
        """
        # Track iteration count
        self.iteration_count += 1
        
        # Store response for analysis
        self.response_history.append(latest_response)
        
        # Update tool usage counts
        if used_tool:
            self.tool_uses[used_tool] = self.tool_uses.get(used_tool, 0) + 1
            
        # Update last activity time
        self.last_activity_time = time.time()
        
        # Check for repetition with previous response
        if len(self.response_history) >= 2:
            similarity = self._calculate_similarity(
                self.response_history[-1], 
                self.response_history[-2]
            )
            if similarity > 0.7:  # High similarity threshold
                self.repetition_count += 1
            else:
                self.repetition_count = 0
                
        # Update informational patterns (facts, data points, etc.)
        self._extract_information_patterns(latest_response)
        
    def is_task_complete(self, 
                        task_description: str,
                        max_iterations: int = 15,
                        timeout_seconds: int = 300) -> Tuple[bool, str, float]:
        """
        Determine if the task is complete based on objective metrics.
        
        Args:
            task_description: The original task description
            max_iterations: Maximum number of iterations before forced completion
            timeout_seconds: Maximum seconds of inactivity before timeout
            
        Returns:
            Tuple of (is_complete, reason, confidence)
        """
        # Check for maximum iterations
        if self.iteration_count >= max_iterations:
            return True, f"Maximum iterations reached ({max_iterations})", 1.0
            
        # Check for timeout
        elapsed = time.time() - self.last_activity_time
        if elapsed > timeout_seconds:
            return True, f"Task timed out after {elapsed:.1f} seconds of inactivity", 0.9
            
        # Check for consecutive repetitive responses
        if self.repetition_count >= 3:
            return True, "Task converged (3+ consecutive similar responses)", 0.85
            
        # Check for explicit completion markers in the latest response
        latest_response = self.response_history[-1] if self.response_history else ""
        completion_markers = self._extract_completion_markers(latest_response)
        if completion_markers:
            marker = completion_markers[0]  # Use the first found marker
            return True, f"Completion marker found: '{marker}'", 0.9
        
        # Detect task type
        task_type = self._detect_task_type(task_description)
        
        # Check for task-specific completion criteria based on task type
        if task_type == "list":
            # For list tasks, check if we have a substantial list
            list_count = self._count_list_items()
            required_items = 10  # Default
            
            # Check if a specific number is mentioned in the task
            number_match = re.search(r"\b(\d+)\b", task_description)
            if number_match:
                required_items = int(number_match.group(1))
                
            if list_count >= required_items:
                return True, f"List task complete with {list_count} items (needed {required_items})", 0.9
                
        elif task_type == "venue":
            # For venue search, check if we have a substantial list of locations
            venue_keywords = ["venue", "club", "bar", "location", "place", "restaurant", "address"]
            combined_text = " ".join(self.response_history).lower()
            
            # Count occurrence of venue keywords
            venue_mentions = sum(combined_text.count(keyword) for keyword in venue_keywords)
            
            # Count addresses (simplified pattern)
            addresses = len(re.findall(r"\d+\s+[A-Za-z]+\s+(?:St|Ave|Blvd|Road|Rd|Street|Avenue)", combined_text, re.IGNORECASE))
            
            list_count = self._count_list_items()
            
            if list_count >= 5 and addresses >= 3:
                return True, f"Venue search complete with {list_count} listings and {addresses} addresses", 0.9
                
        elif task_type == "email":
            # For email tasks, look for email addresses
            email_count = 0
            for response in self.response_history:
                emails = re.findall(r"[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+", response)
                email_count += len(emails)
                
            required_count = 10  # Default
            number_match = re.search(r"\b(\d+)\b", task_description)
            if number_match:
                required_count = int(number_match.group(1))
                
            if email_count >= required_count:
                return True, f"Email task complete with {email_count} email addresses found", 0.95
                
        elif task_type == "facility":
            # For facility search (like restrooms), check for specific details
            combined_text = " ".join(self.response_history).lower()
            
            # Check for details like addresses, ratings, specific locations
            has_address = re.search(r"\d+\s+[A-Za-z]+\s+(?:St|Ave|Blvd|Road|Rd|Street|Avenue)", combined_text, re.IGNORECASE) is not None
            has_rating = any(word in combined_text for word in ["clean", "cleanest", "rating", "review", "stars", "score"])
            
            if has_address and has_rating and self.iteration_count >= 5:
                return True, f"Facility search complete with specific location and quality details", 0.85
            
        # Calculate information gathering sufficiency
        info_coverage = self._calculate_information_coverage(task_description)
        if info_coverage > 0.8:  # High information coverage
            return True, f"High information coverage achieved ({info_coverage:.2f})", 0.8
        
        # Default: task is not complete
        return False, "Task in progress", max(0.1, info_coverage)
        
    def _detect_task_type(self, task_description: str) -> str:
        """Detect the type of task from the description."""
        task_lower = task_description.lower()
        
        # Check for list task
        if "list" in task_lower or any(word in task_lower for word in ["find all", "find me", "gather", "collect"]):
            return "list"
            
        # Check for venue search
        if any(word in task_lower for word in ["venue", "club", "bar", "restaurant", "hotel", "location"]):
            return "venue"
            
        # Check for email search
        if "email" in task_lower or "@" in task_lower:
            return "email"
            
        # Check for facility search
        if any(word in task_lower for word in ["restroom", "bathroom", "toilet", "facility"]):
            return "facility"
            
        # Default type
        return "general"
        
    def _count_list_items(self) -> int:
        """Count list items across recent responses."""
        list_count = 0
        for response in self.response_history:
            # Count numbered items
            list_count += len(re.findall(r"^\s*\d+\.\s", response, re.MULTILINE))
            
            # Count bulleted items
            list_count += len(re.findall(r"^\s*[\*\-•]\s", response, re.MULTILINE))
            
        return list_count
        
    def _extract_completion_markers(self, text: str) -> List[str]:
        """Extract completion marker phrases from text."""
        markers = [
            "task complete", "completed the task", "finished the task",
            "goal achieved", "goals accomplished", "mission accomplished",
            "all objectives met", "research complete", "analysis complete",
            "completed successfully", "here is the final", "in conclusion"
        ]
        
        found_markers = []
        for marker in markers:
            if marker in text.lower():
                found_markers.append(marker)
                
        return found_markers
        
    def _has_substantial_list(self, text: str) -> bool:
        """Check if the text contains a substantial numbered list."""
        list_items = re.findall(r"^\d+\.", text, re.MULTILINE)
        return len(list_items) >= 5  # Require at least 5 items for a substantial list
        
    def _extract_information_patterns(self, text: str) -> None:
        """Extract factual information patterns from text."""
        # Extract dates
        dates = set(re.findall(r"\b\d{4}[-/]\d{1,2}[-/]\d{1,2}\b", text))
        self.informational_patterns["dates"] = self.informational_patterns.get("dates", set()).union(dates)
        
        # Extract percentages
        percentages = set(re.findall(r"\b\d+(\.\d+)?%\b", text))
        self.informational_patterns["percentages"] = self.informational_patterns.get("percentages", set()).union(percentages)
        
        # Extract proper nouns (simplified approach)
        proper_nouns = set(re.findall(r"\b[A-Z][a-z]+(?:\s+[A-Z][a-z]+)*\b", text))
        self.informational_patterns["proper_nouns"] = self.informational_patterns.get("proper_nouns", set()).union(proper_nouns)
        
        # Extract URLs
        urls = set(re.findall(r"https?://[^\s]+", text))
        self.informational_patterns["urls"] = self.informational_patterns.get("urls", set()).union(urls)
        
    def _calculate_information_coverage(self, task_description: str) -> float:
        """
        Calculate how well the gathered information covers the task.
        This is a proxy for task completion.
        """
        # Extract keywords from task description
        keywords = set(re.findall(r"\b[a-zA-Z]{4,}\b", task_description.lower()))
        
        # Count information patterns as a proxy for thoroughness
        pattern_counts = sum(len(items) for items in self.informational_patterns.values())
        
        # Combine recent responses for keyword checking
        recent_text = " ".join(self.response_history[-3:] if len(self.response_history) >= 3 else self.response_history).lower()
        
        # Count keywords from task that appear in recent responses
        keyword_matches = sum(1 for kw in keywords if kw in recent_text)
        keyword_coverage = keyword_matches / max(1, len(keywords))
        
        # Special handling for list-based tasks
        list_items_count = 0
        for response in self.response_history[-3:] if len(self.response_history) >= 3 else self.response_history:
            # Count numbered list items
            list_items = re.findall(r"^\s*\d+\.\s", response, re.MULTILINE)
            list_items_count += len(list_items)
            
            # Count bulleted list items
            bulleted_items = re.findall(r"^\s*[\*\-•]\s", response, re.MULTILINE)
            list_items_count += len(bulleted_items)
            
        list_bonus = min(1.0, list_items_count / 10.0)  # Bonus for having substantial lists (10+ items is max)
        
        # Check for presence of specific entities related to task
        entity_types = {
            "venue": ["venue", "club", "bar", "restaurant", "hotel", "location", "address"],
            "contact": ["email", "contact", "phone", "number", "@"],
            "facility": ["restroom", "bathroom", "toilet", "facility"]
        }
        
        task_type = None
        for entity_type, keywords in entity_types.items():
            if any(keyword in task_description.lower() for keyword in keywords):
                task_type = entity_type
                break
                
        entity_bonus = 0.0
        if task_type:
            entity_matches = sum(1 for keyword in entity_types[task_type] if keyword in recent_text)
            entity_bonus = min(1.0, entity_matches / len(entity_types[task_type]))
        
        # More tools used suggests more thorough research
        tools_diversity = len(self.tool_uses) / 3.0  # Normalize by assuming 3 tools is comprehensive
        tool_usage_count = sum(self.tool_uses.values())
        tool_usage_bonus = min(1.0, tool_usage_count / 5.0)  # Bonus for using tools multiple times
        
        # Combine metrics with appropriate weights
        coverage = (
            (0.3 * keyword_coverage) +
            (0.2 * min(1.0, pattern_counts / 20)) +  # Cap at 20 information patterns
            (0.2 * min(1.0, tools_diversity)) +
            (0.1 * tool_usage_bonus) +
            (0.1 * list_bonus) +
            (0.1 * entity_bonus)
        )
        
        # Check if the response is in a good final format
        has_conclusion = any(marker in recent_text for marker in ["conclusion", "summary", "in summary"])
        if has_conclusion:
            coverage += 0.1  # Bonus for having a conclusion
            
        return min(1.0, coverage)  # Ensure maximum of 1.0
        
    def _calculate_similarity(self, text1: str, text2: str) -> float:
        """Calculate similarity between two text strings."""
        # Convert to word sets for Jaccard similarity
        words1 = set(re.findall(r"\b[a-zA-Z]{3,}\b", text1.lower()))
        words2 = set(re.findall(r"\b[a-zA-Z]{3,}\b", text2.lower()))
        
        # Calculate Jaccard similarity (intersection over union)
        intersection = len(words1.intersection(words2))
        union = len(words1.union(words2))
        
        return intersection / max(1, union)
        
    def get_status_report(self) -> Dict[str, Any]:
        """Get a detailed status report of current metrics."""
        return {
            "iteration_count": self.iteration_count,
            "response_count": len(self.response_history),
            "tool_usages": self.tool_uses,
            "repetition_count": self.repetition_count,
            "information_patterns": {k: len(v) for k, v in self.informational_patterns.items()},
            "elapsed_since_last_activity": time.time() - self.last_activity_time,
        }