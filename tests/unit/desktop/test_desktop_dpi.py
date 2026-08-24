# tests/unit/desktop/test_desktop_dpi.py

from unittest.mock import MagicMock, patch

import pytest

from windows_use.agent.desktop.service import Desktop


class _FakeUser32WithoutGetDpi:
    """Plain object emulating user32 on Windows 7/8/8.1.

    A MagicMock cannot be used here: ``getattr(mock, "GetDpiForSystem", None)``
    would return an auto-created child mock instead of raising AttributeError,
    so the fallback path would never trigger.
    """

    def __init__(self, dc_handle=0x1234):
        self.GetDC = MagicMock(return_value=dc_handle)
        self.ReleaseDC = MagicMock()


class TestGetDpiScaling:
    @pytest.fixture
    def desktop(self):
        # Patching dependencies in __init__
        with (
            patch(
                "windows_use.agent.desktop.service.uia.GetVirtualScreenSize",
                return_value=(1920, 1080),
            ),
            patch("windows_use.agent.desktop.service.Tree"),
        ):
            return Desktop()

    def test_modern_path_uses_get_dpi_for_system(self, desktop):
        user32 = MagicMock()
        user32.GetDpiForSystem = MagicMock(return_value=144)

        with patch("ctypes.windll.user32", user32):
            assert desktop.get_dpi_scaling() == pytest.approx(1.5)

        user32.GetDpiForSystem.assert_called_once()
        user32.GetDC.assert_not_called()

    def test_fallback_path_when_api_missing(self, desktop):
        """Windows 7/8/8.1: GetDpiForSystem does not exist in user32."""
        user32 = _FakeUser32WithoutGetDpi()
        gdi32 = MagicMock()
        gdi32.GetDeviceCaps = MagicMock(return_value=96)

        with (
            patch("ctypes.windll.user32", user32),
            patch("ctypes.windll.gdi32", gdi32),
        ):
            assert desktop.get_dpi_scaling() == pytest.approx(1.0)

        user32.GetDC.assert_called_once_with(None)
        gdi32.GetDeviceCaps.assert_called_once()
        # DC handle must be released (no GDI leak)
        user32.ReleaseDC.assert_called_once()

    def test_fallback_path_scaled_dpi(self, desktop):
        """Fallback returns 1.5 for 144 DPI (150% scaling)."""
        user32 = _FakeUser32WithoutGetDpi()
        gdi32 = MagicMock()
        gdi32.GetDeviceCaps = MagicMock(return_value=144)

        with (
            patch("ctypes.windll.user32", user32),
            patch("ctypes.windll.gdi32", gdi32),
        ):
            assert desktop.get_dpi_scaling() == pytest.approx(1.5)

    def test_fallback_releases_dc_on_error(self, desktop):
        """ReleaseDC must run even if GetDeviceCaps raises."""
        user32 = _FakeUser32WithoutGetDpi()
        gdi32 = MagicMock()
        gdi32.GetDeviceCaps = MagicMock(side_effect=OSError("gdi failure"))

        with (
            patch("ctypes.windll.user32", user32),
            patch("ctypes.windll.gdi32", gdi32),
            pytest.raises(OSError),
        ):
            desktop.get_dpi_scaling()

        user32.ReleaseDC.assert_called_once()

    def test_getdevicecaps_receives_logpixelsx(self, desktop):
        """The fallback must query LOGPIXELSX, not another capability."""
        import win32con

        user32 = _FakeUser32WithoutGetDpi()
        gdi32 = MagicMock()
        gdi32.GetDeviceCaps = MagicMock(return_value=96)

        with (
            patch("ctypes.windll.user32", user32),
            patch("ctypes.windll.gdi32", gdi32),
        ):
            desktop.get_dpi_scaling()

        args = gdi32.GetDeviceCaps.call_args[0]
        assert args[0] == 0x1234
        assert args[1] == win32con.LOGPIXELSX
