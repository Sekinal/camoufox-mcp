"""
Device and network emulation tools for Camoufox MCP Server.

Provides device emulation (viewport, user agent, touch) and network throttling.

Tools: emulate_device, emulate_network, set_geolocation, set_timezone, set_locale,
       set_color_scheme, set_reduced_motion, clear_emulation
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Literal

from src.camoufox_mcp.instrumentation import instrumented_tool
from src.camoufox_mcp.session import get_session

if TYPE_CHECKING:
    from mcp.server.fastmcp import FastMCP


# Common device presets
DEVICE_PRESETS = {
    "iphone_14": {
        "viewport": {"width": 390, "height": 844},
        "user_agent": "Mozilla/5.0 (iPhone; CPU iPhone OS 16_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.0 Mobile/15E148 Safari/604.1",
        "device_scale_factor": 3,
        "is_mobile": True,
        "has_touch": True,
    },
    "iphone_14_pro_max": {
        "viewport": {"width": 430, "height": 932},
        "user_agent": "Mozilla/5.0 (iPhone; CPU iPhone OS 16_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.0 Mobile/15E148 Safari/604.1",
        "device_scale_factor": 3,
        "is_mobile": True,
        "has_touch": True,
    },
    "ipad_pro": {
        "viewport": {"width": 1024, "height": 1366},
        "user_agent": "Mozilla/5.0 (iPad; CPU OS 16_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.0 Mobile/15E148 Safari/604.1",
        "device_scale_factor": 2,
        "is_mobile": True,
        "has_touch": True,
    },
    "pixel_7": {
        "viewport": {"width": 412, "height": 915},
        "user_agent": "Mozilla/5.0 (Linux; Android 13; Pixel 7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/116.0.0.0 Mobile Safari/537.36",
        "device_scale_factor": 2.625,
        "is_mobile": True,
        "has_touch": True,
    },
    "samsung_galaxy_s23": {
        "viewport": {"width": 360, "height": 780},
        "user_agent": "Mozilla/5.0 (Linux; Android 13; SM-S911B) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/116.0.0.0 Mobile Safari/537.36",
        "device_scale_factor": 3,
        "is_mobile": True,
        "has_touch": True,
    },
    "desktop_1080p": {
        "viewport": {"width": 1920, "height": 1080},
        "user_agent": None,  # Use default
        "device_scale_factor": 1,
        "is_mobile": False,
        "has_touch": False,
    },
    "desktop_1440p": {
        "viewport": {"width": 2560, "height": 1440},
        "user_agent": None,
        "device_scale_factor": 1,
        "is_mobile": False,
        "has_touch": False,
    },
    "laptop": {
        "viewport": {"width": 1366, "height": 768},
        "user_agent": None,
        "device_scale_factor": 1,
        "is_mobile": False,
        "has_touch": False,
    },
}

# Network condition presets (latency in ms, download/upload in bytes per second)
NETWORK_PRESETS = {
    "offline": {"offline": True},
    "slow_3g": {
        "offline": False,
        "download_throughput": 500 * 1024 // 8,  # 500 Kbps
        "upload_throughput": 500 * 1024 // 8,
        "latency": 400,
    },
    "fast_3g": {
        "offline": False,
        "download_throughput": 1.5 * 1024 * 1024 // 8,  # 1.5 Mbps
        "upload_throughput": 750 * 1024 // 8,
        "latency": 150,
    },
    "slow_4g": {
        "offline": False,
        "download_throughput": 3 * 1024 * 1024 // 8,  # 3 Mbps
        "upload_throughput": 1.5 * 1024 * 1024 // 8,
        "latency": 100,
    },
    "fast_4g": {
        "offline": False,
        "download_throughput": 10 * 1024 * 1024 // 8,  # 10 Mbps
        "upload_throughput": 5 * 1024 * 1024 // 8,
        "latency": 50,
    },
    "wifi": {
        "offline": False,
        "download_throughput": 30 * 1024 * 1024 // 8,  # 30 Mbps
        "upload_throughput": 15 * 1024 * 1024 // 8,
        "latency": 10,
    },
    "no_throttle": {
        "offline": False,
        "download_throughput": -1,  # No limit
        "upload_throughput": -1,
        "latency": 0,
    },
}


def register(mcp: FastMCP) -> None:
    """Register emulation tools with the MCP server."""

    @mcp.tool()
    @instrumented_tool()
    async def emulate_device(
        device: str | None = None,
        viewport_width: int | None = None,
        viewport_height: int | None = None,
        user_agent: str | None = None,
        device_scale_factor: float | None = None,
        is_mobile: bool | None = None,
        has_touch: bool | None = None,
    ) -> str:
        """
        Emulate a device by setting viewport, user agent, and touch capabilities.

        Can use a preset device name or specify custom settings.

        Args:
            device: Preset device name. Options:
                    - "iphone_14", "iphone_14_pro_max", "ipad_pro"
                    - "pixel_7", "samsung_galaxy_s23"
                    - "desktop_1080p", "desktop_1440p", "laptop"
            viewport_width: Custom viewport width (overrides preset)
            viewport_height: Custom viewport height (overrides preset)
            user_agent: Custom user agent string (overrides preset)
            device_scale_factor: Device pixel ratio (overrides preset)
            is_mobile: Emulate mobile device (overrides preset)
            has_touch: Enable touch events (overrides preset)

        Returns:
            Emulation status
        """
        session = get_session()

        if not session.page:
            return "Error: No active page."

        try:
            # Start with preset if specified
            settings = {}
            if device:
                device_lower = device.lower().replace(" ", "_").replace("-", "_")
                if device_lower not in DEVICE_PRESETS:
                    available = ", ".join(DEVICE_PRESETS.keys())
                    return f"Error: Unknown device '{device}'. Available: {available}"
                settings = DEVICE_PRESETS[device_lower].copy()

            # Apply custom overrides
            if viewport_width is not None or viewport_height is not None:
                viewport = settings.get("viewport", {"width": 1280, "height": 720})
                if viewport_width is not None:
                    viewport["width"] = viewport_width
                if viewport_height is not None:
                    viewport["height"] = viewport_height
                settings["viewport"] = viewport

            if user_agent is not None:
                settings["user_agent"] = user_agent
            if device_scale_factor is not None:
                settings["device_scale_factor"] = device_scale_factor
            if is_mobile is not None:
                settings["is_mobile"] = is_mobile
            if has_touch is not None:
                settings["has_touch"] = has_touch

            # Apply viewport
            if "viewport" in settings:
                await session.page.set_viewport_size(settings["viewport"])

            # Apply other emulation settings via CDP if available
            # Note: Some settings require context-level configuration
            result_parts = []

            if "viewport" in settings:
                result_parts.append(f"viewport: {settings['viewport']['width']}x{settings['viewport']['height']}")

            if settings.get("user_agent"):
                # Try to set user agent via CDP
                try:
                    client = await session.page.context.new_cdp_session(session.page)
                    await client.send("Emulation.setUserAgentOverride", {
                        "userAgent": settings["user_agent"],
                        "platform": "iPhone" if settings.get("is_mobile") else "Win32",
                    })
                    result_parts.append("user agent set")
                except Exception:
                    result_parts.append("user agent (requires page reload)")

            if settings.get("has_touch"):
                try:
                    client = await session.page.context.new_cdp_session(session.page)
                    await client.send("Emulation.setTouchEmulationEnabled", {
                        "enabled": True,
                        "maxTouchPoints": 5,
                    })
                    result_parts.append("touch enabled")
                except Exception:
                    result_parts.append("touch (not supported)")

            if settings.get("device_scale_factor"):
                try:
                    client = await session.page.context.new_cdp_session(session.page)
                    await client.send("Emulation.setDeviceMetricsOverride", {
                        "width": settings["viewport"]["width"],
                        "height": settings["viewport"]["height"],
                        "deviceScaleFactor": settings["device_scale_factor"],
                        "mobile": settings.get("is_mobile", False),
                    })
                    result_parts.append(f"scale: {settings['device_scale_factor']}x")
                except Exception:
                    pass

            device_name = device or "custom"
            return f"Device emulation applied ({device_name}): {', '.join(result_parts)}"

        except Exception as e:
            return f"Error applying device emulation: {str(e)}"

    @mcp.tool()
    @instrumented_tool()
    async def emulate_network(
        preset: str | None = None,
        offline: bool | None = None,
        download_throughput: int | None = None,
        upload_throughput: int | None = None,
        latency: int | None = None,
    ) -> str:
        """
        Emulate network conditions (throttling, offline mode).

        Can use a preset or specify custom values.

        Args:
            preset: Network condition preset. Options:
                    - "offline" - No network
                    - "slow_3g" - 500 Kbps, 400ms latency
                    - "fast_3g" - 1.5 Mbps, 150ms latency
                    - "slow_4g" - 3 Mbps, 100ms latency
                    - "fast_4g" - 10 Mbps, 50ms latency
                    - "wifi" - 30 Mbps, 10ms latency
                    - "no_throttle" - No throttling
            offline: Force offline mode (overrides preset)
            download_throughput: Download speed in bytes/sec (overrides preset)
            upload_throughput: Upload speed in bytes/sec (overrides preset)
            latency: Network latency in ms (overrides preset)

        Returns:
            Network emulation status
        """
        session = get_session()

        if not session.page:
            return "Error: No active page."

        try:
            # Start with preset if specified
            settings = {"offline": False, "download_throughput": -1, "upload_throughput": -1, "latency": 0}

            if preset:
                preset_lower = preset.lower().replace(" ", "_").replace("-", "_")
                if preset_lower not in NETWORK_PRESETS:
                    available = ", ".join(NETWORK_PRESETS.keys())
                    return f"Error: Unknown preset '{preset}'. Available: {available}"
                settings = NETWORK_PRESETS[preset_lower].copy()

            # Apply custom overrides
            if offline is not None:
                settings["offline"] = offline
            if download_throughput is not None:
                settings["download_throughput"] = download_throughput
            if upload_throughput is not None:
                settings["upload_throughput"] = upload_throughput
            if latency is not None:
                settings["latency"] = latency

            # Apply via CDP
            try:
                client = await session.page.context.new_cdp_session(session.page)
                await client.send("Network.emulateNetworkConditions", {
                    "offline": settings["offline"],
                    "downloadThroughput": settings["download_throughput"],
                    "uploadThroughput": settings["upload_throughput"],
                    "latency": settings["latency"],
                })

                if settings["offline"]:
                    return "Network emulation: offline mode enabled"
                elif settings["download_throughput"] == -1:
                    return "Network emulation: throttling disabled"
                else:
                    down_kbps = settings["download_throughput"] * 8 // 1024
                    up_kbps = settings["upload_throughput"] * 8 // 1024
                    return f"Network emulation: {down_kbps} Kbps down, {up_kbps} Kbps up, {settings['latency']}ms latency"

            except Exception as e:
                return f"Error: Network emulation requires CDP support. {str(e)}"

        except Exception as e:
            return f"Error applying network emulation: {str(e)}"

    @mcp.tool()
    @instrumented_tool()
    async def set_geolocation(
        latitude: float,
        longitude: float,
        accuracy: float = 100,
    ) -> str:
        """
        Override the browser's geolocation.

        Args:
            latitude: Latitude coordinate (-90 to 90)
            longitude: Longitude coordinate (-180 to 180)
            accuracy: Accuracy in meters (default: 100)

        Returns:
            Geolocation status
        """
        session = get_session()

        if not session.page:
            return "Error: No active page."

        if not (-90 <= latitude <= 90):
            return "Error: Latitude must be between -90 and 90."
        if not (-180 <= longitude <= 180):
            return "Error: Longitude must be between -180 and 180."

        try:
            await session.page.context.set_geolocation({
                "latitude": latitude,
                "longitude": longitude,
                "accuracy": accuracy,
            })
            return f"Geolocation set to: {latitude}, {longitude} (accuracy: {accuracy}m)"
        except Exception as e:
            return f"Error setting geolocation: {str(e)}"

    @mcp.tool()
    @instrumented_tool()
    async def set_timezone(timezone_id: str) -> str:
        """
        Override the browser's timezone.

        Args:
            timezone_id: IANA timezone ID (e.g., "America/New_York", "Europe/London", "Asia/Tokyo")

        Returns:
            Timezone status
        """
        session = get_session()

        if not session.page:
            return "Error: No active page."

        try:
            client = await session.page.context.new_cdp_session(session.page)
            await client.send("Emulation.setTimezoneOverride", {
                "timezoneId": timezone_id,
            })
            return f"Timezone set to: {timezone_id}"
        except Exception as e:
            if "Invalid timezone" in str(e):
                return f"Error: Invalid timezone ID '{timezone_id}'. Use IANA format (e.g., 'America/New_York')."
            return f"Error setting timezone: {str(e)}"

    @mcp.tool()
    @instrumented_tool()
    async def set_locale(locale: str) -> str:
        """
        Override the browser's locale.

        Args:
            locale: Locale string (e.g., "en-US", "fr-FR", "ja-JP")

        Returns:
            Locale status
        """
        session = get_session()

        if not session.page:
            return "Error: No active page."

        try:
            client = await session.page.context.new_cdp_session(session.page)
            await client.send("Emulation.setLocaleOverride", {
                "locale": locale,
            })
            return f"Locale set to: {locale}"
        except Exception as e:
            return f"Error setting locale: {str(e)}"

    @mcp.tool()
    @instrumented_tool()
    async def set_color_scheme(
        scheme: Literal["light", "dark", "no-preference"] = "light",
    ) -> str:
        """
        Emulate preferred color scheme (light/dark mode).

        Args:
            scheme: Color scheme preference ("light", "dark", or "no-preference")

        Returns:
            Color scheme status
        """
        session = get_session()

        if not session.page:
            return "Error: No active page."

        try:
            await session.page.emulate_media(color_scheme=scheme)
            return f"Color scheme set to: {scheme}"
        except Exception as e:
            return f"Error setting color scheme: {str(e)}"

    @mcp.tool()
    @instrumented_tool()
    async def set_reduced_motion(reduced: bool = True) -> str:
        """
        Emulate reduced motion preference.

        Args:
            reduced: Whether to prefer reduced motion (default: True)

        Returns:
            Reduced motion status
        """
        session = get_session()

        if not session.page:
            return "Error: No active page."

        try:
            await session.page.emulate_media(
                reduced_motion="reduce" if reduced else "no-preference"
            )
            return f"Reduced motion: {'enabled' if reduced else 'disabled'}"
        except Exception as e:
            return f"Error setting reduced motion: {str(e)}"

    @mcp.tool()
    @instrumented_tool()
    async def clear_emulation() -> str:
        """
        Clear all emulation settings and restore defaults.

        Returns:
            Clear status
        """
        session = get_session()

        if not session.page:
            return "Error: No active page."

        try:
            cleared = []

            # Clear media emulation
            try:
                await session.page.emulate_media(color_scheme=None, reduced_motion=None)
                cleared.append("media")
            except Exception:
                pass

            # Clear geolocation
            try:
                await session.page.context.clear_permissions()
                cleared.append("permissions")
            except Exception:
                pass

            # Clear CDP emulations
            try:
                client = await session.page.context.new_cdp_session(session.page)
                await client.send("Emulation.clearDeviceMetricsOverride", {})
                await client.send("Network.emulateNetworkConditions", {
                    "offline": False,
                    "downloadThroughput": -1,
                    "uploadThroughput": -1,
                    "latency": 0,
                })
                cleared.append("device/network")
            except Exception:
                pass

            return f"Emulation cleared: {', '.join(cleared) or 'none active'}"

        except Exception as e:
            return f"Error clearing emulation: {str(e)}"

    @mcp.tool()
    @instrumented_tool()
    async def list_device_presets() -> str:
        """
        List available device presets for emulation.

        Returns:
            JSON list of available device presets with their settings
        """
        import json

        result = {}
        for name, settings in DEVICE_PRESETS.items():
            result[name] = {
                "viewport": settings["viewport"],
                "mobile": settings["is_mobile"],
                "touch": settings["has_touch"],
                "scale": settings["device_scale_factor"],
            }

        return json.dumps(result, indent=2)

    @mcp.tool()
    @instrumented_tool()
    async def list_network_presets() -> str:
        """
        List available network condition presets.

        Returns:
            JSON list of available network presets with their settings
        """
        import json

        result = {}
        for name, settings in NETWORK_PRESETS.items():
            if settings.get("offline"):
                result[name] = {"offline": True}
            elif settings.get("download_throughput", -1) == -1:
                result[name] = {"throttled": False}
            else:
                result[name] = {
                    "download_kbps": settings["download_throughput"] * 8 // 1024,
                    "upload_kbps": settings["upload_throughput"] * 8 // 1024,
                    "latency_ms": settings["latency"],
                }

        return json.dumps(result, indent=2)
