"""Pluggable WhatsApp admin-notification service.

The customer-facing WhatsApp buttons are plain ``wa.me`` links and do NOT use
this module. This abstraction is only for backend admin alerts (new orders,
quotation requests). Swap providers via the ``WHATSAPP_PROVIDER`` setting.
"""
from __future__ import annotations

import abc
import logging

from django.conf import settings

logger = logging.getLogger(__name__)


class WhatsAppProvider(abc.ABC):
    @abc.abstractmethod
    def send(self, to: str, message: str) -> bool:  # pragma: no cover - interface
        ...


class ConsoleWhatsAppProvider(WhatsAppProvider):
    """Default provider: logs instead of hitting an external API."""

    def send(self, to: str, message: str) -> bool:
        logger.info("[WhatsApp:console] to=%s message=%s", to, message)
        return True


class MetaCloudWhatsAppProvider(WhatsAppProvider):
    """WhatsApp Cloud API (Meta Graph) provider.

    Requires WHATSAPP_PHONE_NUMBER_ID and WHATSAPP_ACCESS_TOKEN settings.
    Falls back to logging (and returns False) when unconfigured so callers
    never crash in environments without credentials.
    """

    API_ROOT = "https://graph.facebook.com/v20.0"

    def send(self, to: str, message: str) -> bool:
        phone_number_id = getattr(settings, "WHATSAPP_PHONE_NUMBER_ID", "")
        access_token = getattr(settings, "WHATSAPP_ACCESS_TOKEN", "")
        if not (phone_number_id and access_token and to):
            logger.warning(
                "[WhatsApp:meta] not configured; would send to=%s: %s", to, message
            )
            return False

        import requests  # local import; only needed when this provider is active

        resp = requests.post(
            f"{self.API_ROOT}/{phone_number_id}/messages",
            headers={"Authorization": f"Bearer {access_token}"},
            json={
                "messaging_product": "whatsapp",
                "to": to,
                "type": "text",
                "text": {"body": message},
            },
            timeout=15,
        )
        resp.raise_for_status()
        return True


_PROVIDERS = {
    "console": ConsoleWhatsAppProvider,
    "meta": MetaCloudWhatsAppProvider,
}


def get_whatsapp_provider() -> WhatsAppProvider:
    key = getattr(settings, "WHATSAPP_PROVIDER", "console")
    provider_cls = _PROVIDERS.get(key, ConsoleWhatsAppProvider)
    return provider_cls()


def build_new_order_message(order) -> str:
    """Human-readable admin alert for a newly placed order."""
    return (
        f"🛒 New NLK order {order.order_number}\n"
        f"Customer: {order.shipping_full_name} ({order.shipping_phone})\n"
        f"Total: Rs. {order.total:,.2f}\n"
        f"Payment: {order.get_payment_method_display()}\n"
        f"Status: {order.get_status_display()}"
    )
