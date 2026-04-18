# Demo Video Recording Guide

## Tools Needed
- OBS Studio (screen recording)
- Android emulator (Android Studio) or physical device
- Chrome browser for admin dashboard

---

## Demo Script (10-12 minutes)

### Scene 1: System Overview (1 min)
- Show ARCHITECTURE.md diagram
- Narrate: "This is a complete enterprise MDM system..."

### Scene 2: Admin Dashboard Login (1 min)
- Open admin dashboard in browser
- Login with admin credentials
- Show device list with online/offline status indicators

### Scene 3: Device Enrollment (2 min)
- Show Flutter app on Android emulator
- Fill enrollment form (name, email, dept)
- Submit → device appears in admin dashboard instantly
- Show device status: "Uninstall Protection Active"

### Scene 4: Real-time Monitoring (2 min)
- Show heartbeat (device stays "online")
- Admin dashboard auto-refreshes
- Show location on map
- Show app usage chart (YouTube = red, Chrome = blue)

### Scene 5: Remote Lock (1 min)
- Admin clicks "Lock Device"
- No OTP needed
- Device screen locks immediately
- Show audit log entry created

### Scene 6: Uninstall Attempt Without Authorization (1 min)
- On Android: go to Settings → Apps → Company Agent
- Try to uninstall → "This app is protected by device admin"
- Cannot uninstall without IT admin authorization
- Audit log shows "uninstall_blocked"

### Scene 7: Authorized Remote Uninstall (2 min)
- Admin clicks "Remote Uninstall" → OTP modal appears
- Show 6-digit OTP with countdown timer
- "Admin reads OTP to employee over phone"
- Employee enters OTP in app → OTP dialog shown
- OTP verified → uninstall proceeds
- Audit log: otp_generated → otp_verified → uninstall_authorized

### Scene 8: Audit Logs (1 min)
- Show Audit Logs page
- Demonstrate complete audit trail
- Show timestamps, admin IDs, device IDs, IP addresses

---

## Recording Tips
- Use 1080p, 30fps
- Zoom into important UI elements
- Add text overlays for each feature
- Record in segments, edit together
- Add company branding intro/outro
