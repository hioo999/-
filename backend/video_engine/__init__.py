"""
video_engine — Integration shim around the Pixelle-Video engine.

This package wraps the upstream `pixelle_video` codebase (Apache 2.0, AIDC-AI)
without modifying any of its internal imports. Two things are arranged here:

1. The inner ``pixelle_video`` directory is added to ``sys.path`` so that the
   engine's existing ``from pixelle_video.xxx import yyy`` statements continue
   to resolve unchanged.
2. ``PIXELLE_VIDEO_ROOT`` is pinned to this directory, which is how
   ``pixelle_video.utils.os_util`` locates ``workflows/``, ``templates/``,
   ``bgm/``, ``resources/``, ``data/``, ``output/`` and ``config.yaml``.

Downstream code in this project should import from ``video_engine`` rather
than from ``pixelle_video`` directly, e.g.::

    from video_engine import video_engine, config_manager

See ``video_engine/NOTICE`` for upstream attribution.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

_ENGINE_ROOT: Path = Path(__file__).resolve().parent

# Expose inner package so `import pixelle_video` works.
_engine_root_str = str(_ENGINE_ROOT)
if _engine_root_str not in sys.path:
    sys.path.insert(0, _engine_root_str)

# Pin the runtime root used by pixelle_video.utils.os_util for asset lookup.
# `setdefault` lets operators override via the environment if needed.
os.environ.setdefault("PIXELLE_VIDEO_ROOT", _engine_root_str)

ENGINE_ROOT: str = _engine_root_str

# Lazy re-exports (PEP 562): importing `video_engine` itself must not pull in
# heavy third-party dependencies like `comfykit`. The actual engine objects
# are resolved on first attribute access, so the rest of the backend can boot
# even when the engine deps haven't been installed yet.
_LAZY_EXPORTS = {
    "PixelleVideoCore": ("pixelle_video", "PixelleVideoCore"),
    "config_manager": ("pixelle_video", "config_manager"),
    "video_engine": ("pixelle_video", "pixelle_video"),
}


def __getattr__(name: str):  # noqa: D401
    """Resolve lazy exports on first access."""
    if name in _LAZY_EXPORTS:
        import importlib

        module_name, attr = _LAZY_EXPORTS[name]
        module = importlib.import_module(module_name)
        value = getattr(module, attr)
        globals()[name] = value  # cache on the package
        return value
    raise AttributeError(f"module 'video_engine' has no attribute {name!r}")


__all__ = ["ENGINE_ROOT", *_LAZY_EXPORTS.keys()]
