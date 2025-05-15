"""
Base LLM class for SuperAGI.
"""
from abc import ABC, abstractmethod


class BaseLlm(ABC):
    @abstractmethod
    def chat_completion(self, prompt):
        """Generate a chat completion for the given prompt."""
        pass

    @abstractmethod
    def get_source(self):
        """Get the source of the LLM."""
        pass

    @abstractmethod
    def get_model(self):
        """Get the model name."""
        pass

    @abstractmethod
    def get_models(self):
        """Get available models."""
        pass

    @abstractmethod
    def verify_access_key(self):
        """Verify that the access key is valid."""
        pass