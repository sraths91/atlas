# Fleet Monitoring Packages

## 📦 Two Separate Packages

The fleet monitoring system is split into two independent, distributable packages:

### 1. **Fleet Agent** (`mac-fleet-agent`)
Runs on each Mac being monitored. Collects and reports metrics.

### 2. **Fleet Server** (`mac-fleet-server`)
Central server that receives data and provides dashboard.

---

## 🏗️ Package Structure

```
windsurf-project-2/
├── fleet-agent/                    # Agent Package
│   ├── fleet_agent/
│   │   ├── __init__.py
│   │   └── agent.py               # Main agent code
│   ├── setup.py                   # Package configuration
│   ├── README.md                  # Agent documentation
│   ├── requirements.txt           # Dependencies
│   ├── MANIFEST.in               # Package manifest
│   └── build.sh                  # Build script
│
└── fleet-server/                  # Server Package
    ├── fleet_server/
    │   ├── __init__.py
    │   ├── server.py             # Main server code
    │   └── config.py             # Configuration management
    ├── setup.py                  # Package configuration
    ├── README.md                 # Server documentation
    ├── requirements.txt          # Dependencies
    ├── MANIFEST.in              # Package manifest
    └── build.sh                 # Build script
```

---

## 🚀 Quick Start

### Install Agent on Macs

```bash
# From PyPI (when published)
pip3 install mac-fleet-agent

# From local build
cd fleet-agent
pip3 install .

# Start agent
fleet-agent --server http://fleet-server:8768 --api-key YOUR_KEY
```

### Install Server

```bash
# From PyPI (when published)
pip3 install mac-fleet-server

# From local build
cd fleet-server
pip3 install .

# Run setup wizard
fleet-config

# Start server
fleet-server --config ~/.fleet-config.json
```

---

## 🔨 Building Packages

### Build Agent Package

```bash
cd fleet-agent
./build.sh
```

**Output:**
- `dist/mac_fleet_agent-1.0.0-py3-none-any.whl` (Wheel)
- `dist/mac-fleet-agent-1.0.0.tar.gz` (Source)

### Build Server Package

```bash
cd fleet-server
./build.sh
```

**Output:**
- `dist/mac_fleet_server-1.0.0-py3-none-any.whl` (Wheel)
- `dist/mac-fleet-server-1.0.0.tar.gz` (Source)

---

## 📤 Distribution Methods

### Method 1: PyPI (Public)

```bash
# Build packages
cd fleet-agent && ./build.sh
cd ../fleet-server && ./build.sh

# Upload to PyPI
cd fleet-agent
twine upload dist/*

cd ../fleet-server
twine upload dist/*
```

**Users install with:**
```bash
pip3 install mac-fleet-agent
pip3 install mac-fleet-server
```

### Method 2: Private PyPI Server

```bash
# Upload to private server
twine upload --repository-url https://pypi.company.com dist/*
```

**Users configure:**
```bash
pip3 install --index-url https://pypi.company.com mac-fleet-agent
```

### Method 3: Direct File Distribution

```bash
# Build packages
./build.sh

# Distribute .whl files
# Users install with:
pip3 install mac_fleet_agent-1.0.0-py3-none-any.whl
```

### Method 4: Git Repository

```bash
# Users install directly from git
pip3 install git+https://github.com/company/mac-fleet-agent.git
pip3 install git+https://github.com/company/mac-fleet-server.git
```

### Method 5: Jamf Pro

Package the .whl file with installation script:

```bash
#!/bin/bash
# Install agent via Jamf
pip3 install /path/to/mac_fleet_agent-1.0.0-py3-none-any.whl
fleet-agent --config /etc/fleet-agent/config.json
```

---

## 📋 Installation Examples

### Agent Installation

#### Basic Install
```bash
pip3 install mac-fleet-agent
fleet-agent --server http://server:8768 --api-key KEY
```

