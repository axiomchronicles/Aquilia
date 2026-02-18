"""
Notifications Module — Fault Definitions
"""

from aquilia.faults import (
    Fault,
    FaultDomain,
    Severity,
)


NOTIFICATIONS_DOMAIN = FaultDomain(
    name="notifications",
    description="Notification and real-time messaging fault domain",
)


class NotificationDeliveryFault(Fault):
    domain = NOTIFICATIONS_DOMAIN
    severity = Severity.ERROR
    code = "NOTIFICATION_DELIVERY_FAILED"

    def __init__(self, detail: str = ""):
        msg = detail if detail else "Failed to deliver notification"
        super().__init__(code=self.code, message=msg, domain=self.domain,
                         severity=self.severity, public=True)


class WebSocketConnectionFault(Fault):
    domain = NOTIFICATIONS_DOMAIN
    severity = Severity.WARN
    code = "WS_CONNECTION_FAILED"

    def __init__(self, detail: str = ""):
        msg = detail if detail else "WebSocket connection failed"
        super().__init__(code=self.code, message=msg, domain=self.domain,
                         severity=self.severity, public=True)


class InvalidChannelFault(Fault):
    domain = NOTIFICATIONS_DOMAIN
    severity = Severity.WARN
    code = "INVALID_CHANNEL"

    def __init__(self, channel: str = ""):
        msg = f"Channel '{channel}' does not exist." if channel else "Channel not found"
        super().__init__(code=self.code, message=msg, domain=self.domain,
                         severity=self.severity, public=True)


class BroadcastFault(Fault):
    domain = NOTIFICATIONS_DOMAIN
    severity = Severity.ERROR
    code = "BROADCAST_FAILED"

    def __init__(self, detail: str = ""):
        msg = detail if detail else "Failed to broadcast message"
        super().__init__(code=self.code, message=msg, domain=self.domain,
                         severity=self.severity, public=True)


class ChannelPermissionFault(Fault):
    domain = NOTIFICATIONS_DOMAIN
    severity = Severity.WARN
    code = "CHANNEL_PERMISSION_DENIED"

    def __init__(self, channel: str = ""):
        msg = f"No permission to access channel '{channel}'." if channel else "Channel access denied"
        super().__init__(code=self.code, message=msg, domain=self.domain,
                         severity=self.severity, public=True)
