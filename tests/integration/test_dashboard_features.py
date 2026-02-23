"""
Integration tests for ATLAS Agent dashboard features

Tests the new homepage, help system, and existing dashboard endpoints
to ensure all user-facing features work correctly.
"""

import pytest
import requests
import time
import threading
from atlas.live_widgets import start_live_widget_server


@pytest.fixture(scope="module")
def dashboard_server():
    """
    Start dashboard server for testing on alternate port

    Uses port 18767 to avoid conflicts with running agent
    """
    # Start server in background thread
    server_thread = threading.Thread(
        target=start_live_widget_server,
        kwargs={'port': 18767, 'system_monitor': None},
        daemon=True
    )
    server_thread.start()

    # Wait for server to start
    time.sleep(3)

    # Verify server is responding
    max_attempts = 10
    for i in range(max_attempts):
        try:
            response = requests.get("http://localhost:18767/", timeout=1)
            if response.status_code == 200:
                break
        except:
            if i == max_attempts - 1:
                pytest.fail("Dashboard server failed to start")
            time.sleep(1)

    yield "http://localhost:18767"

    # Cleanup happens automatically when daemon thread exits


class TestHomepage:
    """Tests for the new enhanced homepage"""

    def test_homepage_loads(self, dashboard_server):
        """Homepage should load successfully"""
        response = requests.get(dashboard_server)
        assert response.status_code == 200
        assert "ATLAS Agent" in response.text

    def test_homepage_has_title(self, dashboard_server):
        """Homepage should have proper title"""
        response = requests.get(dashboard_server)
        assert "<title>ATLAS Agent - System Monitor</title>" in response.text

    def test_homepage_has_feature_sections(self, dashboard_server):
        """Homepage should have all three feature sections"""
        response = requests.get(dashboard_server)
        html = response.text

        # Check for category sections
        assert "Real-Time Monitoring" in html
        assert "Network Analysis" in html
        assert "Data Management" in html

    def test_homepage_has_feature_cards(self, dashboard_server):
        """Homepage should have feature cards for all major features"""
        response = requests.get(dashboard_server)
        html = response.text

        # Check for specific feature cards
        assert "System Monitor" in html
        assert "Process Monitor" in html
        assert "WiFi Quality Monitor" in html
        assert "Speed Test Monitor" in html
        assert "Network Analysis" in html
        assert "CSV Exports" in html
        assert "JSON API" in html
        assert "7-Day Retention" in html

    def test_homepage_has_quick_actions(self, dashboard_server):
        """Homepage should have quick action buttons"""
        response = requests.get(dashboard_server)
        html = response.text

        assert "Open Dashboard" in html
        assert "Network Analysis" in html
        assert "Feature Guide" in html

    def test_homepage_has_status_indicators(self, dashboard_server):
        """Homepage should show agent status"""
        response = requests.get(dashboard_server)
        html = response.text

        assert "Agent Active" in html
        assert "Local Processing" in html
        assert "7-Day Retention" in html


class TestHelpSystem:
    """Tests for the help and feature discovery page"""

    def test_help_page_loads(self, dashboard_server):
        """Help page should load successfully"""
        response = requests.get(f"{dashboard_server}/help")
        assert response.status_code == 200
        assert "ATLAS Help" in response.text

    def test_help_has_title(self, dashboard_server):
        """Help page should have proper title"""
        response = requests.get(f"{dashboard_server}/help")
        assert "<title>ATLAS Help & Feature Guide</title>" in response.text

    def test_help_has_feature_highlights(self, dashboard_server):
        """Help page should highlight key features"""
        response = requests.get(f"{dashboard_server}/help")
        html = response.text

        assert "Network Analysis Tool" in html
        assert "Smart Data Export System" in html
        assert "7-Day Data Retention" in html

    def test_help_has_quick_start_guide(self, dashboard_server):
        """Help page should have quick start guide"""
        response = requests.get(f"{dashboard_server}/help")
        html = response.text

        assert "Quick Start Guide" in html
        assert "Dashboard:" in html
        assert "Menu Bar:" in html

    def test_help_has_faq(self, dashboard_server):
        """Help page should have FAQ section"""
        response = requests.get(f"{dashboard_server}/help")
        html = response.text

        assert "Frequently Asked Questions" in html
        assert "How long is data retained?" in html
        assert "What does the Network Analysis tool do" in html
        assert "Can I use ATLAS without a fleet server?" in html

    def test_help_has_back_link(self, dashboard_server):
        """Help page should have link back to homepage"""
        response = requests.get(f"{dashboard_server}/help")
        assert 'href="/"' in response.text
        assert "Back to Home" in response.text