#### With Config File
```bash
pip3 install mac-fleet-agent

# Create config
mkdir -p ~/.fleet-agent
cat > ~/.fleet-agent/config.json << EOF
{
  "server_url": "http://fleet-server:8768",
  "api_key": "your-api-key",
  "report_interval": 10
}
EOF

# Start agent
fleet-agent --config ~/.fleet-agent/config.json
```

#### Development Install
```bash
cd fleet-agent
pip3 install -e .  # Editable install
fleet-agent --server http://localhost:8768
```

### Server Installation

#### Basic Install
```bash
pip3 install mac-fleet-server
fleet-config  # Run setup wizard
fleet-server --config ~/.fleet-config.json
```

#### Quick Start
```bash
pip3 install mac-fleet-server
fleet-server --port 8768 --api-key $(openssl rand -hex 32)
```

#### Development Install
```bash
cd fleet-server
pip3 install -e .  # Editable install
fleet-server --port 8768
```

---

## 🎯 Command-Line Tools

### Agent Commands

After installing `mac-fleet-agent`:

```bash
# Start agent
fleet-agent --server URL --api-key KEY

# With config file
fleet-agent --config ~/.fleet-agent/config.json

# Debug mode
fleet-agent --server URL --debug

# Custom machine ID
fleet-agent --server URL --machine-id "MacBook-Sales-1"

# Help
fleet-agent --help
```

### Server Commands

After installing `mac-fleet-server`:

```bash
# Run setup wizard
fleet-config

# Start server
fleet-server --config ~/.fleet-config.json

# Quick start
fleet-server --port 8768 --api-key KEY

# Debug mode
fleet-server --config ~/.fleet-config.json --debug

# Help
fleet-server --help
fleet-config --help
```

---

## 📦 Package Details

### Agent Package

**Name:** `mac-fleet-agent`
**Version:** 1.0.0
**Dependencies:**
- `psutil>=5.9.0`
- `requests>=2.28.0`

**Entry Points:**
- `fleet-agent` - Main agent command

**Size:** ~50 KB (wheel)

### Server Package

**Name:** `mac-fleet-server`
**Version:** 1.0.0
**Dependencies:**
- `psutil>=5.9.0`

**Entry Points:**
- `fleet-server` - Main server command
- `fleet-config` - Configuration wizard

**Size:** ~100 KB (wheel)

---

## 🔧 Deployment Scenarios

### Scenario 1: Small Office (10-20 Macs)

**Server:**
```bash
# On any Mac or Linux machine
pip3 install mac-fleet-server
fleet-config
fleet-server --config ~/.fleet-config.json
```

**Agents:**
```bash
# On each Mac
pip3 install mac-fleet-agent
fleet-agent --server http://server-ip:8768 --api-key KEY
```

### Scenario 2: Enterprise (100+ Macs)

**Server:**
```bash
# On dedicated server/VM
pip3 install mac-fleet-server
fleet-server --config /etc/fleet-server/config.json
```

**Agents via Jamf:**
1. Build agent package
2. Create Jamf policy with installation script
3. Deploy to all Macs

### Scenario 3: MSP (Multiple Clients)

**Servers:**
```bash
# Client A
pip3 install mac-fleet-server
fleet-server --config /etc/fleet/client-a.json --port 8768

# Client B
fleet-server --config /etc/fleet/client-b.json --port 8769

# Client C
fleet-server --config /etc/fleet/client-c.json --port 8770
```

**Agents:**
Each client's Macs connect to their respective server.

---

## 🔄 Updates

### Update Agent

```bash
pip3 install --upgrade mac-fleet-agent
```

### Update Server

```bash
pip3 install --upgrade mac-fleet-server
```

### Check Version

```bash
pip3 show mac-fleet-agent
pip3 show mac-fleet-server
```

---

## 🗑️ Uninstallation

### Uninstall Agent

```bash
# Stop agent
pkill -f fleet-agent

# Uninstall package
pip3 uninstall mac-fleet-agent

# Remove config
rm -rf ~/.fleet-agent
```

### Uninstall Server

