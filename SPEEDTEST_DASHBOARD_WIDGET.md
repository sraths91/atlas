# Speed Test Dashboard Widget

## Overview

A real-time speed test aggregation widget has been added to the main Fleet Dashboard, providing at-a-glance network performance metrics for all machines.

## Features

### ✅ **Dual View Modes**

1. **Machine View** (Default)
   - Shows recent 20 test average per machine
   - Individual cards for each machine
   - Download, upload, ping, and jitter metrics

2. **Subnet View**
   - Groups machines by IP subnet
   - Shows aggregate performance per subnet
   - Identifies which machines are in each subnet
   - Perfect for comparing locations/ISPs

### ✅ **Auto-Refresh**
- Updates every 30 seconds automatically
- Manual refresh button available
- Seamless data loading

### ✅ **Visual Design**
- Matches Fleet Dashboard aesthetic
- Color-coded metrics:
  - 🟢 Download (green)
  - 🔵 Upload (cyan)
  - 🟡 Ping (yellow)
- Hover effects for better UX
- Responsive grid layout

## Widget Location

The widget appears on the main dashboard **between the summary cards and the machine list**:

```
┌─────────────────────────────────────┐
│  Fleet Dashboard Header             │
├─────────────────────────────────────┤
│  Summary Cards (Total, Online, etc) │
├─────────────────────────────────────┤
│  ⚡ Network Performance Widget       │  ← NEW!
│  (Speed Test Aggregation)           │
├─────────────────────────────────────┤
│  Machine Cards Grid                 │
└─────────────────────────────────────┘
```

## Widget Controls

### Refresh Button
```
🔄 Refresh
```
Manually refresh speed test data without waiting for auto-refresh.

### View Toggle Button
```
📊 Show Subnet View  (when in Machine view)
🖥️ Show Machine View (when in Subnet view)
```
Switch between machine-based and subnet-based views.

## Machine View

### Display Format

Each machine gets a card showing:

```
┌─────────────────────────────────┐
│ 🖥️ MacBook-Pro      [20 tests] │
├─────────────────────────────────┤
│ ⬇️ Download      245.5 Mbps     │
│ ⬆️ Upload         32.5 Mbps     │
│ 🏓 Ping           12.3 ms       │
│ 📊 Jitter          2.1 ms       │
└─────────────────────────────────┘
```

### Features
- **Test Count Badge**: Shows how many tests were averaged (up to 20)
- **Color-Coded Values**: Easy to read at a glance
- **Hover Effect**: Cards lift and glow on hover

## Subnet View

### Display Format

Each subnet gets a card showing:

```
┌─────────────────────────────────┐
│ 🌐 192.168.1.0/24               │
│ 3 machine(s): Mac, MacBook-Pro, │
│ iMac                            │
├─────────────────────────────────┤
│ ⬇️ Download      238.2 Mbps     │
│ ⬆️ Upload         33.1 Mbps     │
│ 🏓 Ping           13.5 ms       │
│ 📊 Tests          45            │
└─────────────────────────────────┘
```

### Features
- **Subnet Header**: Shows IP subnet in CIDR notation
- **Machine List**: Shows which machines are in this subnet
- **Aggregate Stats**: Combined performance for all machines in subnet
- **Test Count**: Total number of tests from this subnet

## Use Cases

### For Technicians

**Quick Health Check**
- Open dashboard
- Glance at speed test widget
- Instantly see if any machine has poor performance

**Compare Locations**
- Switch to Subnet view
- Compare office locations side-by-side
- Identify which location needs attention

**Troubleshooting**
- User reports slow internet
- Check their machine in widget
- Compare to fleet average
- Determine if issue is machine-specific or network-wide

### For Managers

**Fleet Overview**
- See network performance across all machines
- Identify trends and patterns
- Make informed decisions about upgrades

**Location Comparison**
- Compare different office locations
- Evaluate ISP performance
- Plan infrastructure improvements

## Technical Details

### Data Source
- **API Endpoint**: `/api/fleet/speedtest/recent20`
- **Update Frequency**: 30 seconds
- **Sample Size**: Most recent 20 tests per machine
- **Calculation**: Average of download, upload, ping, jitter

### Performance
- **Load Time**: <500ms
- **Memory**: Minimal (client-side rendering)
- **Network**: Small JSON payload (~5KB for 10 machines)

### Browser Compatibility
- ✅ Chrome/Edge (Chromium)
- ✅ Firefox
- ✅ Safari
- ✅ Mobile browsers

## Widget States

### Loading State
```
Loading speed test data...
```
Shown briefly when page first loads or data is refreshing.