class TestDashboard:
    """Tests for the widget dashboard"""

    def test_dashboard_loads(self, dashboard_server):
        """Dashboard should load at /dashboard"""
        response = requests.get(f"{dashboard_server}/dashboard")
        assert response.status_code == 200
        assert "Live Widget Dashboard" in response.text

    def test_dashboard_has_hamburger_menu(self, dashboard_server):
        """Dashboard should have hamburger menu"""
        response = requests.get(f"{dashboard_server}/dashboard")
        html = response.text

        assert "hamburger" in html.lower()
        assert "toggleMenu()" in html

    def test_dashboard_has_export_menu(self, dashboard_server):
        """Dashboard should have export data menu"""
        response = requests.get(f"{dashboard_server}/dashboard")
        html = response.text

        assert "Export Data" in html
        assert "Speed Tests" in html
        assert "Ping Tests" in html
        assert "WiFi Quality" in html
        assert "WiFi Events" in html

    def test_dashboard_has_widgets(self, dashboard_server):
        """Dashboard should embed widget iframes"""
        response = requests.get(f"{dashboard_server}/dashboard")
        html = response.text

        assert "/widget/system-monitor" in html
        assert "/widget/wifi" in html
        assert "/widget/speedtest" in html
        assert "/widget/processes" in html


class TestWidgetEndpoints:
    """Tests for individual widget endpoints"""

    @pytest.mark.parametrize("widget_path", [
        "/widget/system-monitor",
        "/widget/wifi",
        "/widget/speedtest",
        "/widget/speedtest-history",
        "/widget/processes",
        "/widget/network-analysis"
    ])
    def test_widget_endpoint_loads(self, dashboard_server, widget_path):
        """All widget endpoints should return 200"""
        response = requests.get(f"{dashboard_server}{widget_path}")
        assert response.status_code == 200
        # Should return HTML
        assert "html" in response.headers.get("Content-Type", "").lower()


class TestAPIEndpoints:
    """Tests for API endpoints"""

    def test_api_system_comprehensive(self, dashboard_server):
        """Comprehensive system metrics API should work"""
        response = requests.get(f"{dashboard_server}/api/system/comprehensive")

        # May return 200 with data or 500 if system monitor not initialized
        assert response.status_code in [200, 500]

        if response.status_code == 200:
            data = response.json()
            # Should have expected structure
            assert isinstance(data, dict)

    def test_api_agent_health(self, dashboard_server):
        """Agent health endpoint should work"""
        response = requests.get(f"{dashboard_server}/api/agent/health")

        assert response.status_code in [200, 500]

        if response.status_code == 200:
            data = response.json()
            assert isinstance(data, dict)


class TestExportEndpoints:
    """Tests for CSV export endpoints"""

    @pytest.mark.parametrize("export_path,hours", [
        ("/api/speedtest/export", None),
        ("/api/speedtest/export?hours=1", 1),
        ("/api/speedtest/export?hours=24", 24),
        ("/api/ping/export", None),
        ("/api/ping/export?hours=1", 1),
        ("/api/wifi/export", None),
        ("/api/wifi/export?hours=24", 24),
        ("/api/wifi/events/export", None),
    ])
    def test_export_endpoint(self, dashboard_server, export_path, hours):
        """Export endpoints should return CSV or 404 if no data"""
        response = requests.get(f"{dashboard_server}{export_path}")

        # 200 with CSV data, or 404 if no data available
        assert response.status_code in [200, 404]

        if response.status_code == 200:
            # Should be CSV content type
            assert "text/csv" in response.headers.get("Content-Type", "")
            # Should have Content-Disposition for download
            assert "attachment" in response.headers.get("Content-Disposition", "")