```bash
# Stop server
pkill -f fleet-server

# Uninstall package
pip3 uninstall mac-fleet-server

# Remove config
rm -rf ~/.fleet-config.json
```

---

## 📝 Version Management

### Semantic Versioning

Both packages follow semantic versioning:
- **1.0.0** - Initial release
- **1.0.1** - Patch (bug fixes)
- **1.1.0** - Minor (new features, backward compatible)
- **2.0.0** - Major (breaking changes)

### Update Version

Edit `setup.py` in each package:

```python
setup(
    name="mac-fleet-agent",
    version="1.0.1",  # Update here
    ...
)
```

Then rebuild:
```bash
./build.sh
```

---

## 🧪 Testing Packages

### Test Agent Package

```bash
# Create virtual environment
python3 -m venv test-env
source test-env/bin/activate

# Install package
pip install dist/mac_fleet_agent-1.0.0-py3-none-any.whl

# Test command
fleet-agent --help

# Cleanup
deactivate
rm -rf test-env
```

### Test Server Package

```bash
# Create virtual environment
python3 -m venv test-env
source test-env/bin/activate

# Install package
pip install dist/mac_fleet_server-1.0.0-py3-none-any.whl

# Test commands
fleet-server --help
fleet-config --help

# Cleanup
deactivate
rm -rf test-env
```

---

## 📚 Documentation

### Agent Documentation
- **README.md** - Installation and usage
- **--help** - Command-line help
- **ENHANCED_METRICS_GUIDE.md** - Metrics details

### Server Documentation
- **README.md** - Installation and usage
- **--help** - Command-line help
- **MULTI_TENANT_GUIDE.md** - Multi-tenant setup
- **FLEET_DEPLOYMENT.md** - Deployment guide

---

## 🎯 Distribution Checklist

### Before Release

- [ ] Update version numbers
- [ ] Update README files
- [ ] Test installation in clean environment
- [ ] Test agent-server communication
- [ ] Verify all dependencies
- [ ] Check command-line tools work
- [ ] Build packages successfully
- [ ] Run package checks (twine check)

### Release Process

1. **Build packages**
   ```bash
   cd fleet-agent && ./build.sh
   cd ../fleet-server && ./build.sh
   ```

2. **Test packages**
   ```bash
   # Test in virtual environment
   ```

3. **Upload to PyPI** (or private server)
   ```bash
   twine upload dist/*
   ```

4. **Tag release**
   ```bash
   git tag -a v1.0.0 -m "Release 1.0.0"
   git push origin v1.0.0
   ```

5. **Update documentation**
   - Release notes
   - Installation guides
   - Migration guides (if needed)

---

## 🚀 Quick Commands Reference

### Build Both Packages
```bash
cd fleet-agent && ./build.sh && cd ..
cd fleet-server && ./build.sh && cd ..
```

### Install Both Locally
```bash
pip3 install fleet-agent/dist/*.whl
pip3 install fleet-server/dist/*.whl
```

### Test Complete System
```bash
# Terminal 1: Start server
fleet-server --port 8768 --api-key test-key

# Terminal 2: Start agent
fleet-agent --server http://localhost:8768 --api-key test-key

# Browser: Open dashboard
open http://localhost:8768/dashboard
```

---

## 📞 Support

- **Agent Issues:** Check agent logs, verify connectivity
- **Server Issues:** Check server logs, verify port availability
- **Build Issues:** Ensure build dependencies installed
- **Install Issues:** Check Python version (>=3.8)

---

## ✅ Summary

**Two independent packages:**
1. ✅ **mac-fleet-agent** - Runs on monitored Macs
2. ✅ **mac-fleet-server** - Central monitoring server

**Easy distribution:**
- PyPI (public or private)
- Direct file distribution
- Git repository
- Jamf Pro integration

**Simple installation:**
- `pip3 install mac-fleet-agent`
- `pip3 install mac-fleet-server`

**Professional packaging:**
- Proper setup.py
- Dependencies managed
- Command-line tools
- Complete documentation

**Ready for production deployment!** 🎉
