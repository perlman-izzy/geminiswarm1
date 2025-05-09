"""Task queue implementation for the Gemini Swarm Debugger."""
import queue
from typing import Optional, Any


class TaskQueue:
    """A thread-safe queue implementation for distributing tasks to worker threads."""
    
    def __init__(self):
        """Initialize an empty task queue with a thread-safe Queue implementation."""
        self._queue = queue.Queue()
    
    def push(self, item: Any) -> None:
        """Add an item to the end of the queue.
        
        Args:
            item: The item to add to the queue.
        """
        self._queue.put(item)
    
    def pop(self) -> Optional[Any]:
        """Remove and return the next item from the queue.
        
        Returns:
            The next item in the queue, or blocks until an item is available.
        """
        return self._queue.get()
    
    def size(self) -> int:
        """Get the current size of the queue.
        
        Returns:
            The number of items in the queue.
        """
        return self._queue.qsize()
    
    def is_empty(self) -> bool:
        """Check if the queue is empty.
        
        Returns:
            True if the queue is empty, False otherwise.
        """
        return self._queue.empty()