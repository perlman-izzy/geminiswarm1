"""Task queue implementation for the Gemini Swarm Debugger."""
import threading
from collections import deque
from typing import Optional, Any


class TaskQueue:
    """A thread-safe queue implementation for distributing tasks to worker threads."""
    
    def __init__(self):
        """Initialize an empty task queue with a lock for thread safety."""
        self.queue = deque()
        self.lock = threading.Lock()
    
    def push(self, item: Any) -> None:
        """Add an item to the end of the queue.
        
        Args:
            item: The item to add to the queue.
        """
        with self.lock:
            self.queue.append(item)
    
    def pop(self) -> Optional[Any]:
        """Remove and return the next item from the queue.
        
        Returns:
            The next item in the queue, or None if the queue is empty.
        """
        with self.lock:
            if not self.queue:
                return None
            return self.queue.popleft()
    
    def size(self) -> int:
        """Get the current size of the queue.
        
        Returns:
            The number of items in the queue.
        """
        with self.lock:
            return len(self.queue)
    
    def is_empty(self) -> bool:
        """Check if the queue is empty.
        
        Returns:
            True if the queue is empty, False otherwise.
        """
        with self.lock:
            return len(self.queue) == 0