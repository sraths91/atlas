"""
Fleet Server Settings Page
Certificate management and server configuration

Enhanced with modern UX/UI best practices:
- Accessibility (ARIA labels, focus states, screen reader support)
- Toast notifications instead of alerts
- Responsive design with mobile breakpoints
- CSS custom properties design system
- Improved color contrast (WCAG AA compliant)
"""

from atlas.fleet_login_page import get_base_styles, get_toast_script


def get_settings_html():
    """Generate settings page HTML"""
    # Get shared design system CSS and toast script
    base_styles = get_base_styles()
    toast_script = get_toast_script()

    # Build HTML - use string concatenation to inject shared styles
    html_start = '''<!DOCTYPE html>
<html lang="en">
<head>
    <title>Fleet Server Settings</title>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <meta name="description" content="Fleet Server configuration and certificate management">
    <meta name="theme-color" content="#0a0a0a">
    <style>
'''
    # Settings page CSS (continues after base_styles injection)
    html_rest = '''
        /* Settings Page Overrides - improved contrast */
        .cert-label {
            color: #b3b3b3;  /* WCAG AA compliant */
        }
        .status-badge {
            display: inline-block;
            padding: 5px 15px;
            border-radius: 20px;
            font-size: 12px;
            font-weight: bold;
        }
        .status-valid {
            background: rgba(0, 255, 0, 0.2);
            color: #00ff00;
        }
        .status-warning {
            background: rgba(255, 217, 61, 0.2);
            color: #ffd93d;
        }
        .status-critical {
            background: rgba(255, 68, 68, 0.2);
            color: #ff4444;
        }
        .upload-area {
            border: 2px dashed #00ff00;
            border-radius: 10px;
            padding: 40px;
            text-align: center;
            cursor: pointer;
            transition: all 0.3s;
            margin-bottom: 20px;
        }
        .upload-area:hover {
            background: rgba(0, 255, 0, 0.05);
        }
        .upload-area.dragover {
            background: rgba(0, 255, 0, 0.1);
            border-color: #00ff00;
        }
        input[type="file"] {
            display: none;
        }
        .file-label {
            color: #00ff00;
            font-size: 18px;
            margin-bottom: 10px;
        }
        .file-hint {
            color: #999;
            font-size: 14px;
        }
        .selected-file {
            background: #2a2a2a;
            padding: 10px 20px;
            border-radius: 5px;
            margin-top: 10px;
            display: inline-block;
        }
        .button {
            padding: 15px 30px;
            background: #00ff00;
            color: #000;
            border: none;
            border-radius: 10px;
            font-size: 16px;
            font-weight: bold;
            cursor: pointer;
            transition: all 0.3s;
        }
        .button:hover {
            background: #00cc00;
            transform: translateY(-2px);
        }
        .button:disabled {
            background: #666;
            cursor: not-allowed;
            transform: none;
        }
        .button-secondary {
            background: #2a2a2a;
            color: #00ff00;
            border: 2px solid #00ff00;
        }
        .button-secondary:hover {
            background: #00ff00;
            color: #000;
        }
        .message {
            padding: 15px;
            border-radius: 10px;
            margin-bottom: 20px;
            display: none;
        }
        .message.success {
            background: rgba(0, 255, 0, 0.1);
            border: 1px solid #00ff00;
            color: #00ff00;
        }
        .message.error {
            background: rgba(255, 68, 68, 0.1);
            border: 1px solid #ff4444;
            color: #ff4444;
        }
        .loading {
            display: none;
            text-align: center;
            padding: 20px;
        }
        .spinner {
            border: 3px solid #333;
            border-top: 3px solid #00ff00;
            border-radius: 50%;
            width: 40px;
            height: 40px;
            animation: spin 1s linear infinite;
            margin: 0 auto 10px;
        }
        @keyframes spin {
            0% { transform: rotate(0deg); }
            100% { transform: rotate(360deg); }
        }
        .checkbox-group {
            display: grid;
            grid-template-columns: repeat(auto-fill, minmax(250px, 1fr));
            gap: 15px;
            margin: 20px 0;
        }
        .checkbox-item {
            background: #2a2a2a;
            border: 2px solid #333;
            border-radius: 10px;
            padding: 15px;
            cursor: pointer;
            transition: all 0.3s;
        }
        .checkbox-item:hover {
            border-color: #00ff00;
        }
        .checkbox-item.selected {
            border-color: #00ff00;
            background: rgba(0, 255, 0, 0.1);
        }
        .checkbox-item input[type="checkbox"] {
            margin-right: 10px;
            width: 20px;
            height: 20px;
            cursor: pointer;
        }
        .checkbox-label {
            display: flex;
            align-items: center;
            font-size: 16px;
            font-weight: bold;
            color: #fff;
            cursor: pointer;
        }
        .checkbox-description {
            margin-top: 8px;
            font-size: 13px;
            color: #999;
            margin-left: 30px;
        }

        /* Widget Settings Panel (improved) */
        .ws-category-title {
            font-size: 11px;
            text-transform: uppercase;
            letter-spacing: 1.2px;
            color: #00ff00;
            font-weight: 600;
            margin-bottom: 8px;
            padding: 0 4px;
        }
        .ws-widget-list {
            display: flex;
            flex-direction: column;
            gap: 6px;
            margin-bottom: 20px;
        }
        .ws-widget-item {
            display: flex;
            align-items: center;
            gap: 12px;
            padding: 12px 14px;
            background: rgba(255,255,255,0.03);
            border: 1px solid transparent;
            border-radius: 12px;
            cursor: grab;
            transition: all 0.15s ease;
            user-select: none;
        }
        .ws-widget-item:active {
            cursor: grabbing;
        }
        .ws-widget-item:hover {
            background: rgba(255,255,255,0.06);
            border-color: #333;
        }
        .ws-widget-item.dragging {
            opacity: 0.5;
            border-color: #00ff00;
            background: rgba(0,255,0,0.08);
        }
        .ws-widget-item.drag-over {
            border-top: 2px solid #00ff00;
        }
        .ws-drag-handle {
            color: #555;
            font-size: 16px;
            flex-shrink: 0;
            cursor: grab;
        }
        .ws-widget-info {
            flex: 1;
            min-width: 0;
        }
        .ws-widget-name {
            font-size: 14px;
            font-weight: 600;
            color: #e0e0e0;
        }
        .ws-widget-desc {
            font-size: 12px;
            color: #777;
            margin-top: 2px;
        }
        .ws-toggle {
            position: relative;
            width: 40px;
            height: 22px;
            flex-shrink: 0;
        }
        .ws-toggle input {
            opacity: 0;
            width: 0;
            height: 0;
        }
        .ws-toggle-slider {
            position: absolute;
            top: 0; left: 0; right: 0; bottom: 0;
            background: rgba(255,255,255,0.1);
            border-radius: 11px;
            cursor: pointer;
            transition: all 0.15s ease;
        }
        .ws-toggle-slider::before {
            content: '';
            position: absolute;
            width: 16px; height: 16px;
            left: 3px; bottom: 3px;
            background: #555;
            border-radius: 50%;
            transition: all 0.15s ease;
        }
        .ws-toggle input:checked + .ws-toggle-slider {
            background: rgba(0,255,0,0.2);
        }
        .ws-toggle input:checked + .ws-toggle-slider::before {
            transform: translateX(18px);
            background: #00ff00;
        }
        .ws-actions-bar {
            display: flex;
            gap: 8px;
            margin-top: 12px;
            padding-top: 12px;
            border-top: 1px solid #333;
        }
        .ws-hint {
            font-size: 11px;
            color: #555;
            margin-top: 8px;
        }
        .config-summary {
            background: #2a2a2a;
            border-radius: 10px;
            padding: 20px;
            margin: 20px 0;
        }
        .config-summary-title {
            color: #00ff00;
            font-weight: bold;
            margin-bottom: 10px;
        }
        .config-summary-item {
            padding: 5px 0;
            color: #ccc;
        }
        .modal {
            display: none;
            position: fixed;
            z-index: 2000;
            left: 0;
            top: 0;
            width: 100%;
            height: 100%;
            background-color: rgba(0, 0, 0, 0.8);
        }
        .modal-content {
            background-color: #1a1a1a;
            margin: 10% auto;
            padding: 30px;
            border: 2px solid #00ff00;
            border-radius: 10px;
            width: 500px;
            max-width: 90%;
        }
        .modal-header {
            color: #00ff00;
            font-size: 24px;
            font-weight: bold;
            margin-bottom: 20px;
        }
        .modal-close {
            color: #999;
            float: right;
            font-size: 28px;
            font-weight: bold;
            cursor: pointer;
        }
        .modal-close:hover {
            color: #fff;
        }
    </style>
</head>
<body>
    <!-- Password Update Modal -->
    <div id="passwordUpdateModal" class="modal">
        <div class="modal-content">
            <span class="modal-close" onclick="closePasswordUpdateModal()">&times;</span>
            <div class="modal-header">Update Your Password</div>
            <p style="color: #999; margin-bottom: 20px;">
                Your current password does not meet security requirements. Please create a new password.
            </p>
            <div style="margin-bottom: 15px;">
                <label style="display: block; color: #999; margin-bottom: 5px;">New Password</label>
                <input type="password" id="modalNewPassword" placeholder="Min 12 chars, A-Z, a-z, 0-9, symbols" 
                       style="width: 100%; padding: 10px; background: #2a2a2a; border: 1px solid #00ff00; 
                              border-radius: 5px; color: #fff; font-size: 14px;">
                <div id="modalPasswordStrength" style="margin-top: 5px; font-size: 12px;"></div>
            </div>
            <div style="margin-bottom: 20px;">
                <label style="display: block; color: #999; margin-bottom: 5px;">Confirm New Password</label>
                <input type="password" id="modalConfirmPassword" placeholder="Re-enter password" 
                       style="width: 100%; padding: 10px; background: #2a2a2a; border: 1px solid #00ff00; 
                              border-radius: 5px; color: #fff; font-size: 14px;">
            </div>
            <button class="button" onclick="updatePasswordFromModal()" style="width: 100%;">
                Update Password
            </button>
        </div>
    </div>
    
    <div class="container">
        <div class="header">
            <a href="/dashboard" class="back-button">← Back to Dashboard</a>
            <h1>Fleet Server Settings</h1>
        </div>
        
        <!-- Server Resource Usage Section -->
        <div class="section">
            <div class="section-title">
                Server Resource Usage
                <span style="margin-left: auto; font-size: 12px; color: #666;">
                    Auto-refresh: <span id="resourceRefreshStatus">5s</span>
                </span>
            </div>
            
            <div id="serverResourcesInfo" style="display: grid; grid-template-columns: repeat(auto-fit, minmax(280px, 1fr)); gap: 20px;">
                <div class="loading" id="loadingResources" style="grid-column: 1 / -1;">
                    <div class="spinner"></div>
                    <div>Loading server resource information...</div>
                </div>
            </div>
        </div>
        
        <!-- Certificate Information Section -->
        <div class="section">
            <div class="section-title">
                SSL Certificate Status
            </div>
            
            <div id="certInfo" class="cert-info">
                <div class="loading" id="loadingCertInfo">
                    <div class="spinner"></div>
                    <div>Loading certificate information...</div>
                </div>
            </div>
        </div>
        
        <!-- Certificate Upload Section -->
        <div class="section">
            <div class="section-title">
                Upload New Certificate
            </div>
            
            <div id="uploadMessage" class="message"></div>
            
            <div class="upload-area" id="certUploadArea" onclick="document.getElementById('certFile').click()">
                <div class="file-label">Certificate File (.pem or .crt)</div>
                <div class="file-hint">Click to select or drag and drop</div>
                <input type="file" id="certFile" accept=".pem,.crt" onchange="handleFileSelect('cert')">
                <div id="certFileName" class="selected-file" style="display: none;"></div>
            </div>
            
            <div class="upload-area" id="keyUploadArea" onclick="document.getElementById('keyFile').click()">
                <div class="file-label">Private Key File (.pem or .key)</div>
                <div class="file-hint">Click to select or drag and drop</div>
                <input type="file" id="keyFile" accept=".pem,.key" onchange="handleFileSelect('key')">
                <div id="keyFileName" class="selected-file" style="display: none;"></div>
            </div>
            
            <div style="margin-top: 20px; display: flex; gap: 10px;">
                <button class="button" id="uploadButton" onclick="uploadCertificate()" disabled>
                    Upload Certificate
                </button>
                <button class="button button-secondary" onclick="clearFiles()">
                    Clear Selection
                </button>
            </div>
            
            <div class="loading" id="uploadingCert">
                <div class="spinner"></div>
                <div>Uploading and validating certificate...</div>
            </div>
        </div>
        
        <!-- User Management Section -->
        <div class="section">
            <div class="section-title">
                👥 User Management
            </div>
            
            <p style="color: #999; margin-bottom: 20px;">
                Manage admin users who can access the fleet dashboard and settings.
            </p>
            
            <!-- Password Requirements Info -->
            <div style="background: #2a2a2a; padding: 15px; border-radius: 8px; border-left: 4px solid #00ff00; margin-bottom: 20px;">
                <div style="color: #00ff00; font-weight: bold; margin-bottom: 10px;">Password Requirements</div>
                <div style="color: #999; font-size: 13px;">
                    All passwords must meet the following requirements:
                    <ul style="margin: 10px 0; padding-left: 20px;">
                        <li>Minimum 12 characters</li>
                        <li>At least one uppercase letter (A-Z)</li>
                        <li>At least one lowercase letter (a-z)</li>
                        <li>At least one number (0-9)</li>
                        <li>At least one symbol (!@#$%^&*()_+-=[]{}etc.)</li>
                    </ul>
                </div>
            </div>
            
            <!-- Password Update Warning -->
            <div id="passwordUpdateWarning" style="display: none; background: #ff4444; padding: 15px; border-radius: 8px; margin-bottom: 20px;">
                <div style="color: #fff; font-weight: bold; margin-bottom: 10px;">Password Update Required</div>
                <div style="color: #fff; font-size: 13px; margin-bottom: 10px;">
                    Your password does not meet current security requirements. Please update it immediately.
                </div>
                <button class="button" onclick="showPasswordUpdateModal()" style="background: #fff; color: #ff4444;">
                    Update Password Now
                </button>
            </div>
            
            <div id="userMessage" class="message"></div>
            
            <!-- Create New User -->
            <h3 style="color: #00ff00; margin: 20px 0 10px 0;">➕ Create New User</h3>
            <div style="background: #1a1a1a; padding: 20px; border-radius: 10px; margin-bottom: 20px;">
                <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 15px; margin-bottom: 15px;">
                    <div>
                        <label style="display: block; color: #999; margin-bottom: 5px;">Username</label>
                        <input type="text" id="newUsername" placeholder="Enter username" 
                               style="width: 100%; padding: 10px; background: #2a2a2a; border: 1px solid #00ff00; 
                                      border-radius: 5px; color: #fff; font-size: 14px;">
                    </div>
                    <div>
                        <label style="display: block; color: #999; margin-bottom: 5px;">Role</label>
                        <select id="newUserRole" 
                                style="width: 100%; padding: 10px; background: #2a2a2a; border: 1px solid #00ff00; 
                                       border-radius: 5px; color: #fff; font-size: 14px;">
                            <option value="admin">Admin (Full Access)</option>
                            <option value="viewer">Viewer (Read Only)</option>
                        </select>
                    </div>
                </div>
                <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 15px; margin-bottom: 15px;">
                    <div>
                        <label style="display: block; color: #999; margin-bottom: 5px;">Password</label>
                        <input type="password" id="newUserPassword" placeholder="Min 12 chars, A-Z, a-z, 0-9, symbols" 
                               style="width: 100%; padding: 10px; background: #2a2a2a; border: 1px solid #00ff00; 
                                      border-radius: 5px; color: #fff; font-size: 14px;">
                        <div id="newUserPasswordStrength" style="margin-top: 5px; font-size: 12px;"></div>
                    </div>
                    <div>
                        <label style="display: block; color: #999; margin-bottom: 5px;">Confirm Password</label>
                        <input type="password" id="newUserPasswordConfirm" placeholder="Re-enter password" 
                               style="width: 100%; padding: 10px; background: #2a2a2a; border: 1px solid #00ff00; 
                                      border-radius: 5px; color: #fff; font-size: 14px;">
                    </div>
                </div>
                <button class="button" onclick="createUser()">Create User</button>
            </div>
            
            <!-- Change Password -->
            <h3 style="color: #00ff00; margin: 20px 0 10px 0;">Change Your Password</h3>
            <div style="background: #1a1a1a; padding: 20px; border-radius: 10px; margin-bottom: 20px;">
                <div style="display: grid; grid-template-columns: 1fr 1fr 1fr; gap: 15px; margin-bottom: 15px;">
                    <div>
                        <label style="display: block; color: #999; margin-bottom: 5px;">Current Password</label>
                        <input type="password" id="currentPassword" placeholder="Enter current password" 
                               style="width: 100%; padding: 10px; background: #2a2a2a; border: 1px solid #00ff00; 
                                      border-radius: 5px; color: #fff; font-size: 14px;">
                    </div>
                    <div>
                        <label style="display: block; color: #999; margin-bottom: 5px;">New Password</label>
                        <input type="password" id="newPassword" placeholder="Min 8 characters" 
                               style="width: 100%; padding: 10px; background: #2a2a2a; border: 1px solid #00ff00; 
                                      border-radius: 5px; color: #fff; font-size: 14px;">
                    </div>
                    <div>
                        <label style="display: block; color: #999; margin-bottom: 5px;">Confirm New Password</label>
                        <input type="password" id="newPasswordConfirm" placeholder="Re-enter new password" 
                               style="width: 100%; padding: 10px; background: #2a2a2a; border: 1px solid #00ff00; 
                                      border-radius: 5px; color: #fff; font-size: 14px;">
                    </div>
                </div>
                <button class="button" onclick="changePassword()">Change Password</button>
            </div>
            
            <!-- Existing Users List -->
            <h3 style="color: #00ff00; margin: 20px 0 10px 0;">Existing Users</h3>
            <div id="usersList" style="background: #1a1a1a; padding: 20px; border-radius: 10px;">
                <div class="loading">
                    <div class="spinner"></div>
                    <div>Loading users...</div>
                </div>
            </div>
            
            <!-- Session Duration Control -->
            <h3 style="color: #00ff00; margin: 20px 0 10px 0;">Session Duration Control</h3>
            <div style="background: #1a1a1a; padding: 20px; border-radius: 10px;">
                <p style="color: #999; margin-bottom: 15px;">
                    Set automatic logout timeout for inactive sessions. Users will be signed out after the specified period of inactivity.
                </p>
                <div style="display: grid; grid-template-columns: 1fr 1fr 1fr; gap: 15px; margin-bottom: 15px;">
                    <div>
                        <label style="display: block; color: #999; margin-bottom: 5px;">Timeout Duration</label>
                        <select id="sessionTimeout" 
                                style="width: 100%; padding: 10px; background: #2a2a2a; border: 1px solid #00ff00; 
                                       border-radius: 5px; color: #fff; font-size: 14px;">
                            <option value="0">No Timeout (Always On)</option>
                            <option value="15">15 Minutes</option>
                            <option value="30" selected>30 Minutes</option>
                            <option value="60">1 Hour</option>
                            <option value="120">2 Hours</option>
                            <option value="240">4 Hours</option>
                            <option value="480">8 Hours</option>
                            <option value="1440">24 Hours</option>
                        </select>
                    </div>
                    <div>
                        <label style="display: block; color: #999; margin-bottom: 5px;">Warning Before Logout</label>
                        <select id="sessionWarning" 
                                style="width: 100%; padding: 10px; background: #2a2a2a; border: 1px solid #00ff00; 
                                       border-radius: 5px; color: #fff; font-size: 14px;">
                            <option value="0">No Warning</option>
                            <option value="1">1 Minute</option>
                            <option value="2" selected>2 Minutes</option>
                            <option value="5">5 Minutes</option>
                        </select>
                    </div>
                    <div style="display: flex; align-items: flex-end;">
                        <button class="button" onclick="saveSessionSettings()" style="width: 100%;">
                            Save Session Settings
                        </button>
                    </div>
                </div>
                <div style="background: #2a2a2a; padding: 15px; border-radius: 8px; border-left: 4px solid #00ff00;">
                    <div style="color: #00ff00; font-weight: bold; margin-bottom: 5px;">ℹ️ Current Session Info</div>
                    <div style="color: #999; font-size: 13px;">
                        <div>Session Timeout: <span id="currentTimeout" style="color: #fff;">30 Minutes</span></div>
                        <div>Warning Time: <span id="currentWarning" style="color: #fff;">2 Minutes</span></div>
                        <div>Last Activity: <span id="lastActivity" style="color: #fff;">Just now</span></div>
                    </div>
                </div>
            </div>
        </div>
        
        <!-- API Key Management Section -->
        <div class="section">
            <div class="section-title">
                API Connection Key
            </div>
            
            <p style="color: #999; margin-bottom: 20px;">
                View and manage the API key used by agents to connect to this fleet server. The key is stored securely and requires password verification to view.
            </p>
            
            <div id="apiKeyMessage" class="message"></div>
            
            <div style="background: #1a1a1a; padding: 20px; border-radius: 10px; margin-bottom: 20px;">
                <div style="background: #2a2a2a; padding: 15px; border-radius: 8px; border-left: 4px solid #00ff00; margin-bottom: 20px;">
                    <div style="color: #00ff00; font-weight: bold; margin-bottom: 10px;">Security Notice</div>
                    <div style="color: #999; font-size: 13px;">
                        The API key grants full access to report metrics to this fleet server. Keep it secure and only share it with trusted agents.
                    </div>
                </div>
                
                <div id="apiKeyHidden" style="display: block;">
                    <div style="text-align: center; padding: 30px;">
                        <div style="font-size: 48px; margin-bottom: 15px;"></div>
                        <div style="color: #999; margin-bottom: 20px;">API Key is hidden for security</div>
                        <button class="button" onclick="showApiKeyPrompt()">
                            🔓 Show API Key
                        </button>
                    </div>
                </div>
                
                <div id="apiKeyVisible" style="display: none;">
                    <div style="margin-bottom: 15px;">
                        <label style="display: block; color: #999; margin-bottom: 5px;">API Connection Key</label>
                        <div style="display: flex; gap: 10px;">
                            <input type="text" id="apiKeyDisplay" readonly
                                   style="flex: 1; padding: 12px; background: #2a2a2a; border: 1px solid #00ff00; 
                                          border-radius: 5px; color: #fff; font-family: monospace; font-size: 14px;">
                            <button class="button" onclick="copyApiKey()" style="min-width: 120px;">
                                Copy Key
                            </button>
                        </div>
                    </div>
                    
                    <div style="display: flex; gap: 10px; margin-top: 15px;">
                        <button class="button" onclick="hideApiKey()" style="background: #666;">
                            Hide Key
                        </button>
                        <button class="button" onclick="regenerateApiKey()" style="background: #ff4444;">
                            Regenerate Key (Caution!)
                        </button>
                    </div>
                    
                    <div style="background: #2a2a2a; padding: 12px; border-radius: 8px; margin-top: 15px; border-left: 4px solid #ff4444;">
                        <div style="color: #ff4444; font-weight: bold; font-size: 12px; margin-bottom: 5px;">Warning</div>
                        <div style="color: #999; font-size: 12px;">
                            Regenerating the API key will disconnect all existing agents. They will need to be reconfigured with the new key.
                        </div>
                    </div>
                </div>
            </div>
        </div>
        
        <!-- E2EE Encryption Key Section -->
        <div class="section">
            <div class="section-title">
                E2EE Encryption Key
            </div>
            
            <p style="color: #999; margin-bottom: 20px;">
                End-to-End Encryption (E2EE) key used to encrypt all data transmitted between agents and this server.
                This key is automatically included in agent packages built from this server.
            </p>
            
            <div id="encryptionKeyMessage" class="message"></div>
            
            <div style="background: #1a1a1a; padding: 20px; border-radius: 10px; margin-bottom: 20px;">
                <div style="background: #2a2a2a; padding: 15px; border-radius: 8px; border-left: 4px solid #00c8ff; margin-bottom: 20px;">
                    <div style="color: #00c8ff; font-weight: bold; margin-bottom: 10px;">About E2EE</div>
                    <div style="color: #999; font-size: 13px;">
                        E2EE encrypts agent data using AES-256-GCM before transmission. Even if network traffic is intercepted, the data remains encrypted.
                        All agents must use the same key to communicate with this server.
                    </div>
                </div>
                
                <div style="background: #2a2a2a; padding: 15px; border-radius: 8px; border-left: 4px solid #00ff00; margin-bottom: 20px;">
                    <div style="color: #00ff00; font-weight: bold; margin-bottom: 10px;">✨ Remote Key Rotation (Recommended)</div>
                    <div style="color: #999; font-size: 13px;">
                        <strong>Use "Rotate Key" to update all agents automatically:</strong><br>
                        1. Click "Rotate Key (Push to Agents)"<br>
                        2. New key is encrypted with old key and sent to agents<br>
                        3. Agents update within 60 seconds - no reinstall needed!<br>
                        <span style="color: #00ff00; margin-top: 8px; display: block;">Zero downtime key rotation</span>
                    </div>
                </div>
                
                <div id="encryptionKeyStatus">
                    <div style="text-align: center; padding: 20px;">
                        <div id="e2eeStatusIcon" style="font-size: 48px; margin-bottom: 15px;"></div>
                        <div id="e2eeStatusText" style="color: #999; margin-bottom: 20px;">Checking E2EE status...</div>
                        <button class="button" onclick="showEncryptionKeyPrompt()" id="showE2eeKeyBtn" style="display: none;">
                            🔓 Show Encryption Key
                        </button>
                        <button class="button" onclick="generateEncryptionKey()" id="generateE2eeKeyBtn" style="display: none; background: #00c8ff;">
                            Generate E2EE Key
                        </button>
                    </div>
                </div>
                
                <div id="encryptionKeyVisible" style="display: none;">
                    <div style="margin-bottom: 15px;">
                        <label style="display: block; color: #999; margin-bottom: 5px;">E2EE Encryption Key (AES-256)</label>
                        <div style="display: flex; gap: 10px;">
                            <input type="text" id="encryptionKeyDisplay" readonly
                                   style="flex: 1; padding: 12px; background: #2a2a2a; border: 1px solid #00c8ff; 
                                          border-radius: 5px; color: #fff; font-family: monospace; font-size: 14px;">
                            <button class="button" onclick="copyEncryptionKey()" style="min-width: 120px; background: #00c8ff;">
                                Copy Key
                            </button>
                        </div>
                    </div>
                    
                    <div style="display: flex; gap: 10px; margin-top: 15px; flex-wrap: wrap;">
                        <button class="button" onclick="hideEncryptionKey()" style="background: #666;">
                            Hide Key
                        </button>
                        <button class="button" onclick="rotateEncryptionKeyRemotely()" style="background: #00c8ff;">
                            Rotate Key (Push to Agents)
                        </button>
                        <button class="button" onclick="regenerateEncryptionKey()" style="background: #ff4444;">
                            Force New Key (Breaks Agents)
                        </button>
                    </div>
                    
                    <div style="background: #2a2a2a; padding: 12px; border-radius: 8px; margin-top: 15px; border-left: 4px solid #00c8ff;">
                        <div style="color: #00c8ff; font-weight: bold; font-size: 12px; margin-bottom: 5px;">Remote Key Rotation</div>
                        <div style="color: #999; font-size: 12px;">
                            <strong>"Rotate Key"</strong> securely pushes the new key to all connected agents - no reinstall needed!
                            The new key is encrypted with the current key and sent via command queue.
                        </div>
                    </div>
                    
                    <div style="background: #2a2a2a; padding: 12px; border-radius: 8px; margin-top: 10px; border-left: 4px solid #ff4444;">
                        <div style="color: #ff4444; font-weight: bold; font-size: 12px; margin-bottom: 5px;">Force New Key Warning</div>
                        <div style="color: #999; font-size: 12px;">
                            <strong>"Force New Key"</strong> generates a new key immediately without pushing to agents.
                            Use this only for new deployments or if all agents will be reinstalled.
                        </div>
                    </div>
                    
                    <!-- Key Rotation Status -->
                    <div id="keyRotationStatus" style="display: none; margin-top: 15px;">
                        <div style="background: #1a3a1a; padding: 15px; border-radius: 8px; border: 1px solid #00ff00;">
                            <div style="color: #00ff00; font-weight: bold; margin-bottom: 10px;">
                                Key Rotation Status
                                <button onclick="refreshRotationStatus()" style="float: right; background: transparent; border: 1px solid #00ff00; color: #00ff00; padding: 2px 8px; border-radius: 4px; cursor: pointer; font-size: 11px;">
                                    Refresh
                                </button>
                            </div>
                            <div id="rotationStatusList" style="color: #999; font-size: 13px;">
                                Loading...
                            </div>
                        </div>
                    </div>
                </div>
            </div>
        </div>
        
        <!-- Password Verification Modal -->
        <div id="apiKeyPasswordModal" class="modal">
            <div class="modal-content">
                <span class="modal-close" onclick="closeApiKeyPasswordModal()">&times;</span>
                <div class="modal-header">Verify Your Password</div>
                <p style="color: #999; margin-bottom: 20px;">
                    Please enter your password to view the API key.
                </p>
                <div id="apiKeyPasswordError" style="color: #ff4444; margin-bottom: 15px; display: none;"></div>
                <div style="margin-bottom: 20px;">
                    <label style="display: block; color: #999; margin-bottom: 5px;">Password</label>
                    <input type="password" id="apiKeyPassword" 
                           style="width: 100%; padding: 12px; background: #2a2a2a; border: 1px solid #00ff00; 
                                  border-radius: 5px; color: #fff; font-size: 14px;">
                </div>
                <button class="button" onclick="verifyPasswordAndShowKey()" style="width: 100%;">
                    Verify & Show Key
                </button>
            </div>
        </div>
        
        <!-- Agent Package Builder Section -->
        <div class="section">
            <div class="section-title">
                Agent Package Builder
            </div>
            
            <p style="color: #999; margin-bottom: 20px;">
                Customize which widgets and tracking tools to include in the agent installer package.
            </p>
            
            <div id="packageMessage" class="message"></div>
            
            <!-- Package Type Selection -->
            <h3 style="color: #00ff00; margin: 20px 0 10px 0;">Package Type</h3>
            <div class="checkbox-group" style="margin-bottom: 20px;">
                <div class="checkbox-item selected" onclick="togglePackageType('linked')" id="packageTypeLinked">
                    <label class="checkbox-label">
                        <input type="radio" name="packageType" id="package_linked" checked onchange="updatePackageType()">
                        Fleet-Linked Package
                    </label>
                    <div class="checkbox-description">
                        Pre-configured with this server's URL and API key. Agent connects automatically on install.
                    </div>
                </div>
                
                <div class="checkbox-item" onclick="togglePackageType('standalone')" id="packageTypeStandalone">
                    <label class="checkbox-label">
                        <input type="radio" name="packageType" id="package_standalone" onchange="updatePackageType()">
                        Standalone Package
                    </label>
                    <div class="checkbox-description">
                        No server credentials included. User configures fleet server connection after install.
                    </div>
                </div>
            </div>
            
            <!-- Standalone Configuration (hidden by default) -->
            <div id="standaloneConfig" style="display: none; background: #1a1a1a; padding: 20px; border-radius: 10px; margin-bottom: 20px; border: 1px solid #444;">
                <h4 style="color: #ffaa00; margin: 0 0 15px 0;">Standalone Package Options</h4>
                
                <div style="margin-bottom: 15px;">
                    <label class="checkbox-label" style="display: flex; align-items: center; gap: 10px;">
                        <input type="checkbox" id="standalone_include_setup_wizard" checked>
                        <span>Include Setup Wizard</span>
                    </label>
                    <div style="color: #888; font-size: 12px; margin-left: 25px;">
                        Interactive wizard to configure fleet server connection on first run
                    </div>
                </div>
                
                <div style="margin-bottom: 15px;">
                    <label class="checkbox-label" style="display: flex; align-items: center; gap: 10px;">
                        <input type="checkbox" id="standalone_include_menubar" checked>
                        <span>Include Menu Bar App</span>
                    </label>
                    <div style="color: #888; font-size: 12px; margin-left: 25px;">
                        Menu bar icon for status and quick configuration access
                    </div>
                </div>
                
                <div style="background: #2a3a2a; padding: 12px; border-radius: 8px; border-left: 3px solid #00ff00;">
                    <div style="color: #00ff00; font-size: 13px;">
                        <strong>Tip:</strong> Standalone packages are ideal for:
                        <ul style="margin: 8px 0 0 20px; color: #aaa;">
                            <li>Distributing to multiple organizations</li>
                            <li>Letting users choose their fleet server</li>
                            <li>Testing before connecting to production</li>
                        </ul>
                    </div>
                </div>
            </div>
            
            <h3 style="color: #00ff00; margin: 20px 0 10px 0;">Widgets</h3>
            <p class="ws-hint">Drag to reorder. Toggle to include/exclude from agent package.</p>
            <div class="ws-widget-list" id="widgetList">
                <div class="ws-widget-item" draggable="true" data-id="widget_system_monitor">
                    <span class="ws-drag-handle">&#9776;</span>
                    <div class="ws-widget-info">
                        <div class="ws-widget-name">System Monitor</div>
                        <div class="ws-widget-desc">CPU, RAM, GPU, disk, and network monitoring</div>
                    </div>
                    <label class="ws-toggle">
                        <input type="checkbox" id="widget_system_monitor" checked onchange="updateSelection()">
                        <span class="ws-toggle-slider"></span>
                    </label>
                </div>
                <div class="ws-widget-item" draggable="true" data-id="widget_wifi">
                    <span class="ws-drag-handle">&#9776;</span>
                    <div class="ws-widget-info">
                        <div class="ws-widget-name">WiFi Status</div>
                        <div class="ws-widget-desc">Current WiFi connection details</div>
                    </div>
                    <label class="ws-toggle">
                        <input type="checkbox" id="widget_wifi" checked onchange="updateSelection()">
                        <span class="ws-toggle-slider"></span>
                    </label>
                </div>
                <div class="ws-widget-item" draggable="true" data-id="widget_wifi_analyzer">
                    <span class="ws-drag-handle">&#9776;</span>
                    <div class="ws-widget-info">
                        <div class="ws-widget-name">WiFi Analyzer</div>
                        <div class="ws-widget-desc">WiFi signal analysis and nearby networks</div>
                    </div>
                    <label class="ws-toggle">
                        <input type="checkbox" id="widget_wifi_analyzer" checked onchange="updateSelection()">
                        <span class="ws-toggle-slider"></span>
                    </label>
                </div>
                <div class="ws-widget-item" draggable="true" data-id="widget_speedtest">
                    <span class="ws-drag-handle">&#9776;</span>
                    <div class="ws-widget-info">
                        <div class="ws-widget-name">Speed Test</div>
                        <div class="ws-widget-desc">Run and view internet speed tests</div>
                    </div>
                    <label class="ws-toggle">
                        <input type="checkbox" id="widget_speedtest" checked onchange="updateSelection()">
                        <span class="ws-toggle-slider"></span>
                    </label>
                </div>
                <div class="ws-widget-item" draggable="true" data-id="widget_speedtest_history">
                    <span class="ws-drag-handle">&#9776;</span>
                    <div class="ws-widget-info">
                        <div class="ws-widget-name">Speed Test History</div>
                        <div class="ws-widget-desc">Historical speed test results and trends</div>
                    </div>
                    <label class="ws-toggle">
                        <input type="checkbox" id="widget_speedtest_history" checked onchange="updateSelection()">
                        <span class="ws-toggle-slider"></span>
                    </label>
                </div>
                <div class="ws-widget-item" draggable="true" data-id="widget_ping">
                    <span class="ws-drag-handle">&#9776;</span>
                    <div class="ws-widget-info">
                        <div class="ws-widget-name">Ping Monitor</div>
                        <div class="ws-widget-desc">Track network latency and packet loss</div>
                    </div>
                    <label class="ws-toggle">
                        <input type="checkbox" id="widget_ping" checked onchange="updateSelection()">
                        <span class="ws-toggle-slider"></span>
                    </label>
                </div>
                <div class="ws-widget-item" draggable="true" data-id="widget_network_testing">
                    <span class="ws-drag-handle">&#9776;</span>
                    <div class="ws-widget-info">
                        <div class="ws-widget-name">Network Testing</div>
                        <div class="ws-widget-desc">VoIP quality, throughput, and connection rate testing</div>
                    </div>
                    <label class="ws-toggle">
                        <input type="checkbox" id="widget_network_testing" checked onchange="updateSelection()">
                        <span class="ws-toggle-slider"></span>
                    </label>
                </div>
                <div class="ws-widget-item" draggable="true" data-id="widget_network_quality">
                    <span class="ws-drag-handle">&#9776;</span>
                    <div class="ws-widget-info">
                        <div class="ws-widget-name">Network Quality</div>
                        <div class="ws-widget-desc">Network quality metrics and scoring</div>
                    </div>
                    <label class="ws-toggle">
                        <input type="checkbox" id="widget_network_quality" checked onchange="updateSelection()">
                        <span class="ws-toggle-slider"></span>
                    </label>
                </div>
                <div class="ws-widget-item" draggable="true" data-id="widget_network_analysis">
                    <span class="ws-drag-handle">&#9776;</span>
                    <div class="ws-widget-info">
                        <div class="ws-widget-name">Network Analysis</div>
                        <div class="ws-widget-desc">Deep network performance analysis</div>
                    </div>
                    <label class="ws-toggle">
                        <input type="checkbox" id="widget_network_analysis" checked onchange="updateSelection()">
                        <span class="ws-toggle-slider"></span>
                    </label>
                </div>
                <div class="ws-widget-item" draggable="true" data-id="widget_wifi_roaming">
                    <span class="ws-drag-handle">&#9776;</span>
                    <div class="ws-widget-info">
                        <div class="ws-widget-name">WiFi Roaming</div>
                        <div class="ws-widget-desc">WiFi roaming events and analysis</div>
                    </div>
                    <label class="ws-toggle">
                        <input type="checkbox" id="widget_wifi_roaming" checked onchange="updateSelection()">
                        <span class="ws-toggle-slider"></span>
                    </label>
                </div>
                <div class="ws-widget-item" draggable="true" data-id="widget_vpn_status">
                    <span class="ws-drag-handle">&#9776;</span>
                    <div class="ws-widget-info">
                        <div class="ws-widget-name">VPN Status</div>
                        <div class="ws-widget-desc">VPN connection status and health</div>
                    </div>
                    <label class="ws-toggle">
                        <input type="checkbox" id="widget_vpn_status" checked onchange="updateSelection()">
                        <span class="ws-toggle-slider"></span>
                    </label>
                </div>
                <div class="ws-widget-item" draggable="true" data-id="widget_saas_health">
                    <span class="ws-drag-handle">&#9776;</span>
                    <div class="ws-widget-info">
                        <div class="ws-widget-name">SaaS Health</div>
                        <div class="ws-widget-desc">Cloud service availability monitoring</div>
                    </div>
                    <label class="ws-toggle">
                        <input type="checkbox" id="widget_saas_health" checked onchange="updateSelection()">
                        <span class="ws-toggle-slider"></span>
                    </label>
                </div>
                <div class="ws-widget-item" draggable="true" data-id="widget_security_dashboard">
                    <span class="ws-drag-handle">&#9776;</span>
                    <div class="ws-widget-info">
                        <div class="ws-widget-name">Security Dashboard</div>
                        <div class="ws-widget-desc">Security overview and compliance status</div>
                    </div>
                    <label class="ws-toggle">
                        <input type="checkbox" id="widget_security_dashboard" checked onchange="updateSelection()">
                        <span class="ws-toggle-slider"></span>
                    </label>
                </div>
                <div class="ws-widget-item" draggable="true" data-id="widget_system_health">
                    <span class="ws-drag-handle">&#9776;</span>
                    <div class="ws-widget-info">
                        <div class="ws-widget-name">System Health</div>
                        <div class="ws-widget-desc">Overall system health scoring</div>
                    </div>
                    <label class="ws-toggle">
                        <input type="checkbox" id="widget_system_health" checked onchange="updateSelection()">
                        <span class="ws-toggle-slider"></span>
                    </label>
                </div>
                <div class="ws-widget-item" draggable="true" data-id="widget_power">
                    <span class="ws-drag-handle">&#9776;</span>
                    <div class="ws-widget-info">
                        <div class="ws-widget-name">Power & Battery</div>
                        <div class="ws-widget-desc">Battery status and power information</div>
                    </div>
                    <label class="ws-toggle">
                        <input type="checkbox" id="widget_power" checked onchange="updateSelection()">
                        <span class="ws-toggle-slider"></span>
                    </label>
                </div>
                <div class="ws-widget-item" draggable="true" data-id="widget_display">
                    <span class="ws-drag-handle">&#9776;</span>
                    <div class="ws-widget-info">
                        <div class="ws-widget-name">Display</div>
                        <div class="ws-widget-desc">Connected display information</div>
                    </div>
                    <label class="ws-toggle">
                        <input type="checkbox" id="widget_display" checked onchange="updateSelection()">
                        <span class="ws-toggle-slider"></span>
                    </label>
                </div>
                <div class="ws-widget-item" draggable="true" data-id="widget_peripherals">
                    <span class="ws-drag-handle">&#9776;</span>
                    <div class="ws-widget-info">
                        <div class="ws-widget-name">Peripherals</div>
                        <div class="ws-widget-desc">Connected peripherals and USB devices</div>
                    </div>
                    <label class="ws-toggle">
                        <input type="checkbox" id="widget_peripherals" checked onchange="updateSelection()">
                        <span class="ws-toggle-slider"></span>
                    </label>
                </div>
                <div class="ws-widget-item" draggable="true" data-id="widget_disk_health">
                    <span class="ws-drag-handle">&#9776;</span>
                    <div class="ws-widget-info">
                        <div class="ws-widget-name">Disk Health</div>
                        <div class="ws-widget-desc">SMART disk health monitoring</div>
                    </div>
                    <label class="ws-toggle">
                        <input type="checkbox" id="widget_disk_health" checked onchange="updateSelection()">
                        <span class="ws-toggle-slider"></span>
                    </label>
                </div>
                <div class="ws-widget-item" draggable="true" data-id="widget_processes">
                    <span class="ws-drag-handle">&#9776;</span>
                    <div class="ws-widget-info">
                        <div class="ws-widget-name">Processes</div>
                        <div class="ws-widget-desc">Running processes and resource usage</div>
                    </div>
                    <label class="ws-toggle">
                        <input type="checkbox" id="widget_processes" checked onchange="updateSelection()">
                        <span class="ws-toggle-slider"></span>
                    </label>
                </div>
            </div>

            <h3 style="color: #00ff00; margin: 30px 0 10px 0;">Tracking Tools</h3>
            <p class="ws-hint">Drag to reorder. Toggle to include/exclude from agent package.</p>
            <div class="ws-widget-list" id="toolList">
                <div class="ws-widget-item" draggable="true" data-id="tool_metrics">
                    <span class="ws-drag-handle">&#9776;</span>
                    <div class="ws-widget-info">
                        <div class="ws-widget-name">System Metrics</div>
                        <div class="ws-widget-desc">Collect CPU, memory, disk, and network metrics</div>
                    </div>
                    <label class="ws-toggle">
                        <input type="checkbox" id="tool_metrics" checked onchange="updateSelection()">
                        <span class="ws-toggle-slider"></span>
                    </label>
                </div>
                <div class="ws-widget-item" draggable="true" data-id="tool_logs">
                    <span class="ws-drag-handle">&#9776;</span>
                    <div class="ws-widget-info">
                        <div class="ws-widget-name">Widget Logs</div>
                        <div class="ws-widget-desc">Send widget logs to fleet server</div>
                    </div>
                    <label class="ws-toggle">
                        <input type="checkbox" id="tool_logs" checked onchange="updateSelection()">
                        <span class="ws-toggle-slider"></span>
                    </label>
                </div>
                <div class="ws-widget-item" draggable="true" data-id="tool_commands">
                    <span class="ws-drag-handle">&#9776;</span>
                    <div class="ws-widget-info">
                        <div class="ws-widget-name">Remote Commands</div>
                        <div class="ws-widget-desc">Enable remote command execution from dashboard</div>
                    </div>
                    <label class="ws-toggle">
                        <input type="checkbox" id="tool_commands" checked onchange="updateSelection()">
                        <span class="ws-toggle-slider"></span>
                    </label>
                </div>
                <div class="ws-widget-item" draggable="true" data-id="tool_autostart">
                    <span class="ws-drag-handle">&#9776;</span>
                    <div class="ws-widget-info">
                        <div class="ws-widget-name">Auto-Start on Boot</div>
                        <div class="ws-widget-desc">Automatically start agent when Mac boots</div>
                    </div>
                    <label class="ws-toggle">
                        <input type="checkbox" id="tool_autostart" checked onchange="updateSelection()">
                        <span class="ws-toggle-slider"></span>
                    </label>
                </div>
            </div>
            
            <div class="config-summary" id="configSummary">
                <div class="config-summary-title">Package Configuration</div>
                <div id="summaryContent"></div>
            </div>
            
            <div style="margin-top: 20px; display: flex; gap: 10px;">
                <button class="button" onclick="downloadAgentPackage()">
                    Download Agent Package
                </button>
                <button class="button button-secondary" onclick="selectAll()">
                    ✓ Select All
                </button>
                <button class="button button-secondary" onclick="deselectAll()">
                    ✗ Deselect All
                </button>
            </div>
            
            <div class="loading" id="buildingPackage">
                <div class="spinner"></div>
                <div>Building customized agent package...</div>
            </div>
        </div>
        
        <!-- Load Balancer Generator Section -->
        <div class="section" id="loadBalancerSection">
            <div class="section-title">
                ⚖️ Load Balancer Generator
            </div>
            
            <p style="color: #999; margin-bottom: 20px;">
                Generate a load balancer deployment package for your cluster. 
                Use this to add a load balancer to an existing cluster or regenerate the configuration.
            </p>
            
            <div id="loadBalancerMessage" class="message"></div>
            
            <!-- Current Cluster Status -->
            <div id="lbClusterInfo" style="background: #1a1a1a; padding: 20px; border-radius: 10px; margin-bottom: 20px;">
                <h3 style="color: #00ff00; margin: 0 0 15px 0;"> Current Cluster Status</h3>
                <div id="lbClusterStatus">
                    <div class="loading">
                        <div class="spinner"></div>
                        <div>Loading cluster information...</div>
                    </div>
                </div>
            </div>
            
            <!-- Load Balancer Configuration -->
            <div style="background: #1a1a1a; padding: 20px; border-radius: 10px; margin-bottom: 20px;">
                <h3 style="color: #00ff00; margin: 0 0 15px 0;">Load Balancer Configuration</h3>
                
                <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 15px; margin-bottom: 15px;">
                    <div>
                        <label style="display: block; color: #999; margin-bottom: 5px;">Load Balancer Port</label>
                        <input type="number" id="lbGeneratorPort" value="8778" 
                               style="width: 100%; padding: 10px; background: #2a2a2a; border: 1px solid #00ff00; 
                                      border-radius: 5px; color: #fff; font-size: 14px;">
                        <div style="color: #666; font-size: 12px; margin-top: 5px;">
                            Port users will access (default: 8778)
                        </div>
                    </div>
                    <div>
                        <label style="display: block; color: #999; margin-bottom: 5px;">Package Name</label>
                        <input type="text" id="lbGeneratorName" value="FleetLoadBalancer.tar.gz" 
                               style="width: 100%; padding: 10px; background: #2a2a2a; border: 1px solid #00ff00; 
                                      border-radius: 5px; color: #fff; font-size: 14px;">
                    </div>
                </div>
                
                <div style="background: #2a2a2a; padding: 15px; border-radius: 8px; margin-top: 15px;">
                    <div style="color: #00ff00; font-weight: bold; margin-bottom: 10px;">Package Will Include:</div>
                    <div style="color: #999; font-size: 13px;">
                        <ul style="margin: 5px 0; padding-left: 20px; line-height: 1.8;">
                            <li>✓ HAProxy configuration (pre-configured with all cluster nodes)</li>
                            <li>✓ Nginx configuration (alternative option)</li>
                            <li>✓ Docker Compose setup (easiest deployment)</li>
                            <li>✓ Linux installation script (Ubuntu/Debian/CentOS)</li>
                            <li>✓ macOS Docker installation script</li>
                            <li>✓ Complete documentation and README</li>
                        </ul>
                    </div>
                </div>
            </div>
            
            <!-- Use Cases -->
            <div style="background: #2a5a9a; padding: 15px; border-radius: 8px; border-left: 4px solid #4a9aff; margin-bottom: 20px;">
                <div style="color: #fff; font-weight: bold; margin-bottom: 10px;">When to Use This</div>
                <div style="color: #cce5ff; font-size: 13px;">
                    <ul style="margin: 5px 0; padding-left: 20px; line-height: 1.8;">
                        <li><strong>Adding Load Balancer Later:</strong> Started with single server, now need clustering</li>
                        <li><strong>Regenerating Config:</strong> Added/removed nodes, need updated load balancer</li>
                        <li><strong>Disaster Recovery:</strong> Need to redeploy load balancer after failure</li>
                        <li><strong>Testing Different Setups:</strong> Try HAProxy vs Nginx configurations</li>
                    </ul>
                </div>
            </div>
            
            <!-- Generate Button -->
            <div style="margin-top: 20px;">
                <button class="button" onclick="generateLoadBalancerPackage()">
                    Generate Load Balancer Package
                </button>
                <button class="button button-secondary" onclick="refreshLBClusterStatus()" style="margin-left: 10px;">
                    Refresh Cluster Status
                </button>
                <button class="button button-secondary" onclick="viewLBDocs()" style="margin-left: 10px;">
                    📖 Documentation
                </button>
            </div>
            
            <!-- Not Clustered Warning -->
            <div id="notClusteredLBWarning" style="display: none; margin-top: 20px;">
                <div style="background: #2a2a2a; padding: 30px; border-radius: 10px; text-align: center;">
                    <div style="font-size: 48px; margin-bottom: 15px;">ℹ️</div>
                    <div style="color: #999; margin-bottom: 20px;">
                        This server is in standalone mode. You can still generate a load balancer package 
                        for future use when you enable clustering.
                    </div>
                    <div style="color: #666; font-size: 13px; margin-bottom: 20px;">
                        The load balancer will be configured for any nodes you deploy later.
                    </div>
                </div>
            </div>
            
            <div class="loading" id="generatingLoadBalancer">
                <div class="spinner"></div>
                <div>Generating load balancer package...</div>
            </div>
        </div>
        
        <!-- Cluster Health Monitor Section -->
        <div class="section" id="clusterHealthSection">
            <div class="section-title">
                🏥 Cluster Health Monitor
            </div>
            
            <p style="color: #999; margin-bottom: 20px;">
                Real-time health check and diagnostics for your cluster nodes. 
                Verify connectivity, synchronization, and failover readiness.
            </p>
            
            <div id="clusterHealthMessage" class="message"></div>
            
            <!-- Health Check Controls -->
            <div style="margin-bottom: 20px;">
                <button class="button" onclick="runClusterHealthCheck()">
                    Run Health Check
                </button>
                <button class="button button-secondary" onclick="refreshClusterHealth()" style="margin-left: 10px;">
                    Refresh
                </button>
            </div>
            
            <!-- Health Check Results -->
            <div id="clusterHealthResults" style="display: none;">
                
                <!-- Overall Status -->
                <div id="overallHealthStatus" style="background: #2a2a2a; padding: 20px; border-radius: 8px; margin-bottom: 20px;">
                    <div style="display: flex; align-items: center; justify-content: space-between;">
                        <div>
                            <div style="font-size: 14px; color: #666; margin-bottom: 5px;">Overall Cluster Health</div>
                            <div id="overallHealthText" style="font-size: 24px; font-weight: bold; color: #00ff00;">Healthy</div>
                        </div>
                        <div id="overallHealthIcon" style="font-size: 48px;"></div>
                    </div>
                </div>
                
                <!-- Backend Connection Status -->
                <div style="background: #1a1a1a; padding: 20px; border-radius: 8px; margin-bottom: 20px;">
                    <h3 style="color: #00ff00; margin: 0 0 15px 0;"> Backend Connection</h3>
                    <div id="backendStatus">
                        <div class="loading">
                            <div class="spinner"></div>
                            <div>Checking backend...</div>
                        </div>
                    </div>
                </div>
                
                <!-- Node Status Table -->
                <div style="background: #1a1a1a; padding: 20px; border-radius: 8px; margin-bottom: 20px;">
                    <h3 style="color: #00ff00; margin: 0 0 15px 0;"> Cluster Nodes</h3>
                    <div id="nodeStatusTable">
                        <div class="loading">
                            <div class="spinner"></div>
                            <div>Loading node status...</div>
                        </div>
                    </div>
                </div>
                
                <!-- Data Sync Status -->
                <div style="background: #1a1a1a; padding: 20px; border-radius: 8px; margin-bottom: 20px;">
                    <h3 style="color: #00ff00; margin: 0 0 15px 0;">Data Synchronization</h3>
                    <div id="syncStatus">
                        <div class="loading">
                            <div class="spinner"></div>
                            <div>Checking sync status...</div>
                        </div>
                    </div>
                </div>
                
                <!-- Architecture Info -->
                <div style="background: #2a5a9a; padding: 15px; border-radius: 8px; border-left: 4px solid #4a9aff;">
                    <div style="color: #fff; font-weight: bold; margin-bottom: 10px;">Cluster Architecture</div>
                    <div style="color: #cce5ff; font-size: 13px;">
                        <ul style="margin: 5px 0; padding-left: 20px; line-height: 1.8;">
                            <li><strong>No domain required</strong> - Nodes communicate via shared backend (Redis)</li>
                            <li><strong>Load balancer</strong> provides single entry point (can use IP or domain)</li>
                            <li><strong>If primary node fails</strong> - Other nodes continue, no downtime</li>
                            <li><strong>Users access</strong> via load balancer, which routes to healthy nodes</li>
                            <li><strong>All state in Redis</strong> - Sessions and data shared across nodes</li>
                        </ul>
                    </div>
                </div>
                
                <!-- Failover Test -->
                <div style="background: #1a1a1a; padding: 20px; border-radius: 8px; margin-top: 20px;">
                    <h3 style="color: #ff8800; margin: 0 0 15px 0;">🔥 Failover Readiness</h3>
                    <div id="failoverStatus">
                        <div class="loading">
                            <div class="spinner"></div>
                            <div>Checking failover readiness...</div>
                        </div>
                    </div>
                </div>
            </div>
            
            <!-- Not Clustered Warning -->
            <div id="notClusteredHealthWarning" style="display: none;">
                <div style="background: #2a2a2a; padding: 30px; border-radius: 10px; text-align: center;">
                    <div style="font-size: 48px; margin-bottom: 15px;">ℹ️</div>
                    <div style="color: #999; margin-bottom: 20px;">
                        Cluster mode is not enabled on this server. Enable cluster mode to use cluster health monitoring.
                    </div>
                    <button class="button button-secondary" onclick="viewClusterDocs()">
                        📖 Learn About Cluster Mode
                    </button>
                </div>
            </div>
            
            <div class="loading" id="runningHealthCheck">
                <div class="spinner"></div>
                <div>Running comprehensive health check...</div>
            </div>
        </div>
        
        <!-- Server Package Builder Section -->
        <div class="section" id="serverPackageSection">
            <div class="section-title">
                Server Package Builder
            </div>
            
            <p style="color: #999; margin-bottom: 20px;">
                Generate pre-configured .pkg installers for deploying Fleet Servers. 
                Choose between standalone servers or cluster nodes.
            </p>
            
            <div id="serverPackageMessage" class="message"></div>
            
            <!-- Package Type Selection -->
            <h3 style="color: #00ff00; margin: 20px 0 10px 0;">Select Package Type</h3>
            <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 15px; margin-bottom: 20px;">
                <div class="checkbox-item" id="standaloneOption" onclick="selectPackageType('standalone')" 
                     style="cursor: pointer; padding: 20px;">
                    <div style="display: flex; align-items: center; margin-bottom: 10px;">
                        <input type="radio" name="packageType" value="standalone" id="packageTypeStandalone" 
                               style="width: 20px; height: 20px; margin-right: 10px;">
                        <label style="font-size: 18px; font-weight: bold; cursor: pointer;">
                             Standalone Server
                        </label>
                    </div>
                    <div style="color: #999; font-size: 13px; margin-left: 30px;">
                        Deploy a new independent Fleet Server with its own database and configuration. 
                        Perfect for single-server deployments or isolated monitoring.
                    </div>
                </div>
                
                <div class="checkbox-item" id="clusterOption" onclick="selectPackageType('cluster')" 
                     style="cursor: pointer; padding: 20px;">
                    <div style="display: flex; align-items: center; margin-bottom: 10px;">
                        <input type="radio" name="packageType" value="cluster" id="packageTypeCluster" 
                               style="width: 20px; height: 20px; margin-right: 10px;">
                        <label style="font-size: 18px; font-weight: bold; cursor: pointer;">
                            Cluster Node
                        </label>
                    </div>
                    <div style="color: #999; font-size: 13px; margin-left: 30px;">
                        Deploy a server that joins this cluster for high availability and load balancing. 
                        Shares database and sessions with other nodes.
                    </div>
                </div>
            </div>
            
            <!-- Cluster Status (only shown for cluster type) -->
            <div id="clusterStatus" style="display: none; background: #2a2a2a; padding: 15px; border-radius: 8px; margin-bottom: 20px;">
                <div class="loading" id="loadingClusterStatus">
                    <div class="spinner"></div>
                    <div>Checking cluster status...</div>
                </div>
            </div>
            
            <!-- Standalone Package Configuration -->
            <div id="standalonePackageConfig" style="display: none;">
                <h3 style="color: #00ff00; margin: 20px 0 10px 0;">Standalone Server Configuration</h3>
                <div style="background: #1a1a1a; padding: 20px; border-radius: 10px; margin-bottom: 20px;">
                    <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 15px; margin-bottom: 15px;">
                        <div>
                            <label style="display: block; color: #999; margin-bottom: 5px;">Server Name (Optional)</label>
                            <input type="text" id="standaloneServerName" placeholder="e.g., fleet-monitor-01" 
                                   style="width: 100%; padding: 10px; background: #2a2a2a; border: 1px solid #00ff00; 
                                          border-radius: 5px; color: #fff; font-size: 14px;">
                            <div style="color: #666; font-size: 12px; margin-top: 5px;">
                                Leave empty to auto-generate based on hostname
                            </div>
                        </div>
                        <div>
                            <label style="display: block; color: #999; margin-bottom: 5px;">Package Name</label>
                            <input type="text" id="standalonePackageName" value="FleetServerStandalone.pkg" 
                                   style="width: 100%; padding: 10px; background: #2a2a2a; border: 1px solid #00ff00; 
                                          border-radius: 5px; color: #fff; font-size: 14px;">
                        </div>
                    </div>
                    
                    <!-- Configuration Summary -->
                    <div style="background: #2a2a2a; padding: 15px; border-radius: 8px; border-left: 4px solid #00ff00;">
                        <div style="color: #00ff00; font-weight: bold; margin-bottom: 10px;">What Will Be Included</div>
                        <div style="color: #999; font-size: 13px;">
                            <ul style="margin: 10px 0; padding-left: 20px; line-height: 1.8;">
                                <li>✓ Fresh Fleet Server installation</li>
                                <li>✓ New database (SQLite with encryption)</li>
                                <li>✓ Default admin account (you'll set password on first run)</li>
                                <li>✓ Auto-start LaunchDaemon</li>
                                <li>✓ SSL certificate support</li>
                                <li>✓ Independent operation (no clustering)</li>
                            </ul>
                        </div>
                    </div>
                    
                    <!-- Ethernet Requirement Warning -->
                    <div style="background: #ff8800; padding: 15px; border-radius: 8px; margin-top: 15px; border: 2px solid #ffaa00;">
                        <div style="color: #fff; font-weight: bold; margin-bottom: 10px;"> Ethernet Connection Required</div>
                        <div style="color: #fff; font-size: 13px;">
                            <ul style="margin: 5px 0; padding-left: 20px; line-height: 1.6;">
                                <li><strong>MUST have active wired Ethernet connection</strong></li>
                                <li>WiFi is NOT supported for server installations</li>
                                <li>Built-in Ethernet or USB/Thunderbolt adapter required</li>
                                <li>Installation will fail if Ethernet is not connected</li>
                            </ul>
                        </div>
                    </div>
                    
                    <!-- Info Message -->
                    <div style="background: #2a5a9a; padding: 15px; border-radius: 8px; margin-top: 15px;">
                        <div style="color: #fff; font-weight: bold; margin-bottom: 10px;">ℹ️ Standalone Server Notes</div>
                        <div style="color: #fff; font-size: 13px;">
                            <ul style="margin: 5px 0; padding-left: 20px; line-height: 1.6;">
                                <li>Server will operate independently with its own data</li>
                                <li>No shared storage or clustering configured</li>
                                <li>Can be converted to cluster node later if needed</li>
                                <li>Perfect for small deployments or testing</li>
                            </ul>
                        </div>
                    </div>
                </div>
                
                <!-- Build Button -->
                <div style="margin-top: 20px; display: flex; gap: 10px;">
                    <button class="button" onclick="buildStandalonePackage()">
                        Build Standalone Server Package
                    </button>
                    <button class="button button-secondary" onclick="viewServerDocs()">
                        📖 View Documentation
                    </button>
                </div>
                
                <div class="loading" id="buildingStandalonePackage">
                    <div class="spinner"></div>
                    <div>Building standalone server installer package...</div>
                </div>
            </div>
            
            <!-- Cluster Package Configuration -->
            <div id="clusterPackageConfig" style="display: none;">
                <h3 style="color: #00ff00; margin: 20px 0 10px 0;">Cluster Configuration</h3>
                
                <!-- Node Configuration -->
                <div style="background: #1a1a1a; padding: 20px; border-radius: 10px; margin-bottom: 20px;">
                    <h4 style="color: #00ff00; margin: 0 0 15px 0;"> Cluster Node Package</h4>
                    <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 15px; margin-bottom: 15px;">
                        <div>
                            <label style="display: block; color: #999; margin-bottom: 5px;">Node Name (Optional)</label>
                            <input type="text" id="clusterNodeName" placeholder="e.g., server-02" 
                                   style="width: 100%; padding: 10px; background: #2a2a2a; border: 1px solid #00ff00; 
                                          border-radius: 5px; color: #fff; font-size: 14px;">
                            <div style="color: #666; font-size: 12px; margin-top: 5px;">
                                Leave empty to auto-generate based on hostname
                            </div>
                        </div>
                        <div>
                            <label style="display: block; color: #999; margin-bottom: 5px;">Package Name</label>
                            <input type="text" id="clusterPackageName" value="FleetServerClusterNode.pkg" 
                                   style="width: 100%; padding: 10px; background: #2a2a2a; border: 1px solid #00ff00; 
                                          border-radius: 5px; color: #fff; font-size: 14px;">
                        </div>
                    </div>
                </div>
                
                <!-- Load Balancer Configuration -->
                <div style="background: #1a1a1a; padding: 20px; border-radius: 10px; margin-bottom: 20px;">
                    <h4 style="color: #00ff00; margin: 0 0 15px 0;">⚖️ Load Balancer Package (Automatic)</h4>
                    <div style="color: #999; margin-bottom: 15px;">
                        Automatically generates load balancer configuration for all cluster nodes.
                        Deploy on a separate machine (Linux VM or Docker on macOS).
                    </div>
                    
                    <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 15px;">
                        <div>
                            <label style="display: block; color: #999; margin-bottom: 5px;">Load Balancer Port</label>
                            <input type="number" id="loadBalancerPort" value="8778" 
                                   style="width: 100%; padding: 10px; background: #2a2a2a; border: 1px solid #00ff00; 
                                          border-radius: 5px; color: #fff; font-size: 14px;">
                        </div>
                        <div>
                            <label style="display: block; color: #999; margin-bottom: 5px;">
                                <input type="checkbox" id="includeLB" checked style="margin-right: 5px;">
                                Include Load Balancer Package
                            </label>
                            <div style="color: #666; font-size: 12px; margin-top: 5px;">
                                Automatically builds load balancer with cluster nodes
                            </div>
                        </div>
                    </div>
                    
                    <div style="background: #2a2a2a; padding: 15px; border-radius: 8px; margin-top: 15px;">
                        <div style="color: #00ff00; font-weight: bold; margin-bottom: 10px;">Load Balancer Package Includes:</div>
                        <div style="color: #999; font-size: 13px;">
                            <ul style="margin: 5px 0; padding-left: 20px; line-height: 1.8;">
                                <li>✓ HAProxy configuration (auto-configured with all nodes)</li>
                                <li>✓ Nginx configuration (alternative option)</li>
                                <li>✓ Docker Compose setup (easiest for macOS)</li>
                                <li>✓ Linux installation script (Ubuntu/Debian)</li>
                                <li>✓ macOS Docker installation script</li>
                                <li>✓ Complete documentation and README</li>
                            </ul>
                        </div>
                    </div>
                </div>
                    
                    <!-- Configuration Summary -->
                    <div style="background: #2a2a2a; padding: 15px; border-radius: 8px; border-left: 4px solid #00ff00;">
                        <div style="color: #00ff00; font-weight: bold; margin-bottom: 10px;">What Will Be Included</div>
                        <div style="color: #999; font-size: 13px;">
                            <ul style="margin: 10px 0; padding-left: 20px; line-height: 1.8;">
                                <li>✓ Cluster configuration (Redis/shared storage connection)</li>
                                <li>✓ Shared database encryption keys</li>
                                <li>✓ Same API keys and authentication</li>
                                <li>✓ Auto-start LaunchDaemon</li>
                                <li>✓ Automatic cluster registration</li>
                                <li>✓ Shared session storage configuration</li>
                            </ul>
                        </div>
                    </div>
                    
                    <!-- Ethernet Requirement Warning -->
                    <div style="background: #ff8800; padding: 15px; border-radius: 8px; margin-top: 15px; border: 2px solid #ffaa00;">
                        <div style="color: #fff; font-weight: bold; margin-bottom: 10px;"> Ethernet Connection Required</div>
                        <div style="color: #fff; font-size: 13px;">
                            <ul style="margin: 5px 0; padding-left: 20px; line-height: 1.6;">
                                <li><strong>MUST have active wired Ethernet connection</strong></li>
                                <li>WiFi is NOT supported for server installations</li>
                                <li>Built-in Ethernet or USB/Thunderbolt adapter required</li>
                                <li>Installation will fail if Ethernet is not connected</li>
                                <li>See CLUSTER_ETHERNET_REQUIREMENT.md for details</li>
                            </ul>
                        </div>
                    </div>
                    
                    <!-- Warning Message -->
                    <div style="background: #ff4444; padding: 15px; border-radius: 8px; margin-top: 15px;">
                        <div style="color: #fff; font-weight: bold; margin-bottom: 10px;">Important Notes</div>
                        <div style="color: #fff; font-size: 13px;">
                            <ul style="margin: 5px 0; padding-left: 20px; line-height: 1.6;">
                                <li>The new server must be able to reach your Redis server or shared storage</li>
                                <li>All encryption keys and passwords are embedded in the package</li>
                                <li>Keep the .pkg file secure - it contains sensitive configuration</li>
                                <li>The new server will automatically join the cluster on first boot</li>
                                <li>Both servers can be on different networks as long as they share the same backend</li>
                            </ul>
                        </div>
                    </div>
                </div>
                
                <!-- Build Button -->
                <div style="margin-top: 20px; display: flex; gap: 10px;">
                    <button class="button" onclick="buildClusterPackage()">
                        Build Cluster Node Package
                    </button>
                    <button class="button button-secondary" onclick="viewClusterDocs()">
                        📖 View Documentation
                    </button>
                </div>
                
                <div class="loading" id="buildingClusterPackage">
                    <div class="spinner"></div>
                    <div>Building cluster node installer package...</div>
                </div>
            </div>
            
            <!-- Not Clustered Warning -->
            <div id="notClusteredWarning" style="display: none;">
                <div style="background: #2a2a2a; padding: 30px; border-radius: 10px; text-align: center;">
                    <div style="font-size: 48px; margin-bottom: 15px;">ℹ️</div>
                    <div style="color: #999; margin-bottom: 20px;">
                        Cluster mode is not enabled on this server. Enable cluster mode in your configuration to use this feature.
                    </div>
                    <button class="button button-secondary" onclick="viewClusterDocs()">
                        📖 Learn About Cluster Mode
                    </button>
                </div>
            </div>
        </div>
    </div>

    <!-- Export Logs Section -->
    <div class="section">
        <div class="section-title">
            Export Logs
            <span style="margin-left: auto; display: flex; gap: 10px; align-items: center;">
                <select id="exportLogsMachineFilter" onchange="loadExportLogs()"
                        style="padding: 5px 10px; background: #2a2a2a; color: #fff; border: 1px solid #333; border-radius: 5px; font-size: 12px;">
                    <option value="">All Machines</option>
                </select>
                <button class="button-secondary" onclick="loadExportLogs()" style="padding: 5px 15px; font-size: 12px;">
                    Refresh
                </button>
            </span>
        </div>
        <div id="exportLogsContainer">
            <div class="loading" id="loadingExportLogs">
                <div class="spinner"></div>
                <div>Loading export logs...</div>
            </div>
            <div id="exportLogsContent" style="display: none;"></div>
        </div>
    </div>

    <script>
'''
    # Inject toast script and continue with rest of JavaScript
    html_script = '''
        function escapeHtml(str) {
            if (str === null || str === undefined) return '';
            return String(str).replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;').replace(/'/g, '&#039;');
        }

        let certFile = null;
        let keyFile = null;
        let resourceRefreshInterval = null;
        
        // Format bytes to human readable
        function formatBytes(bytes, decimals = 2) {
            if (bytes === 0) return '0 B';
            const k = 1024;
            const dm = decimals < 0 ? 0 : decimals;
            const sizes = ['B', 'KB', 'MB', 'GB', 'TB'];
            const i = Math.floor(Math.log(bytes) / Math.log(k));
            return parseFloat((bytes / Math.pow(k, i)).toFixed(dm)) + ' ' + sizes[i];
        }
        
        // Get color based on percentage
        function getUsageColor(percent) {
            if (percent >= 90) return '#ff4444';
            if (percent >= 75) return '#ffd93d';
            return '#00ff00';
        }
        
        // Format uptime to human readable
        function formatUptime(seconds) {
            const days = Math.floor(seconds / 86400);
            const hours = Math.floor((seconds % 86400) / 3600);
            const mins = Math.floor((seconds % 3600) / 60);
            const secs = Math.floor(seconds % 60);
            
            if (days > 0) return `${days}d ${hours}h ${mins}m`;
            if (hours > 0) return `${hours}h ${mins}m ${secs}s`;
            if (mins > 0) return `${mins}m ${secs}s`;
            return `${secs}s`;
        }
        
        // Load server resource information
        async function loadServerResources() {
            const loadingEl = document.getElementById('loadingResources');
            const infoEl = document.getElementById('serverResourcesInfo');
            
            try {
                const response = await fetch('/api/fleet/server-resources', {
                    credentials: 'include'
                });
                const data = await response.json();
                
                if (loadingEl) loadingEl.style.display = 'none';
                
                if (data.error) {
                    infoEl.innerHTML = `<div style="color: #ff4444; text-align: center; grid-column: 1 / -1;">Error: ${escapeHtml(data.error)}</div>`;
                    return;
                }
                
                const cpuColor = getUsageColor(data.process.cpu_percent);
                const memColor = getUsageColor(data.process.memory_percent);
                
                infoEl.innerHTML = `
                    <!-- Server Process Card -->
                    <div style="background: #2a2a2a; border-radius: 12px; padding: 20px; border-left: 4px solid #00c8ff;">
                        <div style="display: flex; align-items: center; margin-bottom: 15px;">
                            <span style="font-size: 28px; margin-right: 12px;"></span>
                            <div>
                                <div style="color: #999; font-size: 12px; text-transform: uppercase;">Fleet Server Process</div>
                                <div style="color: #00c8ff; font-size: 20px; font-weight: bold;">PID ${data.process.pid}</div>
                            </div>
                        </div>
                        <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 10px; font-size: 13px;">
                            <div><span style="color: #666;">Uptime:</span> <span style="color: #00ff00;">${formatUptime(data.process.uptime_seconds)}</span></div>
                            <div><span style="color: #666;">Threads:</span> <span style="color: #fff;">${data.process.threads}</span></div>
                            <div><span style="color: #666;">Open Files:</span> <span style="color: #fff;">${data.process.open_files}</span></div>
                            <div><span style="color: #666;">Connections:</span> <span style="color: #fff;">${data.process.connections}</span></div>
                        </div>
                    </div>
                    
                    <!-- CPU Usage Card -->
                    <div style="background: #2a2a2a; border-radius: 12px; padding: 20px; border-left: 4px solid ${cpuColor};">
                        <div style="display: flex; align-items: center; margin-bottom: 15px;">
                            <span style="font-size: 28px; margin-right: 12px;">🖥️</span>
                            <div>
                                <div style="color: #999; font-size: 12px; text-transform: uppercase;">Server CPU Usage</div>
                                <div style="color: ${cpuColor}; font-size: 28px; font-weight: bold;">${data.process.cpu_percent.toFixed(1)}%</div>
                            </div>
                        </div>
                        <div style="background: #1a1a1a; border-radius: 8px; height: 8px; overflow: hidden;">
                            <div style="background: ${cpuColor}; height: 100%; width: ${Math.min(data.process.cpu_percent, 100)}%; transition: width 0.3s;"></div>
                        </div>
                    </div>
                    
                    <!-- Memory Usage Card -->
                    <div style="background: #2a2a2a; border-radius: 12px; padding: 20px; border-left: 4px solid ${memColor};">
                        <div style="display: flex; align-items: center; margin-bottom: 15px;">
                            <span style="font-size: 28px; margin-right: 12px;"></span>
                            <div>
                                <div style="color: #999; font-size: 12px; text-transform: uppercase;">Server Memory</div>
                                <div style="color: ${memColor}; font-size: 28px; font-weight: bold;">${formatBytes(data.process.memory_rss)}</div>
                            </div>
                        </div>
                        <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 10px; font-size: 13px;">
                            <div><span style="color: #666;">RSS:</span> <span style="color: #fff;">${formatBytes(data.process.memory_rss)}</span></div>
                            <div><span style="color: #666;">Virtual:</span> <span style="color: #fff;">${formatBytes(data.process.memory_vms)}</span></div>
                        </div>
                    </div>
                    
                    <!-- Storage Card -->
                    <div style="background: #2a2a2a; border-radius: 12px; padding: 20px; border-left: 4px solid #9966ff;">
                        <div style="display: flex; align-items: center; margin-bottom: 15px;">
                            <span style="font-size: 28px; margin-right: 12px;">💿</span>
                            <div>
                                <div style="color: #999; font-size: 12px; text-transform: uppercase;">Server Storage</div>
                                <div style="color: #9966ff; font-size: 28px; font-weight: bold;">${formatBytes(data.storage.total_size)}</div>
                            </div>
                        </div>
                        <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 10px; font-size: 13px;">
                            <div><span style="color: #666;">Data Dir:</span> <span style="color: #fff;">${formatBytes(data.storage.data_dir_size)}</span></div>
                            <div><span style="color: #666;">Logs:</span> <span style="color: #fff;">${formatBytes(data.storage.log_size)}</span></div>
                        </div>
                    </div>
                `;
            } catch (e) {
                if (loadingEl) loadingEl.style.display = 'none';
                infoEl.innerHTML = `<div style="color: #ff4444; text-align: center; grid-column: 1 / -1;">Error loading server resources: ${escapeHtml(e.message)}</div>`;
            }
        }
        
        // Start auto-refresh for server resources
        function startResourceRefresh() {
            loadServerResources();
            resourceRefreshInterval = setInterval(loadServerResources, 5000);
        }
        
        // Load certificate information
        async function loadCertInfo() {
            const loadingEl = document.getElementById('loadingCertInfo');
            const infoEl = document.getElementById('certInfo');
            
            loadingEl.style.display = 'block';
            
            try {
                const response = await fetch('/api/fleet/cert-info');
                const data = await response.json();
                
                loadingEl.style.display = 'none';
                
                if (data.info) {
                    const info = data.info;
                    let statusBadge = '';
                    
                    if (info.expired) {
                        statusBadge = '<span class="status-badge status-critical">EXPIRED</span>';
                    } else if (info.expires_soon) {
                        statusBadge = '<span class="status-badge status-warning">EXPIRES SOON</span>';
                    } else {
                        statusBadge = '<span class="status-badge status-valid">VALID</span>';
                    }
                    
                    infoEl.innerHTML = `
                        <div class="cert-row">
                            <span class="cert-label">Status:</span>
                            <span class="cert-value">${statusBadge}</span>
                        </div>
                        <div class="cert-row">
                            <span class="cert-label">Common Name:</span>
                            <span class="cert-value">${escapeHtml(info.common_name || 'N/A')}</span>
                        </div>
                        ${info.sans && info.sans.length > 0 ? `
                        <div class="cert-row">
                            <span class="cert-label">SANs:</span>
                            <span class="cert-value">${escapeHtml(info.sans.join(', '))}</span>
                        </div>
                        ` : ''}
                        <div class="cert-row">
                            <span class="cert-label">Expires:</span>
                            <span class="cert-value">${new Date(info.not_after).toLocaleDateString()} (${info.days_until_expiry} days)</span>
                        </div>
                        <div class="cert-row">
                            <span class="cert-label">Issuer:</span>
                            <span class="cert-value">${escapeHtml(info.issuer || 'N/A')}</span>
                        </div>
                        <div class="cert-row">
                            <span class="cert-label">Type:</span>
                            <span class="cert-value">
                                ${info.is_wildcard ? ' Wildcard' : ' Standard'}
                                ${info.is_self_signed ? ' (Self-signed)' : ''}
                            </span>
                        </div>
                    `;
                } else {
                    infoEl.innerHTML = '<div style="text-align: center; color: #999;">No SSL certificate configured</div>';
                }
            } catch (e) {
                loadingEl.style.display = 'none';
                infoEl.innerHTML = '<div style="text-align: center; color: #ff4444;">Error loading certificate information</div>';
            }
        }
        
        // Handle file selection
        function handleFileSelect(type) {
            const fileInput = document.getElementById(type + 'File');
            const fileName = document.getElementById(type + 'FileName');
            
            if (fileInput.files.length > 0) {
                const file = fileInput.files[0];
                if (type === 'cert') {
                    certFile = file;
                } else {
                    keyFile = file;
                }
                fileName.textContent = ' ' + file.name;
                fileName.style.display = 'inline-block';
            }
            
            // Enable upload button if both files selected
            document.getElementById('uploadButton').disabled = !(certFile && keyFile);
        }
        
        // Clear file selection
        function clearFiles() {
            certFile = null;
            keyFile = null;
            document.getElementById('certFile').value = '';
            document.getElementById('keyFile').value = '';
            document.getElementById('certFileName').style.display = 'none';
            document.getElementById('keyFileName').style.display = 'none';
            document.getElementById('uploadButton').disabled = true;
        }
        
        // Upload certificate
        async function uploadCertificate() {
            if (!certFile || !keyFile) {
                showMessage('error', 'Please select both certificate and key files');
                return;
            }
            
            const uploadingEl = document.getElementById('uploadingCert');
            const uploadButton = document.getElementById('uploadButton');
            
            uploadingEl.style.display = 'block';
            uploadButton.disabled = true;
            
            try {
                const formData = new FormData();
                formData.append('certificate', certFile);
                formData.append('private_key', keyFile);
                
                const response = await fetch('/api/fleet/update-certificate', {
                    method: 'POST',
                    body: formData
                });
                
                const result = await response.json();
                
                uploadingEl.style.display = 'none';
                
                if (result.success) {
                    showMessage('success', ' Certificate updated successfully! Server will reload with new certificate.');
                    clearFiles();
                    setTimeout(() => {
                        loadCertInfo();
                    }, 2000);
                } else {
                    showMessage('error', ' ' + (result.error || 'Failed to update certificate'));
                    uploadButton.disabled = false;
                }
            } catch (e) {
                uploadingEl.style.display = 'none';
                showMessage('error', ' Error uploading certificate: ' + e.message);
                uploadButton.disabled = false;
            }
        }
        
        // Show message
        function showMessage(type, text) {
            const messageEl = document.getElementById('uploadMessage');
            messageEl.className = 'message ' + type;
            messageEl.textContent = text;
            messageEl.style.display = 'block';
            
            setTimeout(() => {
                messageEl.style.display = 'none';
            }, 5000);
        }
        
        // Drag and drop support
        ['certUploadArea', 'keyUploadArea'].forEach(id => {
            const area = document.getElementById(id);
            const type = id === 'certUploadArea' ? 'cert' : 'key';
            
            area.addEventListener('dragover', (e) => {
                e.preventDefault();
                area.classList.add('dragover');
            });
            
            area.addEventListener('dragleave', () => {
                area.classList.remove('dragover');
            });
            
            area.addEventListener('drop', (e) => {
                e.preventDefault();
                area.classList.remove('dragover');
                
                const files = e.dataTransfer.files;
                if (files.length > 0) {
                    const fileInput = document.getElementById(type + 'File');
                    fileInput.files = files;
                    handleFileSelect(type);
                }
            });
        });
        
        // Load certificate info on page load
        loadCertInfo();
        
        // Start server resource monitoring
        startResourceRefresh();
        
        // Package builder functions
        function updateSelection() {
            updateSummary();
        }

        function updateSummary() {
            const widgets = [];
            const tools = [];
            const isStandalone = document.getElementById('package_standalone').checked;

            // Check widgets in DOM order (reflects drag-drop reordering)
            let widgetIdx = 1;
            document.querySelectorAll('#widgetList .ws-widget-item').forEach(item => {
                const toggle = item.querySelector('.ws-toggle input');
                const name = item.querySelector('.ws-widget-name');
                if (toggle && name) {
                    if (toggle.checked) {
                        widgets.push(widgetIdx + '. ' + name.textContent);
                        widgetIdx++;
                    }
                }
            });

            // Check tools in DOM order (reflects drag-drop reordering)
            let toolIdx = 1;
            document.querySelectorAll('#toolList .ws-widget-item').forEach(item => {
                const toggle = item.querySelector('.ws-toggle input');
                const name = item.querySelector('.ws-widget-name');
                if (toggle && name) {
                    if (toggle.checked) {
                        tools.push(toolIdx + '. ' + name.textContent);
                        toolIdx++;
                    }
                }
            });

            const packageType = isStandalone ? 'Standalone (no server credentials)' : 'Fleet-Linked (auto-connects)';

            const summaryContent = document.getElementById('summaryContent');
            summaryContent.innerHTML = `
                <div class="config-summary-item"><strong>Package Type:</strong> ${packageType}</div>
                <div class="config-summary-item"><strong>Widgets (in order):</strong> ${widgets.length > 0 ? widgets.join(', ') : 'None'}</div>
                <div class="config-summary-item"><strong>Tools (in order):</strong> ${tools.length > 0 ? tools.join(', ') : 'None'}</div>
                <div class="config-summary-item"><strong>Total Features:</strong> ${widgets.length + tools.length}</div>
            `;
        }

        function selectAll() {
            document.querySelectorAll('.ws-toggle input[type="checkbox"]').forEach(cb => {
                cb.checked = true;
            });
            updateSelection();
        }

        function deselectAll() {
            document.querySelectorAll('.ws-toggle input[type="checkbox"]').forEach(cb => {
                cb.checked = false;
            });
            updateSelection();
        }

        // Drag-and-drop reordering for widget/tool lists
        function initDragDrop(listId) {
            const list = document.getElementById(listId);
            if (!list) return;
            let dragItem = null;

            list.querySelectorAll('.ws-widget-item').forEach(item => {
                item.addEventListener('dragstart', e => {
                    dragItem = item;
                    item.classList.add('dragging');
                    e.dataTransfer.effectAllowed = 'move';
                });

                item.addEventListener('dragend', () => {
                    item.classList.remove('dragging');
                    list.querySelectorAll('.ws-widget-item').forEach(el => el.classList.remove('drag-over'));
                    dragItem = null;
                    updateSelection();
                });

                item.addEventListener('dragover', e => {
                    e.preventDefault();
                    e.dataTransfer.dropEffect = 'move';
                    if (item !== dragItem) {
                        item.classList.add('drag-over');
                    }
                });

                item.addEventListener('dragleave', () => {
                    item.classList.remove('drag-over');
                });

                item.addEventListener('drop', e => {
                    e.preventDefault();
                    item.classList.remove('drag-over');
                    if (dragItem && dragItem !== item) {
                        const items = Array.from(list.querySelectorAll('.ws-widget-item'));
                        const fromIdx = items.indexOf(dragItem);
                        const toIdx = items.indexOf(item);
                        if (fromIdx < toIdx) {
                            list.insertBefore(dragItem, item.nextSibling);
                        } else {
                            list.insertBefore(dragItem, item);
                        }
                    }
                });
            });
        }

        // Initialize drag-drop for both lists
        initDragDrop('widgetList');
        initDragDrop('toolList');

        // Wire up toggle change events
        document.querySelectorAll('.ws-toggle input').forEach(toggle => {
            toggle.addEventListener('change', updateSelection);
        });

        // Initial summary update
        updateSelection();
        
        // Package Type Toggle Functions
        function togglePackageType(type) {
            const linkedRadio = document.getElementById('package_linked');
            const standaloneRadio = document.getElementById('package_standalone');
            const linkedItem = document.getElementById('packageTypeLinked');
            const standaloneItem = document.getElementById('packageTypeStandalone');
            const standaloneConfig = document.getElementById('standaloneConfig');
            
            if (type === 'linked') {
                linkedRadio.checked = true;
                standaloneRadio.checked = false;
                linkedItem.classList.add('selected');
                standaloneItem.classList.remove('selected');
                standaloneConfig.style.display = 'none';
            } else {
                linkedRadio.checked = false;
                standaloneRadio.checked = true;
                linkedItem.classList.remove('selected');
                standaloneItem.classList.add('selected');
                standaloneConfig.style.display = 'block';
            }
            updateSummary();
        }
        
        function updatePackageType() {
            const isStandalone = document.getElementById('package_standalone').checked;
            togglePackageType(isStandalone ? 'standalone' : 'linked');
        }
        
        async function downloadAgentPackage() {
            const buildingEl = document.getElementById('buildingPackage');
            const isStandalone = document.getElementById('package_standalone').checked;
            
            // Get selected options - read from DOM order (respects drag-drop reordering)
            const widgets = {};
            const widgetOrder = [];
            document.querySelectorAll('#widgetList .ws-widget-item').forEach(item => {
                const id = item.dataset.id;
                const key = id.replace('widget_', '');
                const checked = item.querySelector('.ws-toggle input').checked;
                widgets[key] = checked;
                widgetOrder.push(key);
            });

            const tools = {};
            const toolOrder = [];
            document.querySelectorAll('#toolList .ws-widget-item').forEach(item => {
                const id = item.dataset.id;
                const key = id.replace('tool_', '');
                const checked = item.querySelector('.ws-toggle input').checked;
                tools[key] = checked;
                toolOrder.push(key);
            });

            const config = {
                widgets: widgets,
                widget_order: widgetOrder,
                tools: tools,
                tool_order: toolOrder,
                standalone: isStandalone,
                standalone_options: isStandalone ? {
                    include_setup_wizard: document.getElementById('standalone_include_setup_wizard').checked,
                    include_menubar: document.getElementById('standalone_include_menubar').checked
                } : null
            };
            
            buildingEl.style.display = 'block';
            
            try {
                const response = await fetch('/api/fleet/build-agent-package', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json'
                    },
                    body: JSON.stringify(config)
                });
                
                if (!response.ok) {
                    const errorData = await response.json().catch(() => ({}));
                    throw new Error(errorData.error || 'Failed to build package');
                }
                
                // Download the file - get filename from Content-Disposition header or use default
                const contentDisposition = response.headers.get('Content-Disposition');
                let filename = isStandalone ? 'ATLAS_Standalone_Agent.pkg' : 'ATLAS_Fleet_Agent.pkg';
                if (contentDisposition) {
                    const match = contentDisposition.match(/filename="?([^"]+)"?/);
                    if (match) filename = match[1];
                }
                
                const blob = await response.blob();
                const url = URL.createObjectURL(blob);
                const a = document.createElement('a');
                a.href = url;
                a.download = filename;
                document.body.appendChild(a);
                a.click();
                document.body.removeChild(a);
                URL.revokeObjectURL(url);
                
                buildingEl.style.display = 'none';
                const packageType = isStandalone ? 'Standalone' : 'Fleet-linked';
                showPackageMessage('success', `${packageType} agent package downloaded successfully!`);
            } catch (e) {
                buildingEl.style.display = 'none';
                showPackageMessage('error', 'Error building package: ' + e.message);
            }
        }
        
        function showPackageMessage(type, text) {
            const messageEl = document.getElementById('packageMessage');
            messageEl.className = 'message ' + type;
            messageEl.textContent = text;
            messageEl.style.display = 'block';
            
            setTimeout(() => {
                messageEl.style.display = 'none';
            }, 5000);
        }
        
        // Initialize summary on page load
        updateSummary();
        
        // Password Validation Functions
        function validatePasswordComplexity(password) {
            const missing = [];
            
            if (password.length < 12) {
                missing.push(`At least 12 characters (currently ${password.length})`);
            }
            if (!/[A-Z]/.test(password)) {
                missing.push('At least one uppercase letter (A-Z)');
            }
            if (!/[a-z]/.test(password)) {
                missing.push('At least one lowercase letter (a-z)');
            }
            if (!/[0-9]/.test(password)) {
                missing.push('At least one number (0-9)');
            }
            if (!/[!@#$%^&*()_+\-=\[\]{};:'\"\\|,.<>\/?`~]/.test(password)) {
                missing.push('At least one symbol (!@#$%^&*()_+-=[]{}etc.)');
            }
            
            return {
                isValid: missing.length === 0,
                missing: missing
            };
        }
        
        function showPasswordStrength(password, elementId) {
            const result = validatePasswordComplexity(password);
            const el = document.getElementById(elementId);
            
            if (!password) {
                el.innerHTML = '';
                return;
            }
            
            if (result.isValid) {
                el.innerHTML = '<span style="color: #00ff00;"> Password meets all requirements</span>';
            } else {
                const missingHtml = result.missing.map(req => `<span style="color: #ff4444;"> ${req}</span>`).join('<br>');
                el.innerHTML = missingHtml;
            }
        }
        
        // Add event listeners for password strength indicators
        document.addEventListener('DOMContentLoaded', function() {
            const newUserPassword = document.getElementById('newUserPassword');
            if (newUserPassword) {
                newUserPassword.addEventListener('input', function() {
                    showPasswordStrength(this.value, 'newUserPasswordStrength');
                });
            }
            
            const modalPassword = document.getElementById('modalNewPassword');
            if (modalPassword) {
                modalPassword.addEventListener('input', function() {
                    showPasswordStrength(this.value, 'modalPasswordStrength');
                });
            }
            
            // Load load balancer cluster status
            refreshLBClusterStatus();
        });
        
        // Password Update Modal Functions
        function showPasswordUpdateModal() {
            document.getElementById('passwordUpdateModal').style.display = 'block';
        }
        
        function closePasswordUpdateModal() {
            document.getElementById('passwordUpdateModal').style.display = 'none';
            document.getElementById('modalNewPassword').value = '';
            document.getElementById('modalConfirmPassword').value = '';
            document.getElementById('modalPasswordStrength').innerHTML = '';
        }
        
        async function updatePasswordFromModal() {
            const newPassword = document.getElementById('modalNewPassword').value;
            const confirmPassword = document.getElementById('modalConfirmPassword').value;
            
            if (!newPassword) {
                alert('Please enter a new password');
                return;
            }
            
            if (newPassword !== confirmPassword) {
                alert('Passwords do not match');
                return;
            }
            
            const validation = validatePasswordComplexity(newPassword);
            if (!validation.isValid) {
                alert('Password does not meet requirements: ' + validation.missing.join(', '));
                return;
            }
            
            try {
                const response = await fetch('/api/fleet/users/force-update-password', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    credentials: 'include',
                    body: JSON.stringify({ new_password: newPassword })
                });
                
                const data = await response.json();
                
                if (data.success) {
                    alert('Success:  Password updated successfully! Please log in again with your new password.');
                    closePasswordUpdateModal();
                    // Redirect to logout
                    window.location.href = '/dashboard?logout=1';
                } else {
                    alert('Error:  ' + data.message);
                }
            } catch (e) {
                alert('Error:  Error updating password: ' + e.message);
            }
        }
        
        // Check if current user needs password update
        async function checkPasswordUpdate() {
            try {
                const response = await fetch('/api/fleet/users/check-password-update', {
                    credentials: 'include'
                });
                const data = await response.json();
                
                if (data.needs_update) {
                    document.getElementById('passwordUpdateWarning').style.display = 'block';
                }
            } catch (e) {
                console.error('Error checking password update:', e);
            }
        }
        
        // User Management Functions
        async function loadUsers() {
            try {
                const response = await fetch('/api/fleet/users', {
                    credentials: 'include'
                });
                const data = await response.json();
                
                if (data.users) {
                    displayUsers(data.users);
                } else {
                    document.getElementById('usersList').innerHTML = '<p style="color: #999;">No users found</p>';
                }
            } catch (e) {
                document.getElementById('usersList').innerHTML = '<p style="color: #ff4444;">Error loading users</p>';
            }
        }
        
        function displayUsers(users) {
            const listEl = document.getElementById('usersList');
            if (users.length === 0) {
                listEl.innerHTML = '<p style="color: #999;">No users found</p>';
                return;
            }
            
            let html = '<div style="display: grid; gap: 10px;">';
            users.forEach(user => {
                const statusColor = user.is_active ? '#00ff00' : '#ff4444';
                const lastLogin = user.last_login ? new Date(user.last_login).toLocaleString() : 'Never';
                html += `
                    <div style="background: #2a2a2a; padding: 15px; border-radius: 8px; border-left: 4px solid ${statusColor};">
                        <div style="display: flex; justify-content: space-between; align-items: center;">
                            <div>
                                <div style="font-weight: bold; color: #fff; font-size: 16px;">
                                    ${escapeHtml(user.username)}
                                    <span style="background: #00ff00; color: #000; padding: 2px 8px; border-radius: 4px;
                                                 font-size: 12px; margin-left: 10px;">${escapeHtml(user.role.toUpperCase())}</span>
                                </div>
                                <div style="color: #999; font-size: 13px; margin-top: 5px;">
                                    Created: ${new Date(user.created_at).toLocaleString()} | Last Login: ${lastLogin}
                                </div>
                            </div>
                            <button onclick="deleteUser('${escapeHtml(user.username)}')" 
                                    style="background: #ff4444; color: #fff; border: none; padding: 8px 15px; 
                                           border-radius: 5px; cursor: pointer; font-weight: bold;">
                                Delete
                            </button>
                        </div>
                    </div>
                `;
            });
            html += '</div>';
            listEl.innerHTML = html;
        }
        
        async function createUser() {
            const username = document.getElementById('newUsername').value.trim();
            const password = document.getElementById('newUserPassword').value;
            const passwordConfirm = document.getElementById('newUserPasswordConfirm').value;
            const role = document.getElementById('newUserRole').value;
            
            if (!username || !password) {
                showUserMessage('error', 'Error:  Username and password are required');
                return;
            }
            
            if (password !== passwordConfirm) {
                showUserMessage('error', 'Error:  Passwords do not match');
                return;
            }
            
            // Validate password complexity
            const validation = validatePasswordComplexity(password);
            if (!validation.isValid) {
                showUserMessage('error', 'Error: Password does not meet requirements: ' + validation.missing.join(', '));
                return;
            }
            
            try {
                const response = await fetch('/api/fleet/users/create', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    credentials: 'include',
                    body: JSON.stringify({ username, password, role })
                });
                
                const data = await response.json();
                
                if (data.success) {
                    showUserMessage('success', 'Success:  ' + data.message);
                    document.getElementById('newUsername').value = '';
                    document.getElementById('newUserPassword').value = '';
                    document.getElementById('newUserPasswordConfirm').value = '';
                    loadUsers();
                } else {
                    showUserMessage('error', 'Error:  ' + data.message);
                }
            } catch (e) {
                showUserMessage('error', 'Error:  Error creating user: ' + e.message);
            }
        }
        
        async function changePassword() {
            const currentPassword = document.getElementById('currentPassword').value;
            const newPassword = document.getElementById('newPassword').value;
            const newPasswordConfirm = document.getElementById('newPasswordConfirm').value;
            
            if (!currentPassword || !newPassword) {
                showUserMessage('error', 'Error:  All password fields are required');
                return;
            }
            
            if (newPassword !== newPasswordConfirm) {
                showUserMessage('error', 'Error:  New passwords do not match');
                return;
            }
            
            if (newPassword.length < 8) {
                showUserMessage('error', 'Error:  Password must be at least 8 characters');
                return;
            }
            
            try {
                const response = await fetch('/api/fleet/users/change-password', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    credentials: 'include',
                    body: JSON.stringify({ current_password: currentPassword, new_password: newPassword })
                });
                
                const data = await response.json();
                
                if (data.success) {
                    showUserMessage('success', 'Success:  ' + data.message);
                    document.getElementById('currentPassword').value = '';
                    document.getElementById('newPassword').value = '';
                    document.getElementById('newPasswordConfirm').value = '';
                } else {
                    showUserMessage('error', 'Error:  ' + data.message);
                }
            } catch (e) {
                showUserMessage('error', 'Error:  Error changing password: ' + e.message);
            }
        }
        
        async function deleteUser(username) {
            if (!confirm(`Are you sure you want to delete user "${username}"?`)) {
                return;
            }
            
            try {
                const response = await fetch('/api/fleet/users/delete', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    credentials: 'include',
                    body: JSON.stringify({ username })
                });
                
                const data = await response.json();
                
                if (data.success) {
                    showUserMessage('success', 'Success:  ' + data.message);
                    loadUsers();
                } else {
                    showUserMessage('error', 'Error:  ' + data.message);
                }
            } catch (e) {
                showUserMessage('error', 'Error:  Error deleting user: ' + e.message);
            }
        }
        
        function showUserMessage(type, text) {
            const messageEl = document.getElementById('userMessage');
            messageEl.className = 'message ' + type;
            messageEl.textContent = text;
            messageEl.style.display = 'block';
            
            setTimeout(() => {
                messageEl.style.display = 'none';
            }, 5000);
        }
        
        // Load users on page load
        loadUsers();
        
        // Check if password needs update
        checkPasswordUpdate();
        
        // Session Management Functions
        let sessionTimeout = 30; // minutes
        let sessionWarning = 2; // minutes
        let lastActivityTime = Date.now();
        let sessionTimer = null;
        let warningTimer = null;
        
        function loadSessionSettings() {
            const saved = localStorage.getItem('sessionSettings');
            if (saved) {
                const settings = JSON.parse(saved);
                sessionTimeout = settings.timeout || 30;
                sessionWarning = settings.warning || 2;
                
                document.getElementById('sessionTimeout').value = sessionTimeout;
                document.getElementById('sessionWarning').value = sessionWarning;
            }
            updateSessionInfo();
            startSessionTimer();
        }
        
        function saveSessionSettings() {
            sessionTimeout = parseInt(document.getElementById('sessionTimeout').value);
            sessionWarning = parseInt(document.getElementById('sessionWarning').value);
            
            const settings = {
                timeout: sessionTimeout,
                warning: sessionWarning
            };
            
            localStorage.setItem('sessionSettings', JSON.stringify(settings));
            showUserMessage('success', 'Success:  Session settings saved successfully');
            
            updateSessionInfo();
            startSessionTimer();
        }
        
        function updateSessionInfo() {
            const timeoutText = sessionTimeout === 0 ? 'No Timeout' : sessionTimeout + ' Minutes';
            const warningText = sessionWarning === 0 ? 'No Warning' : sessionWarning + ' Minutes';
            
            document.getElementById('currentTimeout').textContent = timeoutText;
            document.getElementById('currentWarning').textContent = warningText;
            updateLastActivity();
        }
        
        function updateLastActivity() {
            const now = Date.now();
            const elapsed = Math.floor((now - lastActivityTime) / 1000);
            
            let text;
            if (elapsed < 60) {
                text = 'Just now';
            } else if (elapsed < 3600) {
                text = Math.floor(elapsed / 60) + ' minutes ago';
            } else {
                text = Math.floor(elapsed / 3600) + ' hours ago';
            }
            
            document.getElementById('lastActivity').textContent = text;
        }
        
        function resetActivity() {
            lastActivityTime = Date.now();
            updateLastActivity();
            startSessionTimer();
        }
        
        function startSessionTimer() {
            // Clear existing timers
            if (sessionTimer) clearTimeout(sessionTimer);
            if (warningTimer) clearTimeout(warningTimer);
            
            if (sessionTimeout === 0) return; // No timeout
            
            const timeoutMs = sessionTimeout * 60 * 1000;
            const warningMs = sessionWarning * 60 * 1000;
            
            // Set warning timer
            if (sessionWarning > 0 && sessionWarning < sessionTimeout) {
                warningTimer = setTimeout(() => {
                    const remaining = sessionTimeout - sessionWarning;
                    if (confirm(`Your session will expire in ${remaining} minute(s) due to inactivity. Click OK to stay logged in.`)) {
                        resetActivity();
                    }
                }, timeoutMs - warningMs);
            }
            
            // Set logout timer
            sessionTimer = setTimeout(() => {
                alert('Your session has expired due to inactivity. You will be logged out.');
                window.location.href = '/dashboard?logout=1';
                setTimeout(() => window.location.reload(), 100);
            }, timeoutMs);
        }
        
        // Track user activity
        ['mousedown', 'keydown', 'scroll', 'touchstart'].forEach(event => {
            document.addEventListener(event, resetActivity, true);
        });
        
        // Update last activity display every 30 seconds
        setInterval(updateLastActivity, 30000);
        
        // Load session settings on page load
        loadSessionSettings();
        
        // API Key Management Functions
        function showApiKeyPrompt() {
            document.getElementById('apiKeyPasswordModal').style.display = 'block';
            document.getElementById('apiKeyPassword').value = '';
            document.getElementById('apiKeyPasswordError').style.display = 'none';
            document.getElementById('apiKeyPassword').dataset.target = 'api';
        }
        
        function closeApiKeyPasswordModal() {
            document.getElementById('apiKeyPasswordModal').style.display = 'none';
            document.getElementById('apiKeyPassword').value = '';
            document.getElementById('apiKeyPasswordError').style.display = 'none';
        }
        
        async function verifyPasswordAndShowKey() {
            const password = document.getElementById('apiKeyPassword').value;
            const errorEl = document.getElementById('apiKeyPasswordError');
            const target = document.getElementById('apiKeyPassword').dataset.target;
            
            if (!password) {
                errorEl.textContent = 'Please enter your password';
                errorEl.style.display = 'block';
                return;
            }
            
            // Check if this is for encryption key or API key
            if (target === 'encryption') {
                await verifyPasswordAndShowEncryptionKey();
                return;
            }
            
            try {
                const response = await fetch('/api/fleet/verify-and-get-key', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    credentials: 'include',
                    body: JSON.stringify({ password: password })
                });
                
                const data = await response.json();
                
                if (data.success) {
                    // Show the API key
                    document.getElementById('apiKeyDisplay').value = data.api_key;
                    document.getElementById('apiKeyHidden').style.display = 'none';
                    document.getElementById('apiKeyVisible').style.display = 'block';
                    closeApiKeyPasswordModal();
                } else {
                    errorEl.textContent = data.message || 'Incorrect password';
                    errorEl.style.display = 'block';
                }
            } catch (e) {
                errorEl.textContent = 'Error verifying password: ' + e.message;
                errorEl.style.display = 'block';
            }
        }
        
        function hideApiKey() {
            document.getElementById('apiKeyHidden').style.display = 'block';
            document.getElementById('apiKeyVisible').style.display = 'none';
            document.getElementById('apiKeyDisplay').value = '';
        }
        
        function copyApiKey() {
            const keyInput = document.getElementById('apiKeyDisplay');
            keyInput.select();
            document.execCommand('copy');
            
            showApiKeyMessage('success', 'Success:  API key copied to clipboard!');
        }
        
        async function regenerateApiKey() {
            if (!confirm('WARNING: Regenerating the API key will disconnect ALL existing agents!\\n\\nThey will need to be reconfigured with the new key.\\n\\nAre you sure you want to continue?')) {
                return;
            }
            
            const password = prompt('Please enter your password to confirm:');
            if (!password) {
                return;
            }
            
            try {
                const response = await fetch('/api/fleet/regenerate-key', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    credentials: 'include',
                    body: JSON.stringify({ password: password })
                });
                
                const data = await response.json();
                
                if (data.success) {
                    document.getElementById('apiKeyDisplay').value = data.new_api_key;
                    showApiKeyMessage('success', 'Success:  API key regenerated successfully! Make sure to update all agents.');
                } else {
                    showApiKeyMessage('error', 'Error:  ' + data.message);
                }
            } catch (e) {
                showApiKeyMessage('error', 'Error:  Error regenerating key: ' + e.message);
            }
        }
        
        function showApiKeyMessage(type, text) {
            const messageEl = document.getElementById('apiKeyMessage');
            messageEl.className = 'message ' + type;
            messageEl.textContent = text;
            messageEl.style.display = 'block';
            
            setTimeout(() => {
                messageEl.style.display = 'none';
            }, 5000);
        }
        
        // Allow Enter key to submit password
        document.addEventListener('DOMContentLoaded', function() {
            const passwordInput = document.getElementById('apiKeyPassword');
            if (passwordInput) {
                passwordInput.addEventListener('keypress', function(e) {
                    if (e.key === 'Enter') {
                        verifyPasswordAndShowKey();
                    }
                });
            }
            
            // Check E2EE status on page load
            checkE2EEStatus();
        });
        
        // E2EE Encryption Key Management Functions
        async function checkE2EEStatus() {
            try {
                const response = await fetch('/api/fleet/e2ee-status', {
                    credentials: 'include'
                });
                const data = await response.json();
                
                const statusIcon = document.getElementById('e2eeStatusIcon');
                const statusText = document.getElementById('e2eeStatusText');
                const showBtn = document.getElementById('showE2eeKeyBtn');
                const generateBtn = document.getElementById('generateE2eeKeyBtn');
                
                if (data.has_key) {
                    statusIcon.textContent = '';
                    statusText.innerHTML = '<span style="color: #00ff00;">E2EE is ENABLED</span><br><small style="color: #666;">All agent communications are encrypted</small>';
                    showBtn.style.display = 'inline-block';
                    generateBtn.style.display = 'none';
                } else {
                    statusIcon.textContent = '';
                    statusText.innerHTML = '<span style="color: #ffd93d;">E2EE is NOT CONFIGURED</span><br><small style="color: #666;">Generate a key to enable encryption</small>';
                    showBtn.style.display = 'none';
                    generateBtn.style.display = 'inline-block';
                }
            } catch (e) {
                console.error('Error checking E2EE status:', e);
            }
        }
        
        function showEncryptionKeyPrompt() {
            // Use the same password modal
            document.getElementById('apiKeyPasswordModal').style.display = 'block';
            document.getElementById('apiKeyPassword').value = '';
            document.getElementById('apiKeyPasswordError').style.display = 'none';
            document.getElementById('apiKeyPassword').dataset.target = 'encryption';
        }
        
        async function verifyPasswordAndShowEncryptionKey() {
            const password = document.getElementById('apiKeyPassword').value;
            const errorEl = document.getElementById('apiKeyPasswordError');
            
            if (!password) {
                errorEl.textContent = 'Please enter your password';
                errorEl.style.display = 'block';
                return;
            }
            
            try {
                const response = await fetch('/api/fleet/verify-and-get-encryption-key', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    credentials: 'include',
                    body: JSON.stringify({ password: password })
                });
                
                const data = await response.json();
                
                if (data.success) {
                    document.getElementById('encryptionKeyDisplay').value = data.encryption_key;
                    document.getElementById('encryptionKeyStatus').style.display = 'none';
                    document.getElementById('encryptionKeyVisible').style.display = 'block';
                    closeApiKeyPasswordModal();
                } else {
                    errorEl.textContent = data.message || 'Incorrect password';
                    errorEl.style.display = 'block';
                }
            } catch (e) {
                errorEl.textContent = 'Error verifying password: ' + e.message;
                errorEl.style.display = 'block';
            }
        }
        
        function hideEncryptionKey() {
            document.getElementById('encryptionKeyStatus').style.display = 'block';
            document.getElementById('encryptionKeyVisible').style.display = 'none';
            document.getElementById('encryptionKeyDisplay').value = '';
        }
        
        function copyEncryptionKey() {
            const keyInput = document.getElementById('encryptionKeyDisplay');
            keyInput.select();
            document.execCommand('copy');
            
            showEncryptionKeyMessage('success', 'Success: Encryption key copied to clipboard!');
        }
        
        async function generateEncryptionKey() {
            if (!confirm('Generate a new E2EE encryption key?\\n\\nThis key will be automatically included in all agent packages built from this server.')) {
                return;
            }
            
            const password = prompt('Please enter your password to confirm:');
            if (!password) return;
            
            try {
                const response = await fetch('/api/fleet/generate-encryption-key', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    credentials: 'include',
                    body: JSON.stringify({ password: password })
                });
                
                const data = await response.json();
                
                if (data.success) {
                    document.getElementById('encryptionKeyDisplay').value = data.encryption_key;
                    document.getElementById('encryptionKeyStatus').style.display = 'none';
                    document.getElementById('encryptionKeyVisible').style.display = 'block';
                    showEncryptionKeyMessage('success', 'Success: E2EE encryption key generated! This key will be included in agent packages.');
                } else {
                    showEncryptionKeyMessage('error', 'Error: ' + data.message);
                }
            } catch (e) {
                showEncryptionKeyMessage('error', 'Error generating key: ' + e.message);
            }
        }
        
        async function rotateEncryptionKeyRemotely() {
            if (!confirm('Rotate E2EE encryption key?\\n\\nThe new key will be securely pushed to all connected agents.\\nAgents will update automatically on their next poll (within 60 seconds).\\n\\nContinue?')) {
                return;
            }
            
            const password = prompt('Please enter your password to confirm:');
            if (!password) return;
            
            try {
                const response = await fetch('/api/fleet/rotate-encryption-key', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    credentials: 'include',
                    body: JSON.stringify({ password: password })
                });
                
                const data = await response.json();
                
                if (data.success) {
                    document.getElementById('encryptionKeyDisplay').value = data.encryption_key;
                    showEncryptionKeyMessage('success', `Success: Key rotation queued for ${data.agents_queued} agent(s). They will update automatically.`);
                    
                    // Show rotation status panel and start monitoring
                    document.getElementById('keyRotationStatus').style.display = 'block';
                    document.getElementById('rotationStatusList').innerHTML = `<div style="color: #ffd93d;">⏳ Waiting for ${data.agents_queued} agent(s) to confirm...</div>`;
                    
                    // Start polling for status updates
                    setTimeout(refreshRotationStatus, 3000);
                } else {
                    showEncryptionKeyMessage('error', 'Error: ' + data.message);
                }
            } catch (e) {
                showEncryptionKeyMessage('error', 'Error rotating key: ' + e.message);
            }
        }
        
        async function regenerateEncryptionKey() {
            if (!confirm('WARNING: This will generate a NEW key WITHOUT pushing to agents!\\n\\nAll existing agents will stop reporting until reinstalled.\\n\\nUse "Rotate Key" instead for seamless updates.\\n\\nAre you SURE you want to force a new key?')) {
                return;
            }
            
            const password = prompt('Please enter your password to confirm:');
            if (!password) return;
            
            try {
                const response = await fetch('/api/fleet/regenerate-encryption-key', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    credentials: 'include',
                    body: JSON.stringify({ password: password })
                });
                
                const data = await response.json();
                
                if (data.success) {
                    document.getElementById('encryptionKeyDisplay').value = data.encryption_key;
                    showEncryptionKeyMessage('success', 'Success: New key generated. Rebuild and reinstall all agent packages.');
                } else {
                    showEncryptionKeyMessage('error', 'Error: ' + data.message);
                }
            } catch (e) {
                showEncryptionKeyMessage('error', 'Error regenerating key: ' + e.message);
            }
        }
        
        function showEncryptionKeyMessage(type, text) {
            const messageEl = document.getElementById('encryptionKeyMessage');
            messageEl.className = 'message ' + type;
            messageEl.textContent = text;
            messageEl.style.display = 'block';
            
            setTimeout(() => {
                messageEl.style.display = 'none';
            }, 5000);
        }
        
        async function refreshRotationStatus() {
            try {
                const response = await fetch('/api/fleet/key-rotation-status', {
                    credentials: 'include'
                });
                const data = await response.json();
                
                if (data.success && data.rotations.length > 0) {
                    document.getElementById('keyRotationStatus').style.display = 'block';
                    
                    let html = '<table style="width: 100%; border-collapse: collapse;">';
                    html += '<tr style="border-bottom: 1px solid #333;"><th style="text-align: left; padding: 5px; color: #00c8ff;">Agent</th><th style="text-align: left; padding: 5px; color: #00c8ff;">Status</th><th style="text-align: left; padding: 5px; color: #00c8ff;">Time</th></tr>';
                    
                    for (const rotation of data.rotations) {
                        let statusIcon, statusColor;
                        switch (rotation.status) {
                            case 'completed':
                                statusIcon = '';
                                statusColor = '#00ff00';
                                break;
                            case 'failed':
                                statusIcon = '';
                                statusColor = '#ff4444';
                                break;
                            default:
                                statusIcon = '⏳';
                                statusColor = '#ffd93d';
                        }
                        
                        const time = rotation.executed_at || rotation.created_at;
                        const timeStr = time ? new Date(time).toLocaleString() : 'Pending...';
                        const resultMsg = rotation.result?.message || '';
                        
                        html += `<tr style="border-bottom: 1px solid #222;">`;
                        html += `<td style="padding: 8px; color: #fff;">${escapeHtml(rotation.hostname)}</td>`;
                        html += `<td style="padding: 8px; color: ${statusColor};">${statusIcon} ${escapeHtml(rotation.status)}${resultMsg ? ' - ' + escapeHtml(resultMsg) : ''}</td>`;
                        html += `<td style="padding: 8px; color: #666;">${escapeHtml(timeStr)}</td>`;
                        html += `</tr>`;
                    }
                    html += '</table>';
                    
                    document.getElementById('rotationStatusList').innerHTML = html;
                } else {
                    document.getElementById('keyRotationStatus').style.display = 'none';
                }
            } catch (e) {
                console.error('Error fetching rotation status:', e);
            }
        }
        
        // Auto-refresh rotation status every 10 seconds if visible
        setInterval(() => {
            if (document.getElementById('keyRotationStatus').style.display !== 'none') {
                refreshRotationStatus();
            }
        }, 10000);
        
        // Load Balancer Generator Functions
        async function generateLoadBalancerPackage() {
            const generatingEl = document.getElementById('generatingLoadBalancer');
            const messageEl = document.getElementById('loadBalancerMessage');
            const port = document.getElementById('lbGeneratorPort').value;
            const packageName = document.getElementById('lbGeneratorName').value;
            
            if (!packageName) {
                messageEl.className = 'message error';
                messageEl.textContent = 'Please specify a package name';
                messageEl.style.display = 'block';
                setTimeout(() => messageEl.style.display = 'none', 5000);
                return;
            }
            
            generatingEl.style.display = 'block';
            messageEl.style.display = 'none';
            
            try {
                const response = await fetch('/api/fleet/generate-loadbalancer', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json'
                    },
                    body: JSON.stringify({
                        port: parseInt(port) || 8778,
                        package_name: packageName
                    })
                });
                
                generatingEl.style.display = 'none';
                
                if (response.ok) {
                    // Download the package
                    const blob = await response.blob();
                    const url = window.URL.createObjectURL(blob);
                    const a = document.createElement('a');
                    a.href = url;
                    a.download = packageName;
                    document.body.appendChild(a);
                    a.click();
                    window.URL.revokeObjectURL(url);
                    document.body.removeChild(a);
                    
                    messageEl.className = 'message success';
                    messageEl.textContent = 'Load balancer package generated successfully! Download started.';
                    messageEl.style.display = 'block';
                    setTimeout(() => messageEl.style.display = 'none', 5000);
                } else {
                    const error = await response.json();
                    messageEl.className = 'message error';
                    messageEl.textContent = '' + (error.error || 'Failed to generate package');
                    messageEl.style.display = 'block';
                }
            } catch (e) {
                generatingEl.style.display = 'none';
                messageEl.className = 'message error';
                messageEl.textContent = 'Error generating package: ' + e.message;
                messageEl.style.display = 'block';
            }
        }
        
        async function refreshLBClusterStatus() {
            const statusEl = document.getElementById('lbClusterStatus');
            const warningEl = document.getElementById('notClusteredLBWarning');
            
            statusEl.innerHTML = `
                <div class="loading">
                    <div class="spinner"></div>
                    <div>Loading cluster information...</div>
                </div>
            `;
            
            try {
                const response = await fetch('/api/fleet/cluster/status');
                const data = await response.json();
                
                if (data.enabled) {
                    warningEl.style.display = 'none';
                    
                    // Get nodes
                    const nodesResponse = await fetch('/api/fleet/cluster/nodes');
                    const nodesData = await nodesResponse.json();
                    
                    let html = `
                        <div style="display: grid; grid-template-columns: repeat(3, 1fr); gap: 15px; margin-bottom: 15px;">
                            <div>
                                <div style="font-size: 12px; color: #666;">Cluster Mode</div>
                                <div style="font-size: 18px; color: #00ff00;">Enabled</div>
                            </div>
                            <div>
                                <div style="font-size: 12px; color: #666;">Backend</div>
                                <div style="font-size: 18px; color: #fff;">${escapeHtml(data.backend || 'Unknown')}</div>
                            </div>
                            <div>
                                <div style="font-size: 12px; color: #666;">Active Nodes</div>
                                <div style="font-size: 18px; color: #fff;">${nodesData.count || 0}</div>
                            </div>
                        </div>
                    `;
                    
                    if (nodesData.nodes && nodesData.nodes.length > 0) {
                        html += `
                            <div style="background: #2a2a2a; padding: 10px; border-radius: 5px;">
                                <div style="font-size: 12px; color: #666; margin-bottom: 5px;">Nodes to Include:</div>
                                <ul style="margin: 5px 0; padding-left: 20px; color: #999; font-size: 13px;">
                        `;
                        nodesData.nodes.forEach(node => {
                            html += `<li>${escapeHtml(node.node_id)} (${escapeHtml(node.host || 'unknown')})</li>`;
                        });
                        html += `
                                </ul>
                            </div>
                        `;
                    }
                    
                    statusEl.innerHTML = html;
                } else {
                    warningEl.style.display = 'block';
                    statusEl.innerHTML = `
                        <div style="text-align: center; padding: 20px; color: #999;">
                            <div style="font-size: 48px; margin-bottom: 10px;">📍</div>
                            <div>Standalone Mode</div>
                            <div style="font-size: 13px; margin-top: 5px;">
                                You can still generate a load balancer package for future clustering
                            </div>
                        </div>
                    `;
                }
            } catch (e) {
                statusEl.innerHTML = `
                    <div style="color: #ff4444; text-align: center; padding: 20px;">
                        Error loading cluster status: ${escapeHtml(e.message)}
                    </div>
                `;
            }
        }

        function viewLBDocs() {
            window.open('https://docs.haproxy.org/', '_blank');
        }
        
        // Cluster Health Monitor Functions
        async function runClusterHealthCheck() {
            const runningEl = document.getElementById('runningHealthCheck');
            const resultsEl = document.getElementById('clusterHealthResults');
            const warningEl = document.getElementById('notClusteredHealthWarning');
            const messageEl = document.getElementById('clusterHealthMessage');
            
            runningEl.style.display = 'block';
            resultsEl.style.display = 'none';
            warningEl.style.display = 'none';
            messageEl.style.display = 'none';
            
            try {
                // Check if cluster is enabled first
                const statusResponse = await fetch('/api/fleet/cluster/status');
                const statusData = await statusResponse.json();
                
                if (!statusData.enabled) {
                    runningEl.style.display = 'none';
                    warningEl.style.display = 'block';
                    return;
                }
                
                // Run comprehensive health check
                const healthResponse = await fetch('/api/fleet/cluster/health-check');
                const healthData = await healthResponse.json();
                
                runningEl.style.display = 'none';
                resultsEl.style.display = 'block';
                
                // Update overall status
                updateOverallHealth(healthData);
                
                // Update backend status
                updateBackendStatus(healthData.backend);
                
                // Update node status
                updateNodeStatus(healthData.nodes);
                
                // Update sync status
                updateSyncStatus(healthData.sync);
                
                // Update failover status
                updateFailoverStatus(healthData.failover);
                
                messageEl.className = 'message success';
                messageEl.textContent = 'Health check completed successfully';
                messageEl.style.display = 'block';
                setTimeout(() => messageEl.style.display = 'none', 5000);
                
            } catch (e) {
                runningEl.style.display = 'none';
                messageEl.className = 'message error';
                messageEl.textContent = 'Error running health check: ' + e.message;
                messageEl.style.display = 'block';
            }
        }
        
        function updateOverallHealth(healthData) {
            const textEl = document.getElementById('overallHealthText');
            const iconEl = document.getElementById('overallHealthIcon');
            const statusEl = document.getElementById('overallHealthStatus');
            
            if (healthData.overall === 'healthy') {
                textEl.textContent = 'Healthy';
                textEl.style.color = '#00ff00';
                iconEl.textContent = '';
                statusEl.style.background = '#2a2a2a';
            } else if (healthData.overall === 'degraded') {
                textEl.textContent = 'Degraded';
                textEl.style.color = '#ff8800';
                iconEl.textContent = '';
                statusEl.style.background = '#3a2a00';
            } else {
                textEl.textContent = 'Critical';
                textEl.style.color = '#ff4444';
                iconEl.textContent = '';
                statusEl.style.background = '#3a0000';
            }
        }
        
        function updateBackendStatus(backend) {
            const el = document.getElementById('backendStatus');
            
            if (backend.connected) {
                el.innerHTML = `
                    <div style="display: grid; grid-template-columns: repeat(3, 1fr); gap: 15px;">
                        <div>
                            <div style="font-size: 12px; color: #666;">Backend Type</div>
                            <div style="font-size: 18px; color: #fff;">${escapeHtml(backend.type || 'Unknown')}</div>
                        </div>
                        <div>
                            <div style="font-size: 12px; color: #666;">Connection Status</div>
                            <div style="font-size: 18px; color: #00ff00;">Connected</div>
                        </div>
                        <div>
                            <div style="font-size: 12px; color: #666;">Latency</div>
                            <div style="font-size: 18px; color: #fff;">${backend.latency_ms || 0}ms</div>
                        </div>
                    </div>
                    ${backend.host ? `<div style="margin-top: 15px; padding: 10px; background: #2a2a2a; border-radius: 5px;">
                        <div style="font-size: 12px; color: #666;">Host</div>
                        <div style="font-size: 14px; color: #999; font-family: monospace;">${escapeHtml(backend.host)}</div>
                    </div>` : ''}
                `;
            } else {
                el.innerHTML = `
                    <div style="color: #ff4444; padding: 15px; background: #3a0000; border-radius: 5px;">
                        Backend connection failed: ${escapeHtml(backend.error || 'Unknown error')}
                    </div>
                `;
            }
        }
        
        function updateNodeStatus(nodes) {
            const el = document.getElementById('nodeStatusTable');
            
            if (!nodes || nodes.length === 0) {
                el.innerHTML = '<div style="color: #999; text-align: center;">No nodes found</div>';
                return;
            }
            
            let html = `
                <table style="width: 100%; border-collapse: collapse;">
                    <thead>
                        <tr style="border-bottom: 1px solid #444;">
                            <th style="padding: 10px; text-align: left; color: #666; font-size: 12px;">Node ID</th>
                            <th style="padding: 10px; text-align: left; color: #666; font-size: 12px;">Status</th>
                            <th style="padding: 10px; text-align: left; color: #666; font-size: 12px;">Last Heartbeat</th>
                            <th style="padding: 10px; text-align: left; color: #666; font-size: 12px;">IP Address</th>
                            <th style="padding: 10px; text-align: left; color: #666; font-size: 12px;">Uptime</th>
                        </tr>
                    </thead>
                    <tbody>
            `;
            
            nodes.forEach(node => {
                const statusColor = node.status === 'healthy' ? '#00ff00' : (node.status === 'degraded' ? '#ff8800' : '#ff4444');
                const statusIcon = node.status === 'healthy' ? '' : (node.status === 'degraded' ? '' : '');
                const isCurrentNode = node.is_current ? ' (This Node)' : '';
                
                html += `
                    <tr style="border-bottom: 1px solid #333;">
                        <td style="padding: 10px; color: #fff; font-family: monospace; font-size: 13px;">
                            ${escapeHtml(node.node_id)}${isCurrentNode}
                        </td>
                        <td style="padding: 10px; color: ${statusColor};">
                            ${statusIcon} ${escapeHtml(node.status)}
                        </td>
                        <td style="padding: 10px; color: #999; font-size: 13px;">
                            ${escapeHtml(node.last_heartbeat || 'N/A')}
                        </td>
                        <td style="padding: 10px; color: #999; font-family: monospace; font-size: 13px;">
                            ${escapeHtml(node.host || 'N/A')}
                        </td>
                        <td style="padding: 10px; color: #999; font-size: 13px;">
                            ${escapeHtml(node.uptime || 'N/A')}
                        </td>
                    </tr>
                `;
            });
            
            html += '</tbody></table>';
            el.innerHTML = html;
        }
        
        function updateSyncStatus(sync) {
            const el = document.getElementById('syncStatus');
            
            if (sync.synced) {
                el.innerHTML = `
                    <div style="display: grid; grid-template-columns: repeat(3, 1fr); gap: 15px;">
                        <div>
                            <div style="font-size: 12px; color: #666;">Sync Status</div>
                            <div style="font-size: 18px; color: #00ff00;">In Sync</div>
                        </div>
                        <div>
                            <div style="font-size: 12px; color: #666;">Session Count</div>
                            <div style="font-size: 18px; color: #fff;">${sync.session_count || 0}</div>
                        </div>
                        <div>
                            <div style="font-size: 12px; color: #666;">Last Sync</div>
                            <div style="font-size: 18px; color: #fff;">${escapeHtml(sync.last_sync || 'N/A')}</div>
                        </div>
                    </div>
                    ${sync.details ? `<div style="margin-top: 15px; padding: 10px; background: #2a2a2a; border-radius: 5px;">
                        <div style="font-size: 12px; color: #666;">Details</div>
                        <div style="font-size: 13px; color: #999;">${escapeHtml(sync.details)}</div>
                    </div>` : ''}
                `;
            } else {
                el.innerHTML = `
                    <div style="color: #ff8800; padding: 15px; background: #3a2a00; border-radius: 5px;">
                        Sync issues detected: ${escapeHtml(sync.error || 'Unknown issue')}
                    </div>
                `;
            }
        }
        
        function updateFailoverStatus(failover) {
            const el = document.getElementById('failoverStatus');
            
            if (failover.ready) {
                el.innerHTML = `
                    <div style="padding: 15px; background: #00330055; border-radius: 5px; border-left: 4px solid #00ff00;">
                        <div style="color: #00ff00; font-weight: bold; margin-bottom: 10px;">Cluster is Failover Ready</div>
                        <div style="color: #99cc99; font-size: 13px; line-height: 1.6;">
                            ${failover.healthy_nodes || 0} healthy nodes available.
                            If any single node fails, the cluster will automatically continue operating on the remaining nodes.
                            ${escapeHtml(failover.details || '')}
                        </div>
                    </div>
                `;
            } else {
                el.innerHTML = `
                    <div style="padding: 15px; background: #3a2a00; border-radius: 5px; border-left: 4px solid #ff8800;">
                        <div style="color: #ff8800; font-weight: bold; margin-bottom: 10px;">Failover Risk</div>
                        <div style="color: #ffcc99; font-size: 13px; line-height: 1.6;">
                            Only ${failover.healthy_nodes || 0} healthy node(s) available. 
                            For true high availability, you need at least 2 healthy nodes. 
                            Consider adding more cluster nodes.
                        </div>
                    </div>
                `;
            }
        }
        
        function refreshClusterHealth() {
            runClusterHealthCheck();
        }
        
        // Server Package Builder Functions
        let selectedPackageType = null;
        
        function selectPackageType(type) {
            selectedPackageType = type;
            
            // Update UI selection
            document.getElementById('standaloneOption').classList.remove('selected');
            document.getElementById('clusterOption').classList.remove('selected');
            document.getElementById('packageTypeStandalone').checked = false;
            document.getElementById('packageTypeCluster').checked = false;
            
            if (type === 'standalone') {
                document.getElementById('standaloneOption').classList.add('selected');
                document.getElementById('packageTypeStandalone').checked = true;
                document.getElementById('standalonePackageConfig').style.display = 'block';
                document.getElementById('clusterPackageConfig').style.display = 'none';
                document.getElementById('clusterStatus').style.display = 'none';
                document.getElementById('notClusteredWarning').style.display = 'none';
            } else if (type === 'cluster') {
                document.getElementById('clusterOption').classList.add('selected');
                document.getElementById('packageTypeCluster').checked = true;
                document.getElementById('standalonePackageConfig').style.display = 'none';
                document.getElementById('clusterStatus').style.display = 'block';
                document.getElementById('notClusteredWarning').style.display = 'none';
                
                // Load cluster status
                loadClusterStatus();
            }
        }
        
        async function loadClusterStatus() {
            const loadingEl = document.getElementById('loadingClusterStatus');
            const statusEl = document.getElementById('clusterStatus');
            const configEl = document.getElementById('clusterPackageConfig');
            const warningEl = document.getElementById('notClusteredWarning');
            
            loadingEl.style.display = 'block';
            
            try {
                const response = await fetch('/api/fleet/cluster/status');
                const data = await response.json();
                
                loadingEl.style.display = 'none';
                
                if (data.enabled) {
                    // Show cluster status
                    statusEl.innerHTML = `
                        <div style="color: #00ff00; font-weight: bold; margin-bottom: 10px;">
                            Cluster Mode Enabled
                        </div>
                        <div style="display: grid; grid-template-columns: repeat(3, 1fr); gap: 15px; color: #999;">
                            <div>
                                <div style="font-size: 12px; color: #666;">Backend</div>
                                <div style="font-size: 18px; color: #fff;">${escapeHtml(data.backend || 'Unknown')}</div>
                            </div>
                            <div>
                                <div style="font-size: 12px; color: #666;">Active Nodes</div>
                                <div style="font-size: 18px; color: #fff;">${data.active_nodes || 0}</div>
                            </div>
                            <div>
                                <div style="font-size: 12px; color: #666;">This Node ID</div>
                                <div style="font-size: 14px; color: #fff; font-family: monospace;">${escapeHtml(data.node_id || 'Unknown')}</div>
                            </div>
                        </div>
                    `;
                    statusEl.style.display = 'block';
                    configEl.style.display = 'block';
                    warningEl.style.display = 'none';
                } else {
                    // Show not clustered warning
                    statusEl.style.display = 'none';
                    configEl.style.display = 'none';
                    warningEl.style.display = 'block';
                }
            } catch (e) {
                loadingEl.style.display = 'none';
                statusEl.innerHTML = '<div style="color: #ff4444; text-align: center;">Error loading cluster status</div>';
                statusEl.style.display = 'block';
                warningEl.style.display = 'block';
                configEl.style.display = 'none';
            }
        }
        
        async function buildStandalonePackage() {
            const buildingEl = document.getElementById('buildingStandalonePackage');
            const messageEl = document.getElementById('serverPackageMessage');
            const serverName = document.getElementById('standaloneServerName').value;
            const packageName = document.getElementById('standalonePackageName').value;
            
            if (!packageName) {
                messageEl.className = 'message error';
                messageEl.textContent = 'Please specify a package name';
                messageEl.style.display = 'block';
                setTimeout(() => messageEl.style.display = 'none', 5000);
                return;
            }
            
            buildingEl.style.display = 'block';
            messageEl.style.display = 'none';
            
            try {
                const response = await fetch('/api/fleet/build-standalone-package', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json'
                    },
                    body: JSON.stringify({
                        server_name: serverName || null,
                        package_name: packageName
                    })
                });
                
                buildingEl.style.display = 'none';
                
                if (response.ok) {
                    // Download the package
                    const blob = await response.blob();
                    const url = window.URL.createObjectURL(blob);
                    const a = document.createElement('a');
                    a.href = url;
                    a.download = packageName;
                    document.body.appendChild(a);
                    a.click();
                    window.URL.revokeObjectURL(url);
                    document.body.removeChild(a);
                    
                    messageEl.className = 'message success';
                    messageEl.textContent = 'Standalone server package built successfully! Download started.';
                    messageEl.style.display = 'block';
                    setTimeout(() => messageEl.style.display = 'none', 5000);
                } else {
                    const error = await response.json();
                    messageEl.className = 'message error';
                    messageEl.textContent = '' + (error.error || 'Failed to build package');
                    messageEl.style.display = 'block';
                }
            } catch (e) {
                buildingEl.style.display = 'none';
                messageEl.className = 'message error';
                messageEl.textContent = 'Error building package: ' + e.message;
                messageEl.style.display = 'block';
            }
        }
        
        async function buildClusterPackage() {
            const buildingEl = document.getElementById('buildingClusterPackage');
            const messageEl = document.getElementById('serverPackageMessage');
            const nodeName = document.getElementById('clusterNodeName').value;
            const packageName = document.getElementById('clusterPackageName').value;
            const includeLB = document.getElementById('includeLB').checked;
            const lbPort = document.getElementById('loadBalancerPort').value;
            
            if (!packageName) {
                messageEl.className = 'message error';
                messageEl.textContent = 'Please specify a package name';
                messageEl.style.display = 'block';
                setTimeout(() => messageEl.style.display = 'none', 5000);
                return;
            }
            
            buildingEl.style.display = 'block';
            messageEl.style.display = 'none';
            
            try {
                const response = await fetch('/api/fleet/build-cluster-package', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json'
                    },
                    body: JSON.stringify({
                        node_name: nodeName || null,
                        package_name: packageName,
                        include_loadbalancer: includeLB,
                        lb_port: parseInt(lbPort) || 8778
                    })
                });
                
                buildingEl.style.display = 'none';
                
                if (response.ok) {
                    // Check if response is JSON (multiple files) or single file
                    const contentType = response.headers.get('content-type');
                    
                    if (contentType && contentType.includes('application/json')) {
                        // Multiple packages built - get download URLs
                        const result = await response.json();
                        
                        // Download node package
                        if (result.node_package_url) {
                            const nodeBlob = await (await fetch(result.node_package_url)).blob();
                            const nodeUrl = window.URL.createObjectURL(nodeBlob);
                            const nodeLink = document.createElement('a');
                            nodeLink.href = nodeUrl;
                            nodeLink.download = packageName;
                            document.body.appendChild(nodeLink);
                            nodeLink.click();
                            window.URL.revokeObjectURL(nodeUrl);
                            document.body.removeChild(nodeLink);
                        }
                        
                        // Download load balancer package
                        if (result.lb_package_url) {
                            setTimeout(async () => {
                                const lbBlob = await (await fetch(result.lb_package_url)).blob();
                                const lbUrl = window.URL.createObjectURL(lbBlob);
                                const lbLink = document.createElement('a');
                                lbLink.href = lbUrl;
                                lbLink.download = result.lb_package_name || 'FleetLoadBalancer.tar.gz';
                                document.body.appendChild(lbLink);
                                lbLink.click();
                                window.URL.revokeObjectURL(lbUrl);
                                document.body.removeChild(lbLink);
                            }, 500);
                        }
                        
                        messageEl.className = 'message success';
                        messageEl.textContent = `Packages built successfully! ${result.lb_package_url ? 'Downloaded: Node package + Load balancer' : 'Downloaded: Node package'}`;
                        messageEl.style.display = 'block';
                        setTimeout(() => messageEl.style.display = 'none', 8000);
                    } else {
                        // Single package download (backward compatibility)
                        const blob = await response.blob();
                        const url = window.URL.createObjectURL(blob);
                        const a = document.createElement('a');
                        a.href = url;
                        a.download = packageName;
                        document.body.appendChild(a);
                        a.click();
                        window.URL.revokeObjectURL(url);
                        document.body.removeChild(a);
                        
                        messageEl.className = 'message success';
                        messageEl.textContent = 'Cluster node package built successfully! Download started.';
                        messageEl.style.display = 'block';
                        setTimeout(() => messageEl.style.display = 'none', 5000);
                    }
                } else {
                    const error = await response.json();
                    messageEl.className = 'message error';
                    messageEl.textContent = '' + (error.error || 'Failed to build package');
                    messageEl.style.display = 'block';
                }
            } catch (e) {
                buildingEl.style.display = 'none';
                messageEl.className = 'message error';
                messageEl.textContent = 'Error building package: ' + e.message;
                messageEl.style.display = 'block';
            }
        }
        
        function viewServerDocs() {
            window.open('/static/CLUSTER_SETUP_GUIDE.md', '_blank');
        }

        function viewClusterDocs() {
            window.open('/static/CLUSTER_SETUP_GUIDE.md', '_blank');
        }

        // ========================================
        // Export Logs
        // ========================================
        async function loadExportLogs() {
            const container = document.getElementById('exportLogsContent');
            const loading = document.getElementById('loadingExportLogs');
            loading.style.display = 'block';
            container.style.display = 'none';

            try {
                let url = '/api/fleet/export-logs?limit=200';
                const machineId = document.getElementById('exportLogsMachineFilter').value;
                if (machineId) url += '&machine_id=' + encodeURIComponent(machineId);

                const response = await fetch(url, { credentials: 'include' });
                const data = await response.json();
                const logs = data.logs || [];

                loading.style.display = 'none';
                container.style.display = 'block';

                if (logs.length === 0) {
                    container.innerHTML = '<div style="text-align: center; color: #666; padding: 30px;">No export logs found</div>';
                    return;
                }

                let html = '<table style="width: 100%; border-collapse: collapse;">';
                html += '<tr style="border-bottom: 1px solid #333;">';
                html += '<th style="text-align: left; padding: 8px; color: #00c8ff;">Date & Time</th>';
                html += '<th style="text-align: left; padding: 8px; color: #00c8ff;">Machine</th>';
                html += '<th style="text-align: left; padding: 8px; color: #00c8ff;">User</th>';
                html += '<th style="text-align: left; padding: 8px; color: #00c8ff;">Type</th>';
                html += '<th style="text-align: left; padding: 8px; color: #00c8ff;">Format</th>';
                html += '<th style="text-align: left; padding: 8px; color: #00c8ff;">Encryption</th>';
                html += '</tr>';

                for (const log of logs) {
                    const ts = log.timestamp ? new Date(log.timestamp).toLocaleString() : '--';
                    const machine = escapeHtml(log.machine_id || '--');
                    const user = escapeHtml(log.local_user || '--');
                    const exportType = escapeHtml(log.export_type || '--');
                    const fmt = escapeHtml((log.format || '--').toUpperCase());

                    let encLabel = 'None';
                    let encColor = '#666';
                    if (log.encrypted) {
                        if (log.mode === 'fleet_key') {
                            encLabel = 'Fleet Key';
                            encColor = '#00ff00';
                        } else {
                            encLabel = 'Password';
                            encColor = '#00c8ff';
                        }
                    }

                    html += '<tr style="border-bottom: 1px solid #222;">';
                    html += '<td style="padding: 8px; color: #999; white-space: nowrap;">' + escapeHtml(ts) + '</td>';
                    html += '<td style="padding: 8px; color: #fff;">' + machine + '</td>';
                    html += '<td style="padding: 8px; color: #fff;">' + user + '</td>';
                    html += '<td style="padding: 8px; color: #fff;">' + exportType + '</td>';
                    html += '<td style="padding: 8px; color: #fff;">' + fmt + '</td>';
                    html += '<td style="padding: 8px; color: ' + encColor + ';">' + encLabel + '</td>';
                    html += '</tr>';
                }
                html += '</table>';
                container.innerHTML = html;
            } catch (e) {
                loading.style.display = 'none';
                container.style.display = 'block';
                container.innerHTML = '<div style="text-align: center; color: #ff4444; padding: 20px;">Failed to load export logs</div>';
                console.error('Error loading export logs:', e);
            }
        }

        async function populateExportLogsMachineFilter() {
            try {
                const response = await fetch('/api/fleet/machines', { credentials: 'include' });
                const data = await response.json();
                const machines = data.machines || data || [];
                const select = document.getElementById('exportLogsMachineFilter');
                for (const m of machines) {
                    const opt = document.createElement('option');
                    opt.value = m.machine_id;
                    opt.textContent = (m.info && (m.info.computer_name || m.info.hostname)) || m.machine_id;
                    select.appendChild(opt);
                }
            } catch (e) {
                console.error('Error populating machine filter:', e);
            }
        }

        populateExportLogsMachineFilter();
        loadExportLogs();
    </script>
</body>
</html>'''

    # Return concatenated HTML with injected shared components
    return html_start + base_styles + html_rest + toast_script + html_script
