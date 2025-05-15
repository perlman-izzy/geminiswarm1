"""
Task Completion Evaluation for SuperAGI.

This module evaluates whether an agent has completed its tasks and should stop execution.
"""
import re
from typing import List, Dict, Any, Tuple


class TaskCompletion:
    """
    Evaluates whether an agent has completed its assigned task.
    
    This class implements various stopping conditions to determine if an agent
    should continue execution or if it has completed its goals.
    """
    
    @staticmethod
    def evaluate_completion(
        goals: List[str],
        messages: List[Dict[str, str]],
        max_iterations: int = 15,
        current_iteration: int = 0,
    ) -> Tuple[bool, str, float]:
        """
        Evaluate if the task is complete based on goals, messages, and iterations.
        
        Args:
            goals: List of goals the agent should achieve
            messages: List of messages in the conversation history
            max_iterations: Maximum number of iterations before forced stop
            current_iteration: Current iteration number
            
        Returns:
            Tuple of (is_complete, reason, confidence)
        """
        # Check iterations first
        if current_iteration >= max_iterations:
            return True, f"Maximum iterations ({max_iterations}) reached", 1.0
            
        # Extract only assistant messages
        assistant_messages = [msg["content"] for msg in messages if msg["role"] == "assistant"]
        
        if not assistant_messages:
            return False, "No assistant messages yet", 0.0
            
        # Get the most recent messages (last 3)
        recent_messages = assistant_messages[-3:] if len(assistant_messages) >= 3 else assistant_messages
        
        # Check the most recent message for explicit completion indicators
        last_message = assistant_messages[-1]
        completion_indicators = [
            r"(?i)task\s+(?:is\s+)?(?:now\s+)?(?:complete|finished|done|accomplished)",
            r"(?i)(?:i|i've|we|we've)\s+(?:have\s+)?(?:now\s+)?(?:complete|accomplished|finished|done|achieved)\s+(?:the|all|your)",
            r"(?i)(?:here|this)\s+(?:is|are)\s+(?:the|your)\s+(?:final|complete|full)",
            r"(?i)(?:goal|goals|objective|objectives)\s+(?:has|have)\s+(?:been|all)\s+(?:achieved|met|completed|fulfilled)",
            r"(?i)(?:found|gathered|collected|compiled)\s+all\s+(?:the|requested|required)",
            r"(?i)(?:in\s+conclusion|to\s+summarize|summing\s+up).{1,50}(?:completed|achieved|done)",
        ]
        
        for pattern in completion_indicators:
            if re.search(pattern, last_message, re.DOTALL):
                return True, "Agent indicated task completion", 0.95
                
        # Check if we're seeing loops or repetitive responses
        if len(assistant_messages) >= 3:
            # Check for similarity in recent messages
            if TaskCompletion._messages_are_similar(assistant_messages[-1], assistant_messages[-2]):
                if TaskCompletion._messages_are_similar(assistant_messages[-2], assistant_messages[-3]):
                    return True, "Detected repetitive outputs, suggesting completion", 0.8
        
        # Check if all goals are covered in the messages
        goal_coverage = TaskCompletion._calculate_goal_coverage(goals, assistant_messages)
        if goal_coverage >= 0.9:  # 90% of goals covered
            return True, f"High goal coverage ({goal_coverage:.2f})", 0.9
            
        # Default: task is not complete
        return False, f"Task in progress (goal coverage: {goal_coverage:.2f})", goal_coverage
    
    @staticmethod
    def _messages_are_similar(msg1: str, msg2: str, threshold: float = 0.7) -> bool:
        """
        Check if two messages are similar based on content overlap.
        
        Args:
            msg1: First message
            msg2: Second message
            threshold: Similarity threshold (0.0 to 1.0)
            
        Returns:
            True if messages are similar, False otherwise
        """
        # Extract content without common formatting
        def normalize(text):
            # Remove code blocks
            text = re.sub(r'```.*?```', '', text, flags=re.DOTALL)
            # Remove markdown headers
            text = re.sub(r'#+\s+.*?\n', '', text)
            # Keep only alphanumeric and whitespace
            text = re.sub(r'[^a-zA-Z0-9\s]', '', text)
            # Normalize whitespace
            text = re.sub(r'\s+', ' ', text).strip().lower()
            return text
            
        norm_msg1 = normalize(msg1)
        norm_msg2 = normalize(msg2)
        
        # Simple word overlap calculation
        words1 = set(norm_msg1.split())
        words2 = set(norm_msg2.split())
        
        if not words1 or not words2:
            return False
            
        overlap = len(words1.intersection(words2))
        similarity = overlap / max(len(words1), len(words2))
        
        return similarity >= threshold
    
    @staticmethod
    def _calculate_goal_coverage(goals: List[str], messages: List[str]) -> float:
        """
        Calculate how well the goals are covered in the messages.
        
        Args:
            goals: List of goals
            messages: List of message contents
            
        Returns:
            Score from 0.0 to 1.0 representing goal coverage
        """
        if not goals:
            return 1.0  # No goals means perfect coverage
            
        # Extract key terms from goals
        goal_terms = set()
        for goal in goals:
            # Remove common words
            terms = re.findall(r'\b[a-zA-Z]{4,}\b', goal.lower())
            goal_terms.update(terms)
            
        if not goal_terms:
            return 1.0  # No meaningful terms to match
            
        # Combine all messages into a single string for checking
        all_content = ' '.join(messages).lower()
        
        # Count how many goal terms are present in messages
        matched_terms = sum(1 for term in goal_terms if term in all_content)
        
        # Calculate coverage
        return matched_terms / len(goal_terms)