"""
Task Completion Evaluator for SuperAGI

This module provides functions to determine if a task has been completed successfully,
is making progress, or should be terminated.
"""
import re
from typing import Dict, List, Any, Tuple

from superagi_replit.lib.logger import logger


class TaskEvaluator:
    """Evaluates task completion and determines when to stop agent execution."""
    
    def __init__(self):
        """Initialize the task evaluator."""
        self.previous_responses = []
        self.task_metrics = {
            "information_completeness": 0.0,
            "convergence_rate": 0.0,
            "successful_tool_calls": 0,
            "failed_tool_calls": 0,
            "information_sources": set(),
            "convergence_iterations": 0,
            "potential_hallucinations": 0,
            "keyword_presence": {},
        }
    
    def update_metrics(self, 
                      response: str, 
                      tool_results: List[Dict[str, Any]], 
                      task_description: str) -> Dict[str, Any]:
        """
        Update task completion metrics based on the latest response and tool results.
        
        Args:
            response: The latest agent response
            tool_results: Results from tool executions
            task_description: Original task description
            
        Returns:
            Updated metrics dictionary
        """
        # Track responses for convergence analysis
        self.previous_responses.append(response)
        
        # Extract key information from task description
        keywords = self._extract_keywords(task_description)
        
        # Count successful vs failed tool calls
        for tool_result in tool_results:
            if "error" in tool_result and tool_result["error"]:
                self.task_metrics["failed_tool_calls"] += 1
            else:
                self.task_metrics["successful_tool_calls"] += 1
                
                # Track diverse information sources (e.g., different websites)
                if "source" in tool_result:
                    self.task_metrics["information_sources"].add(tool_result["source"])
                    
        # Check for keyword presence in the response
        for keyword in keywords:
            if keyword.lower() in response.lower():
                if keyword not in self.task_metrics["keyword_presence"]:
                    self.task_metrics["keyword_presence"][keyword] = 0
                self.task_metrics["keyword_presence"][keyword] += 1
                
        # Calculate information completeness (what % of keywords are covered)
        keyword_coverage = len(self.task_metrics["keyword_presence"]) / max(1, len(keywords))
        self.task_metrics["information_completeness"] = min(1.0, keyword_coverage)
        
        # Detect potential hallucinations (unverified claims)
        hallucination_patterns = [
            r"\b(?:according to|as per|based on)\b.{1,30}?\b(?:analysis|study|research|report|findings)\b",
            r"\b(?:shows|indicates|suggests|demonstrates|proves)\b.{1,30}?\b(?:that|which|how)\b",
            r"\b(?:significantly|dramatically|substantially)\b.{1,30}?\b(?:increases|decreases|improves|reduces)\b"
        ]
        
        for pattern in hallucination_patterns:
            matches = re.findall(pattern, response, re.IGNORECASE)
            self.task_metrics["potential_hallucinations"] += len(matches)
            
        # Calculate convergence (are we still getting new information?)
        if len(self.previous_responses) >= 2:
            current = self.previous_responses[-1].lower()
            previous = self.previous_responses[-2].lower()
            
            # Simple similarity check (more sophisticated in a real implementation)
            same_info_ratio = self._calculate_similarity(current, previous)
            
            if same_info_ratio > 0.8:  # High similarity with previous response
                self.task_metrics["convergence_iterations"] += 1
            else:
                # Reset if we're getting new information
                self.task_metrics["convergence_iterations"] = 0
                
            # Calculate convergence rate
            total_iterations = len(self.previous_responses)
            self.task_metrics["convergence_rate"] = self.task_metrics["convergence_iterations"] / max(1, total_iterations)
        
        return self.task_metrics
    
    def is_task_complete(self, 
                       task_description: str, 
                       current_response: str,
                       all_responses: List[str],
                       tool_results: List[Dict[str, Any]],
                       max_iterations: int = 10) -> Tuple[bool, str, float]:
        """
        Determine if a task is complete based on multiple signals.
        
        Args:
            task_description: Original task description
            current_response: Latest agent response
            all_responses: All agent responses so far
            tool_results: All tool execution results
            max_iterations: Maximum number of iterations
            
        Returns:
            Tuple of (is_complete, reason, confidence)
        """
        # Update metrics with new data
        self.update_metrics(current_response, tool_results, task_description)
        
        # Check for explicit completion indicators
        completion_indicators = [
            "task complete", "task completed", "task is complete",
            "i have completed", "i've completed", "completed the task",
            "found all the requested information", "finished gathering",
            "here is the final", "final answer"
        ]
        
        for indicator in completion_indicators:
            if indicator in current_response.lower():
                return True, f"Agent indicates completion with: '{indicator}'", 0.95
        
        # Check if we've reached maximum iterations
        if len(all_responses) >= max_iterations:
            return True, f"Reached maximum iterations ({max_iterations})", 0.9
        
        # Check information completeness (>80% of keywords covered)
        if self.task_metrics["information_completeness"] > 0.8:
            # If we have high info completeness AND convergence, we're likely done
            if self.task_metrics["convergence_iterations"] >= 2:
                confidence = 0.85
                return True, "High information completeness and convergence reached", confidence
                
        # Check if the agent is simply repeating itself
        if self.task_metrics["convergence_iterations"] >= 3:
            return True, "Agent has converged (repeating similar information)", 0.75
        
        # Check for task-specific completion indicators
        if "list" in task_description.lower():
            # For listing tasks, check if we have a substantial list
            list_items = re.findall(r"^\d+\.\s", current_response, re.MULTILINE)
            if len(list_items) >= 5:  # Consider a list of 5+ items to be substantial
                return True, f"Found a substantial list with {len(list_items)} items", 0.8
                
        if "compare" in task_description.lower():
            # For comparison tasks, look for comparison language
            comparison_terms = ["whereas", "while", "in contrast", "on the other hand", 
                               "however", "compared to", "better than", "worse than"]
            for term in comparison_terms:
                if term in current_response.lower():
                    return True, f"Comparison completed (contains term: '{term}')", 0.8
                    
        # Default: task not yet complete
        # Calculate completion confidence
        confidence = (
            (0.4 * self.task_metrics["information_completeness"]) +
            (0.3 * self.task_metrics["convergence_rate"]) +
            (0.2 * min(1.0, self.task_metrics["successful_tool_calls"] / max(1, self.task_metrics["successful_tool_calls"] + self.task_metrics["failed_tool_calls"]))) +
            (0.1 * min(1.0, len(self.task_metrics["information_sources"]) / 3))
        )
        
        return False, f"Task in progress (confidence: {confidence:.2f})", confidence
        
    def _extract_keywords(self, text: str) -> List[str]:
        """Extract important keywords from text."""
        # Remove common words and punctuation
        common_words = ["the", "and", "a", "an", "in", "on", "at", "of", "to", "for", 
                      "with", "by", "about", "like", "through", "over", "before", "after",
                      "between", "under", "during", "regarding", "into"]
        
        # Extract single words
        words = re.findall(r'\b\w+\b', text.lower())
        keywords = [word for word in words if len(word) > 3 and word not in common_words]
        
        # Extract multi-word phrases (2-3 words)
        phrases = re.findall(r'\b\w+\s+\w+(?:\s+\w+)?\b', text.lower())
        keywords.extend([phrase for phrase in phrases if len(phrase) > 10])
        
        # Ensure uniqueness and return
        return list(set(keywords))
    
    def _calculate_similarity(self, text1: str, text2: str) -> float:
        """
        Calculate similarity between two text snippets.
        
        A real implementation would use more sophisticated methods like cosine similarity
        with word embeddings, but this is a simple version for demonstration.
        """
        # Convert to sets of words for basic overlap calculation
        words1 = set(re.findall(r'\b\w+\b', text1.lower()))
        words2 = set(re.findall(r'\b\w+\b', text2.lower()))
        
        # Calculate Jaccard similarity (intersection over union)
        intersection = len(words1.intersection(words2))
        union = len(words1.union(words2))
        
        return intersection / max(1, union)