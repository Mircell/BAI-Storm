from abc import ABC, abstractmethod

class BaseSession(ABC):
    @abstractmethod
    def get_next_idea(self):
        """Generate the next idea from the next agent."""
        pass

    @abstractmethod
    def stop(self):
        """Stop the session."""
        pass

    @abstractmethod
    def get_summary(self):
        """Return a summary of the session."""
        pass