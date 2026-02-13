"""
Delivery layer: abstract interface and plugin registry.
All delivery plugins implement DeliveryPlugin and are loaded by config (delivery.plugins).
"""
import importlib
import logging
from abc import ABC, abstractmethod
from typing import Any

logger = logging.getLogger(__name__)

# Registry: plugin_id -> class or factory
_plugins: dict[str, type] = {}


class DeliveryPlugin(ABC):
    """Abstract interface for delivery: read from InsightStore, execute delivery (e.g. send email)."""

    @property
    @abstractmethod
    def plugin_id(self) -> str:
        """Unique id for config, e.g. 'email', 'report'."""
        pass

    @abstractmethod
    def deliver(
        self,
        insight_store: Any,
        config: dict[str, Any] | None = None,
        context: dict[str, Any] | None = None,
    ) -> bool:
        """
        Read insights from insight_store, perform delivery.
        context may contain e.g. raw_store for link resolution.
        Returns True on success, False on failure (caller may log).
        """
        pass


def register_plugin(plugin_id: str, plugin_class: type) -> None:
    if not issubclass(plugin_class, DeliveryPlugin):
        raise TypeError(f"{plugin_class} must implement DeliveryPlugin")
    _plugins[plugin_id] = plugin_class
    logger.debug("Registered delivery plugin: %s", plugin_id)


def get_plugin(plugin_id: str) -> DeliveryPlugin | None:
    cls = _plugins.get(plugin_id)
    if cls is None:
        return None
    return cls()


def load_plugins_from_config(plugin_ids: list[str]) -> list[DeliveryPlugin]:
    """Load plugins by id list; each id maps to delivery.plugins.<id> module with a 'plugin' export."""
    loaded = []
    for pid in plugin_ids or []:
        try:
            mod = importlib.import_module(f"src.delivery.plugins.{pid}")
            plugin = getattr(mod, "plugin", None)
            if plugin is None:
                logger.warning("Plugin %s has no 'plugin' export", pid)
                continue
            if not isinstance(plugin, DeliveryPlugin):
                logger.warning("Plugin %s export is not DeliveryPlugin", pid)
                continue
            loaded.append(plugin)
            logger.info("Loaded delivery plugin: %s", pid)
        except Exception as e:
            logger.exception("Failed to load plugin %s: %s", pid, e)
    return loaded


def list_registered_ids() -> list[str]:
    return list(_plugins.keys())
