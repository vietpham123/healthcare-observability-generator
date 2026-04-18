from abc import ABC, abstractmethod


class BaseGenerator(ABC):
    """Abstract base class for all log generators."""

    @abstractmethod
    def generate_event(self, session, config):
        """Generate a single log event.

        Args:
            session: UserSession (or None for service/API events).
            config: dict of configuration values.

        Returns:
            str: The raw event content (XML, HL7, JSON, etc.)
        """
        pass

    @abstractmethod
    def format_output(self, event, environment=None):
        """Wrap event in transport format (e.g., syslog header).

        Args:
            event: str raw event content.
            environment: optional dict with environment-specific values.

        Returns:
            str: Fully formatted log line ready for output.
        """
        pass

    def generate_sample(self, n=10, config=None):
        """Generate n sample events to stdout for validation."""
        for i in range(n):
            event = self.generate_event(None, config or {})
            formatted = self.format_output(event)
            print(formatted)
