"""
Licensing Attribution Module - GPL Compliance for ATLAS Agent
Generates proper attribution notices and license documentation for bundled tools.
"""
import os
from pathlib import Path
from typing import Optional
from atlas.tool_availability import (
    get_tool_monitor,
    TOOL_REGISTRY,
    License
)


# Full license text references
LICENSE_URLS = {
    License.MIT: "https://opensource.org/licenses/MIT",
    License.APACHE_2: "https://www.apache.org/licenses/LICENSE-2.0",
    License.BSD_3: "https://opensource.org/licenses/BSD-3-Clause",
    License.GPL_2: "https://www.gnu.org/licenses/old-licenses/gpl-2.0.html",
    License.GPL_3: "https://www.gnu.org/licenses/gpl-3.0.html",
    License.LGPL_3: "https://www.gnu.org/licenses/lgpl-3.0.html",
}


def get_bundled_tools_notice() -> str:
    """
    Generate attribution notice for all tools that may be bundled with ATLAS.
    This should be included in any distribution that bundles third-party tools.
    """
    notice = """
================================================================================
ATLAS Agent - Third Party Software Notices
================================================================================

This distribution may include the following third-party software components.
Each component is subject to its own license terms as described below.

--------------------------------------------------------------------------------
PERMISSIVELY LICENSED COMPONENTS (MIT, Apache-2.0, BSD-3-Clause)
--------------------------------------------------------------------------------
These components may be freely redistributed under their respective licenses.

"""
    monitor = get_tool_monitor()

    # Permissive licenses
    for name in monitor.get_permissive_licensed_tools():
        tool = TOOL_REGISTRY[name]
        notice += f"""
{tool.name}
  License: {tool.license.value}
  URL: {LICENSE_URLS.get(tool.license, 'See license file')}
  Description: {tool.description}
  {tool.attribution or ''}
"""

    notice += """
--------------------------------------------------------------------------------
COPYLEFT LICENSED COMPONENTS (GPL-2.0, GPL-3.0, LGPL-3.0)
--------------------------------------------------------------------------------
These components are distributed under copyleft licenses. Source code is
available from the respective project websites listed below.

IMPORTANT: These binaries are distributed UNMODIFIED. No changes have been
made to the original source code. Full license text is included below.

"""
    # Copyleft licenses
    for name in monitor.get_copyleft_licensed_tools():
        tool = TOOL_REGISTRY[name]
        notice += f"""
{tool.name}
  License: {tool.license.value}
  URL: {LICENSE_URLS.get(tool.license, 'See license file')}
  Description: {tool.description}
  Source: {tool.attribution or 'See project website'}

  This software is distributed under the {tool.license.value} license.
  A complete copy of the source code is available from the project website.
  If you require a physical copy of the source code, contact the ATLAS
  development team for a written offer valid for three years.
"""

    notice += """
--------------------------------------------------------------------------------
GPL-2.0 LICENSE SUMMARY
--------------------------------------------------------------------------------
This software is free software; you can redistribute it and/or modify it
under the terms of the GNU General Public License as published by the
Free Software Foundation; either version 2 of the License, or (at your
option) any later version.

This software is distributed in the hope that it will be useful, but
WITHOUT ANY WARRANTY; without even the implied warranty of MERCHANTABILITY
or FITNESS FOR A PARTICULAR PURPOSE. See the GNU General Public License
for more details.

Full license text: https://www.gnu.org/licenses/old-licenses/gpl-2.0.html

--------------------------------------------------------------------------------
GPL-3.0 LICENSE SUMMARY
--------------------------------------------------------------------------------
This program is free software: you can redistribute it and/or modify it
under the terms of the GNU General Public License as published by the
Free Software Foundation, either version 3 of the License, or (at your
option) any later version.

This program is distributed in the hope that it will be useful, but
WITHOUT ANY WARRANTY; without even the implied warranty of MERCHANTABILITY
or FITNESS FOR A PARTICULAR PURPOSE. See the GNU General Public License
for more details.

Full license text: https://www.gnu.org/licenses/gpl-3.0.html

--------------------------------------------------------------------------------
LGPL-3.0 LICENSE SUMMARY
--------------------------------------------------------------------------------
This library is free software; you can redistribute it and/or modify it
under the terms of the GNU Lesser General Public License as published by
the Free Software Foundation; either version 3 of the License, or (at
your option) any later version.

This library is distributed in the hope that it will be useful, but
WITHOUT ANY WARRANTY; without even the implied warranty of MERCHANTABILITY
or FITNESS FOR A PARTICULAR PURPOSE. See the GNU Lesser General Public
License for more details.

Full license text: https://www.gnu.org/licenses/lgpl-3.0.html

================================================================================
"""
    return notice


