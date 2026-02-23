# 🔍 Web Viewer Debugging Guide

## Issue: Display Not Updating When Browser is Focused

### Problem
When you click on the web browser tab, the display image stops updating and appears "frozen" or "locked" to the current PNG.

### Root Cause Analysis

The issue was caused by the `visibilitychange` event handler that was **clearing the update interval** when the browser thought the page was hidden:

```javascript
// PROBLEMATIC CODE (removed):
document.addEventListener('visibilitychange', function() {
    if (document.hidden) {
        clearInterval(intervalId);  // ❌ This stops updates
    } else {
        intervalId = setInterval(updateDisplay, refreshInterval);
        updateDisplay();
    }
});
```

### Why This Happened

1. **Browser behavior**: Some browsers trigger `visibilitychange` events unexpectedly
2. **Focus vs Visibility**: Clicking on the browser doesn't always mean the page is "visible" according to the API
3. **Interval clearing**: Once cleared, the interval might not restart properly

### Solution Applied

1. ✅ **Removed visibility change handler** - Let updates run continuously
2. ✅ **Added comprehensive logging** - Debug what's happening in real-time
3. ✅ **Improved fetch implementation** - Better cache busting with blob URLs

### Updated Code

```javascript
// Start auto-refresh
intervalId = setInterval(updateDisplay, refreshInterval);

// Initial update
updateDisplay();

// Debug logging
console.log('Auto-refresh started with interval:', refreshInterval, 'ms');

// Keep updating even when tab is in background
// (removed visibilitychange handler that was causing issues)
```

### Testing

#### Option 1: Use the Main Web Viewer
Open: **http://localhost:8765**

Then open browser console (F12 or Cmd+Option+I) and look for:
```
Auto-refresh started with interval: 1000 ms
Fetching image #1 at 6:31:40 AM
Response received, size: 14009 bytes
Image blob created, updating src
Image loaded successfully #1
Fetching image #2 at 6:31:41 AM
...
```

#### Option 2: Use the Test Viewer
Open: **file:///Users/samraths/CascadeProjects/windsurf-project-2/test_viewer.html**

This provides:
- ✅ Visual console log on the page
- ✅ Update counter
- ✅ Load counter
- ✅ Status indicator
- ✅ Detailed logging of every fetch

### Verification Steps

1. **Start the app:**
   ```bash
   python3 -m atlas.app --simulated --theme cyberpunk --refresh-rate 1.0
   ```

2. **Open web viewer:**
   - Main: http://localhost:8765
   - Test: file:///Users/samraths/CascadeProjects/windsurf-project-2/test_viewer.html

3. **Check console logs:**
   - Press F12 (or Cmd+Option+I on Mac)
   - Go to Console tab
   - You should see logs every second

4. **Verify updates:**
   - Watch the "Updates" counter increment
   - Watch the "Loaded" counter increment
   - CPU/RAM/GPU values should change
   - Network graph should animate

### What to Look For

#### ✅ Good Signs
```
Fetching image #1 at 6:31:40 AM
Response received, size: 14009 bytes
Image blob created, updating src
Image loaded successfully #1
```

#### ❌ Bad Signs
```
Update skipped - paused
Failed to fetch image: TypeError: Failed to fetch
Response received, size: null bytes
```

### Troubleshooting

#### Problem: Updates Counter Increments But Image Doesn't Change

**Possible Causes:**
1. App not updating the preview file
2. Browser caching despite no-cache headers
3. Image load error

**Solution:**
```bash
# Check if file is updating
watch -n 1 'ls -l /tmp/atlas_preview.png'

# Check if app is running
ps aux | grep atlas

# Check web server logs
# Look for "Request: GET /preview" messages
```

#### Problem: No Console Logs Appearing

**Possible Causes:**
1. Console not open
2. JavaScript error preventing execution
3. Page not loaded properly

**Solution:**
1. Open browser console (F12)
2. Refresh the page (Cmd+R or Ctrl+R)
3. Check for any red error messages

#### Problem: Fetch Errors

**Possible Causes:**
1. Web server not running
2. Port 8765 blocked
3. CORS issues (for test_viewer.html)

**Solution:**
```bash
# Check if web server is running
lsof -i :8765

# Test endpoint directly
curl -I http://localhost:8765/preview

# Restart app
pkill -f atlas
python3 -m atlas.app --simulated --refresh-rate 1.0
```

### Performance Notes

#### Update Frequency
- **1000ms (1 second)**: Recommended for normal use
- **500ms (0.5 seconds)**: Smooth updates, higher CPU
- **2000ms (2 seconds)**: Battery saving mode

#### Browser Performance
- **Blob URLs**: Efficient, no memory leaks
- **Fetch API**: Better than img.src for cache control
- **Continuous updates**: Works even in background tabs

### Advanced Debugging

#### Enable Verbose Logging

The web viewer now includes comprehensive logging:

```javascript
console.log('Fetching image #' + updateCount + ' at', new Date().toLocaleTimeString());
console.log('Response received, size:', response.headers.get('content-length'), 'bytes');
console.log('Image blob created, updating src');
console.log('Image loaded successfully #' + imageLoadCount);
```

#### Monitor Network Traffic

1. Open browser DevTools (F12)
2. Go to Network tab
3. Filter by "preview"
4. Watch requests every second
5. Check response sizes and timing

#### Check Image Changes

```bash
# Watch file modification time
watch -n 0.5 'stat -f "%Sm" -t "%H:%M:%S" /tmp/atlas_preview.png'

# Compare consecutive images
cp /tmp/atlas_preview.png /tmp/prev1.png
sleep 1
cp /tmp/atlas_preview.png /tmp/prev2.png
diff /tmp/prev1.png /tmp/prev2.png
```

### Summary

✅ **Fixed Issues:**
- Removed problematic visibility change handler
- Added comprehensive console logging
- Improved fetch implementation with blob URLs
- Better error handling and status display

✅ **Current Status:**
- Web viewer updates continuously
- No pausing when browser is focused
- Detailed logging for debugging
- Test viewer available for verification

✅ **How to Verify:**
1. Open http://localhost:8765
2. Open browser console (F12)
3. Watch for log messages every second
4. Verify image updates visually
5. Check update/load counters increment

The web viewer should now update smoothly regardless of browser focus! 🎉
