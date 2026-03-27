"""
Unit Tests for atlas.monitors_registry

Tests the lazy-loading monitor registry: get_monitor, is_available,
caching behavior, and error handling.
"""
import pytest
from unittest.mock import patch, MagicMock


@pytest.fixture(autouse=True)
def clear_cache():
    """Clear the module-level _MONITORS cache before and after each test."""
    from atlas import monitors_registry
    monitors_registry._MONITORS.clear()
    yield
    monitors_registry._MONITORS.clear()


@pytest.mark.unit
class TestMonitorsRegistry:
    """Tests for the monitors_registry module."""

    def test_get_known_monitor(self):
        """get_monitor returns the imported instance and caches it."""
        from atlas import monitors_registry

        mock_instance = MagicMock(name='power_monitor_instance')
        mock_importer = MagicMock(return_value=mock_instance)

        with patch.dict(monitors_registry._IMPORTERS, {'power': mock_importer}):
            result = monitors_registry.get_monitor('power')
            assert result is mock_instance
            mock_importer.assert_called_once()

            # Second call should return cached version without re-importing
            result2 = monitors_registry.get_monitor('power')
            assert result2 is mock_instance
            mock_importer.assert_called_once()  # still only one call

    def test_get_unknown_monitor(self):
        """get_monitor returns None for an unrecognized monitor name."""
        from atlas import monitors_registry

        result = monitors_registry.get_monitor('nonexistent')
        assert result is None

    def test_get_monitor_import_error(self):
        """get_monitor returns None when the importer raises ImportError."""
        from atlas import monitors_registry

        mock_importer = MagicMock(side_effect=ImportError("no module"))

        with patch.dict(monitors_registry._IMPORTERS, {'broken': mock_importer}):
            result = monitors_registry.get_monitor('broken')
            assert result is None

    def test_is_available_true(self):
        """is_available returns True when get_monitor returns a non-None value."""
        from atlas import monitors_registry

        mock_instance = MagicMock(name='display_monitor_instance')
        mock_importer = MagicMock(return_value=mock_instance)

        with patch.dict(monitors_registry._IMPORTERS, {'display': mock_importer}):
            assert monitors_registry.is_available('display') is True

    def test_is_available_false_unknown(self):
        """is_available returns False for an unknown monitor name."""
        from atlas import monitors_registry

        assert monitors_registry.is_available('nonexistent') is False

    def test_is_available_false_import_error(self):
        """is_available returns False when the monitor fails to import."""
        from atlas import monitors_registry

        mock_importer = MagicMock(side_effect=ImportError("missing dep"))

        with patch.dict(monitors_registry._IMPORTERS, {'unavailable': mock_importer}):
            assert monitors_registry.is_available('unavailable') is False

    def test_caching(self):
        """get_monitor called twice with the same name only invokes the importer once."""
        from atlas import monitors_registry

        mock_instance = MagicMock(name='disk_monitor_instance')
        mock_importer = MagicMock(return_value=mock_instance)

        with patch.dict(monitors_registry._IMPORTERS, {'disk': mock_importer}):
            monitors_registry.get_monitor('disk')
            monitors_registry.get_monitor('disk')
            monitors_registry.get_monitor('disk')
            mock_importer.assert_called_once()

    def test_get_monitor_generic_exception(self):
        """get_monitor returns None when the importer raises a non-ImportError exception."""
        from atlas import monitors_registry

        mock_importer = MagicMock(side_effect=RuntimeError("init failed"))

        with patch.dict(monitors_registry._IMPORTERS, {'failing': mock_importer}):
            result = monitors_registry.get_monitor('failing')
            assert result is None

    def test_cache_stores_none_for_failed_import(self):
        """After a failed import, the None result is cached (importer not retried)."""
        from atlas import monitors_registry

        mock_importer = MagicMock(side_effect=ImportError("missing"))

        with patch.dict(monitors_registry._IMPORTERS, {'flaky': mock_importer}):
            result1 = monitors_registry.get_monitor('flaky')
            assert result1 is None

            result2 = monitors_registry.get_monitor('flaky')
            assert result2 is None
            # Importer should only be called once; second call uses cached None
            mock_importer.assert_called_once()
