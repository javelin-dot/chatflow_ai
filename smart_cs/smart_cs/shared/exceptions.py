"""Common exceptions for smart_cs."""


class SmartCSError(Exception):
    """Base for all smart_cs errors."""


class ConfigError(SmartCSError):
    pass


class TenantNotFoundError(SmartCSError):
    pass


class ChannelError(SmartCSError):
    pass


class SessionError(SmartCSError):
    pass


class SkillError(SmartCSError):
    pass


class ToolGuardError(SmartCSError):
    """Raised when a tool call is rejected by ToolGuard (denied/quota/expired)."""


class QuotaExceededError(SmartCSError):
    pass


class GuardrailBlockedError(SmartCSError):
    pass


class HandoffRequestedError(SmartCSError):
    """Signal to switch to human handoff (not really an error)."""