def get_jamf_pkg_notices() -> str:
    """
    Generate notices specifically for Jamf PKG deployment.
    Includes compliance checklist for enterprise deployment.
    """
    return """
================================================================================
ATLAS Agent - Jamf Deployment License Compliance
================================================================================

DEPLOYMENT CHECKLIST FOR GPL COMPLIANCE:

[ ] Include THIRD_PARTY_NOTICES.txt in the PKG
[ ] Include full GPL/LGPL license text files
[ ] Do NOT modify GPL-licensed binaries
[ ] Document that binaries are unmodified Homebrew builds
[ ] Provide source code access method (URL or written offer)

SAFE FOR ENTERPRISE DEPLOYMENT (Permissive Licenses):
- iperf3 (BSD-3-Clause) - Network bandwidth testing
- bandwhich (MIT) - Per-process network monitoring
- btop (Apache-2.0) - System resource monitoring
- osquery (Apache-2.0) - Endpoint visibility and compliance
- trivy (Apache-2.0) - Security scanning

REQUIRES GPL COMPLIANCE (Copyleft Licenses):
- smartmontools (GPL-2.0) - Disk health monitoring
- mtr (GPL-2.0) - Network path analysis
- vnstat (GPL-2.0) - Network traffic history
- lynis (GPL-3.0) - Security auditing
- glances (LGPL-3.0) - System monitoring

LGPL-3.0 NOTE (glances):
LGPL allows dynamic linking without triggering copyleft requirements.
Since ATLAS uses glances as a separate process (not linked), this is
compliant. However, include the LGPL license text for completeness.

================================================================================
"""


def generate_third_party_notices_file(output_path: Optional[str] = None) -> str:
    """
    Generate THIRD_PARTY_NOTICES.txt file for distribution.

    Args:
        output_path: Path to write the file. If None, returns content only.

    Returns:
        The content of the notices file
    """
    content = get_bundled_tools_notice()
    content += "\n" + get_jamf_pkg_notices()

    if output_path:
        path = Path(output_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content)

    return content


def get_api_licensing_info() -> dict:
    """
    Get licensing information as JSON for API endpoints.
    Used by the ATLAS dashboard to display tool attribution.
    """
    monitor = get_tool_monitor()

    tools_info = []
    for name, tool in TOOL_REGISTRY.items():
        is_installed = monitor.is_tool_available(name)
        tools_info.append({
            "name": tool.name,
            "installed": is_installed,
            "license": tool.license.value,
            "license_url": LICENSE_URLS.get(tool.license),
            "description": tool.description,
            "attribution": tool.attribution,
            "license_type": "permissive" if tool.license in {
                License.MIT, License.APACHE_2, License.BSD_3
            } else "copyleft",
            "compliance_notes": _get_compliance_notes(tool.license)
        })

    return {
        "tools": tools_info,
        "compliance_summary": monitor.get_licensing_summary(),
        "notices_available": True
    }


def _get_compliance_notes(license_type: License) -> str:
    """Get brief compliance notes for a license type"""
    notes = {
        License.MIT: "Include copyright notice and license text",
        License.APACHE_2: "Include copyright notice, license text, and NOTICE file if present",
        License.BSD_3: "Include copyright notice and license text",
        License.GPL_2: "Distribute unmodified, include license, provide source access",
        License.GPL_3: "Distribute unmodified, include license, provide source access",
        License.LGPL_3: "Dynamic linking OK, include license for modifications",
    }
    return notes.get(license_type, "Check specific license terms")
