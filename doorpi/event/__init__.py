"""The event-action system"""


class AbortEventExecution(Exception):
    """Abort executing the current event"""

class SkipEventExecution(Exception):
    """Skipping executing of next action"""
