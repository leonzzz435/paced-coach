def get_config():
    from core.config import get_config as resolve_config

    return resolve_config()


def get_version_manifest():
    from core.version_manifest import get_version_manifest as resolve_version_manifest

    return resolve_version_manifest()

__all__ = ["get_config", "get_version_manifest"]