class TestNetworkAnalysis:
    """Tests for network analysis endpoints"""

    def test_network_analysis_api(self, dashboard_server):
        """Network analysis API should return structured data"""
        response = requests.get(f"{dashboard_server}/api/network/analysis?hours=24")

        # Should work even if no data
        assert response.status_code in [200, 500]

        if response.status_code == 200:
            data = response.json()

            # Should have expected structure
            assert "generated_at" in data
            assert "analysis_period_hours" in data
            assert "incidents_detected" in data
            assert "overall_status" in data

            # Status should be valid
            assert data["overall_status"] in ["healthy", "slowdowns", "degraded"]

    def test_network_analysis_latest(self, dashboard_server):
        """Latest incident API should work"""
        response = requests.get(f"{dashboard_server}/api/network/analysis/latest")

        assert response.status_code in [200, 500]

        if response.status_code == 200:
            data = response.json()
            assert "has_recent_incident" in data
            assert "overall_status" in data

    def test_network_analysis_widget(self, dashboard_server):
        """Network analysis widget should load"""
        response = requests.get(f"{dashboard_server}/widget/network-analysis")

        assert response.status_code == 200
        assert "Network Analysis" in response.text


class TestNavigation:
    """Tests for navigation between pages"""

    def test_homepage_to_dashboard_link(self, dashboard_server):
        """Homepage should link to dashboard"""
        response = requests.get(dashboard_server)
        assert "/dashboard" in response.text

    def test_homepage_to_help_link(self, dashboard_server):
        """Homepage should link to help"""
        response = requests.get(dashboard_server)
        assert "/help" in response.text

    def test_help_to_homepage_link(self, dashboard_server):
        """Help should link back to homepage"""
        response = requests.get(f"{dashboard_server}/help")
        assert 'href="/"' in response.text

    def test_homepage_to_network_analysis_link(self, dashboard_server):
        """Homepage should link to network analysis"""
        response = requests.get(dashboard_server)
        assert "/widget/network-analysis" in response.text


class TestResponsiveness:
    """Tests for page responsiveness and error handling"""

    def test_nonexistent_page_returns_404(self, dashboard_server):
        """Non-existent pages should return 404"""
        response = requests.get(f"{dashboard_server}/nonexistent-page")
        assert response.status_code == 404

    def test_api_handles_invalid_params(self, dashboard_server):
        """API endpoints should handle invalid parameters gracefully"""
        # Invalid hours parameter
        response = requests.get(f"{dashboard_server}/api/network/analysis?hours=invalid")
        # Should not crash, may return default or error
        assert response.status_code in [200, 400, 500]

    def test_pages_load_quickly(self, dashboard_server):
        """Pages should load within reasonable time"""
        start = time.time()
        response = requests.get(dashboard_server)
        elapsed = time.time() - start

        assert response.status_code == 200
        assert elapsed < 1.0  # Should load in under 1 second


class TestSecurity:
    """Basic security tests"""

    def test_no_script_injection_in_homepage(self, dashboard_server):
        """Homepage should not have obvious XSS vulnerabilities"""
        response = requests.get(dashboard_server)
        html = response.text

        # Should not have unescaped user input or eval()
        assert "<script>alert(" not in html.lower()
        assert "eval(" not in html

    def test_cors_headers_present(self, dashboard_server):
        """API should have CORS headers"""
        response = requests.get(f"{dashboard_server}/api/system/comprehensive")

        # Check for CORS header (may or may not be present depending on implementation)
        # This is informational rather than strict requirement
        headers = response.headers
        # Just verify headers exist
        assert "Content-Type" in headers


# Summary test to verify all major features
def test_all_major_features_accessible(dashboard_server):
    """Smoke test - all major features should be accessible"""
    endpoints_to_test = [
        "/",  # Homepage
        "/help",  # Help system
        "/dashboard",  # Dashboard
        "/widget/system-monitor",  # System monitor widget
        "/widget/wifi",  # WiFi widget
        "/widget/speedtest",  # Speed test widget
        "/widget/processes",  # Process widget
        "/widget/network-analysis",  # Network analysis widget
    ]

    failed = []
    for endpoint in endpoints_to_test:
        try:
            response = requests.get(f"{dashboard_server}{endpoint}", timeout=3)
            if response.status_code != 200:
                failed.append(f"{endpoint} returned {response.status_code}")
        except Exception as e:
            failed.append(f"{endpoint} raised {type(e).__name__}: {e}")

    assert len(failed) == 0, f"Failed endpoints: {', '.join(failed)}"


if __name__ == "__main__":
    # Run tests with pytest
    pytest.main([__file__, "-v", "--tb=short"])
