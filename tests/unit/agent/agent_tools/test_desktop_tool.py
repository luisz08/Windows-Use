# tests/unit/agent/agent_tools/test_desktop_tool.py

from unittest.mock import patch

from windows_use.agent.tools.service import desktop_tool


class TestDesktopToolVdmAvailability:
    def test_unavailable_vdm_returns_clear_error(self):
        """Win7/8: no virtual desktops -> clear, actionable error message."""
        with patch("windows_use.agent.tools.service.is_vdm_available", return_value=False):
            result = desktop_tool.invoke(action="create")

        assert isinstance(result, str)
        assert "not supported" in result
        assert "17763" in result

    def test_unavailable_vdm_error_for_every_action(self):
        for action in ("create", "remove", "rename", "switch"):
            with patch("windows_use.agent.tools.service.is_vdm_available", return_value=False):
                result = desktop_tool.invoke(action=action, desktop_name="Work")
            assert result.startswith("Error: Virtual desktops are not supported"), (
                f"action={action} returned: {result}"
            )

    def test_available_vdm_proceeds_to_action(self):
        """Normal path (Win10/11): availability check passes through to the action."""
        with (
            patch(
                "windows_use.agent.tools.service.is_vdm_available", return_value=True
            ) as mock_avail,
            patch("windows_use.agent.tools.service.vdm_switch", return_value=None) as mock_switch,
        ):
            result = desktop_tool.invoke(action="switch", desktop_name="Work")

        mock_avail.assert_called_once()
        mock_switch.assert_called_once_with("Work")
        assert result == "Switched to desktop 'Work'"
