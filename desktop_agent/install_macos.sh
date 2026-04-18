#!/bin/bash
# macOS LaunchDaemon installer for MDM Agent
# Run with sudo: sudo bash install_macos.sh

set -e

PLIST_PATH="/Library/LaunchDaemons/com.company.mdmagent.plist"
AGENT_PATH="/Library/Application Support/CompanyMDM/mdm_agent"
LABEL="com.company.mdmagent"

echo "Installing Company MDM Agent..."

# Create directory
mkdir -p "/Library/Application Support/CompanyMDM"

# Copy agent binary
cp mdm_agent "$AGENT_PATH"
chmod 755 "$AGENT_PATH"

# Create LaunchDaemon plist (root-level, auto-start)
cat > "$PLIST_PATH" << EOF
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN"
  "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>com.company.mdmagent</string>
    <key>ProgramArguments</key>
    <array>
        <string>/Library/Application Support/CompanyMDM/mdm_agent</string>
    </array>
    <key>RunAtLoad</key>
    <true/>
    <key>KeepAlive</key>
    <true/>
    <key>StandardOutPath</key>
    <string>/var/log/company_mdm.log</string>
    <key>StandardErrorPath</key>
    <string>/var/log/company_mdm_error.log</string>
    <key>UserName</key>
    <string>root</string>
</dict>
</plist>
EOF

# Set permissions — only root can modify
chown root:wheel "$PLIST_PATH"
chmod 644 "$PLIST_PATH"

# Load daemon
launchctl load "$PLIST_PATH"
launchctl start "$LABEL"

echo "MDM Agent installed and running."
echo "To uninstall, IT admin authorization (OTP) is required."
