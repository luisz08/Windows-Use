# tests/unit/desktop/test_desktop_vdm_degradation.py

from unittest.mock import MagicMock, patch

import pytest
from comtypes import COMError

from windows_use.agent.desktop.service import Desktop
from windows_use.agent.desktop.views import DesktopState, Status, Window
from windows_use.agent.tree.views import BoundingBox


def _com_error() -> COMError:
    """COMError as raised when a COM class is not registered (e.g. VDM on Win7)."""
    return COMError(-2147221164, "Class not registered", (None, None, None, None, None))


class TestDesktopVdmDegradation:
    @staticmethod
    def _mock_window() -> Window:
        return Window(
            name="Notepad",
            is_browser=False,
            depth=0,
            status=Status.NORMAL,
            bounding_box=BoundingBox(0, 0, 100, 100, 100, 100),
            handle=123,
            process_id=456,
        )

    @pytest.fixture
    def desktop(self):
        with (
            patch(
                "windows_use.agent.desktop.service.uia.GetVirtualScreenSize",
                return_value=(1920, 1080),
            ),
            patch("windows_use.agent.desktop.service.Tree"),
        ):
            return Desktop()

    def _get_state_with_vdm_error(self, desktop, error: Exception) -> DesktopState:
        mock_window = self._mock_window()
        with (
            patch.object(desktop, "get_controls_handles", return_value={123, 456}),
            patch.object(desktop, "get_windows", return_value=([mock_window], {123})),
            patch.object(desktop, "get_active_window", return_value=mock_window),
            patch.object(desktop.tree, "get_state", return_value=MagicMock()),
            patch(
                "windows_use.agent.desktop.service.get_current_desktop",
                side_effect=error,
            ),
        ):
            return desktop.get_state()

    def test_get_state_survives_comerror(self, desktop):
        """Win7/8: VDM COM class is not registered -> degrade to Default Desktop."""
        state = self._get_state_with_vdm_error(desktop, _com_error())
        assert isinstance(state, DesktopState)
        assert state.active_desktop["name"] == "Default Desktop"
        assert state.all_desktops == [state.active_desktop]

    def test_get_state_survives_runtime_error(self, desktop):
        """VDM internal manager missing -> degrade to Default Desktop."""
        state = self._get_state_with_vdm_error(
            desktop, RuntimeError("Internal VDM not initialized")
        )
        assert isinstance(state, DesktopState)
        assert state.active_desktop["name"] == "Default Desktop"

    def test_get_state_survives_oserror(self, desktop):
        """COM activation failure surfacing as OSError -> degrade to Default Desktop."""
        state = self._get_state_with_vdm_error(
            desktop, OSError(-2147221164, "Class not registered")
        )
        assert isinstance(state, DesktopState)
        assert state.active_desktop["name"] == "Default Desktop"
