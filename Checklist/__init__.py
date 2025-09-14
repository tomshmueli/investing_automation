import sys
import types

# Compatibility shim for environments where websockets<12 is installed.
# yfinance>=0.2.59 imports from websockets.asyncio.client. Provide a minimal
# alias to avoid import-time failures in hosts that pin older websockets.
try:
    import websockets  # noqa: F401
    try:
        from websockets.asyncio.client import connect as _ws_async_connect  # type: ignore
        _ = _ws_async_connect  # silence unused
    except Exception:
        _legacy_connect = None
        try:
            from websockets.client import connect as _legacy_connect  # type: ignore
        except Exception:
            try:
                from websockets.legacy.client import connect as _legacy_connect  # type: ignore
            except Exception:
                _legacy_connect = None

        if _legacy_connect is not None:
            ws_asyncio = types.ModuleType("websockets.asyncio")
            ws_asyncio_client = types.ModuleType("websockets.asyncio.client")
            ws_asyncio_client.connect = _legacy_connect  # type: ignore[attr-defined]
            ws_asyncio.client = ws_asyncio_client  # type: ignore[attr-defined]
            sys.modules.setdefault("websockets.asyncio", ws_asyncio)
            sys.modules["websockets.asyncio.client"] = ws_asyncio_client
except Exception:
    pass