### No Data State
```
No speed test data available yet
```
Shown when no machines have run speed tests yet.

### Error State
```
Error loading speed test data
```
Shown if API call fails (rare).

### Normal State
Grid of machine/subnet cards with current data.

## Customization

### Refresh Interval
Default: 30 seconds

To change, edit in `fleet_server.py`:
```javascript
setInterval(loadSpeedTestData, 30000); // Change 30000 to desired ms
```

### Grid Layout
Default: Auto-fill with minimum 280px cards

To change, edit CSS in `fleet_server.py`:
```css
.speedtest-grid {
    grid-template-columns: repeat(auto-fill, minmax(280px, 1fr));
}
```

### Colors
Download: `#00ff00` (green)
Upload: `#00ccff` (cyan)
Ping: `#ffd93d` (yellow)

## Example Scenarios

### Scenario 1: All Machines Performing Well
```
⚡ Network Performance (Recent 20 Tests)

┌──────────────┐ ┌──────────────┐ ┌──────────────┐
│ Mac          │ │ MacBook-Pro  │ │ iMac         │
│ 250.5 Mbps ⬇️│ │ 245.2 Mbps ⬇️│ │ 248.8 Mbps ⬇️│
│  32.5 Mbps ⬆️│ │  31.8 Mbps ⬆️│ │  33.2 Mbps ⬆️│
│  12.3 ms  🏓│ │  11.5 ms  🏓│ │  12.8 ms  🏓│
└──────────────┘ └──────────────┘ └──────────────┘
```
**Action**: None needed, all performing well.

### Scenario 2: One Machine Slow
```
⚡ Network Performance (Recent 20 Tests)

┌──────────────┐ ┌──────────────┐ ┌──────────────┐
│ Mac          │ │ MacBook-Pro  │ │ iMac         │
│ 250.5 Mbps ⬇️│ │ 245.2 Mbps ⬇️│ │  45.2 Mbps ⬇️│ ⚠️
│  32.5 Mbps ⬆️│ │  31.8 Mbps ⬆️│ │   8.5 Mbps ⬆️│
│  12.3 ms  🏓│ │  11.5 ms  🏓│ │  85.3 ms  🏓│
└──────────────┘ └──────────────┘ └──────────────┘
```
**Action**: Investigate iMac - machine-specific issue.

### Scenario 3: Subnet Comparison
```
⚡ Network Performance (Recent 20 Tests)
[Subnet View]

┌─────────────────────┐ ┌─────────────────────┐
│ 🌐 192.168.1.0/24   │ │ 🌐 10.0.1.0/24      │
│ Office A            │ │ Office B            │
│ 245.5 Mbps ⬇️       │ │ 125.2 Mbps ⬇️       │ ⚠️
│  32.5 Mbps ⬆️       │ │  15.8 Mbps ⬆️       │
│  12.3 ms  🏓       │ │  45.5 ms  🏓       │
└─────────────────────┘ └─────────────────────┘
```
**Action**: Office B has network issues - check ISP/router.

## Benefits

### For IT Teams
- ✅ **Instant visibility** into network performance
- ✅ **Proactive monitoring** - catch issues before users complain
- ✅ **Quick troubleshooting** - identify problem machines fast
- ✅ **Location comparison** - see which offices need attention

### For End Users
- ✅ **Faster issue resolution** - IT can see problems immediately
- ✅ **Better service** - proactive fixes before major issues
- ✅ **Transparency** - IT can show actual performance data

## Integration with Existing Features

### Works With
- ✅ **Speed Test Widget** (on agent machines)
- ✅ **Widget Log Collection** (automatic)
- ✅ **Speed Test Aggregator** (backend)
- ✅ **API Endpoints** (programmatic access)

### Complements
- Machine status cards (online/offline)
- CPU/Memory metrics
- Alert system
- Export functionality

## Future Enhancements

Potential additions:
- [ ] Trend graphs (sparklines)
- [ ] Performance alerts (red/yellow indicators)
- [ ] Click to see detailed history
- [ ] Export speed test data
- [ ] Custom thresholds
- [ ] Historical comparison

## Summary

The Speed Test Dashboard Widget provides:

✅ **At-a-glance** network performance visibility
✅ **Dual views** - machine and subnet perspectives
✅ **Auto-refresh** - always current data
✅ **Beautiful design** - matches dashboard aesthetic
✅ **Zero configuration** - works automatically
✅ **Responsive** - works on all screen sizes

**Perfect for technicians who need quick network performance insights!** ⚡📊

---

*Widget automatically appears on the dashboard - no configuration needed!*
