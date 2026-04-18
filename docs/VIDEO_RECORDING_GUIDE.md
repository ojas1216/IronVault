# Video Recording Guide — Demo Videos

## Tools
- **OBS Studio** (free) — screen recording
- **Android Studio** emulator + scrcpy (mirror physical device)
- **Postman** (optional) — show API calls live

---

## Video 1: Device Enrollment + Uninstall Protection (3–4 min)

### Setup
- Open admin dashboard in browser (left half of screen)
- Open Flutter app on Android emulator or phone (right half)

### Script
1. **[00:00]** Show admin dashboard — empty device list
2. **[00:20]** Open MDM app on device — enrollment screen appears
3. **[00:40]** Fill form: employee name, email, department → click "Enroll Device"
4. **[01:00]** Switch to dashboard — device appears in real-time (30s heartbeat)
5. **[01:30]** On device: try to uninstall via Settings → Apps → Company Agent
   - **Expected:** Android shows "This app is protected by device admin"
   - Cannot uninstall without authorization
6. **[02:00]** Show "Uninstall Protection Active" badge on device card
7. **[02:30]** Open audit logs — show `device_enrolled` and `uninstall_blocked` events
8. **[03:00]** Show timestamps, admin IDs, device IDs in log

---

## Video 2: Admin One-Click Silent Uninstall (2 min)

### Script
1. **[00:00]** Admin opens Device Detail page
2. **[00:10]** Click "Remote Uninstall" button
3. **[00:15]** No OTP modal — goes straight to confirmation
4. **[00:20]** Admin clicks confirm
5. **[00:25]** FCM push shown in terminal logs
6. **[00:35]** Device screen: app closes and uninstalls silently (no employee interaction)
7. **[01:00]** Dashboard: device status changes to "Decommissioned"
8. **[01:10]** Audit log: `otp_generated` → `otp_verified` → `uninstall_authorized` — all by server
9. **[01:30]** Show timestamp, admin ID, device ID in audit record

---

## Video 3: SIM Swap Detection + Auto-Response (3 min)

### Setup
- Physical Android device with dual SIM
- Admin dashboard open on laptop

### Script
1. **[00:00]** Show device enrolled, SIM Alerts page empty
2. **[00:15]** Remove SIM card from device (or use emulator SIM change API)
3. **[00:30]** Within 5 seconds — SIM Alerts page shows new alert (red badge)
4. **[00:45]** Click alert — shows: event type, ICCID, carrier, timestamp
5. **[01:00]** Show security photo attached (front camera auto-captured)
6. **[01:15]** Show location captured at moment of SIM change
7. **[01:30]** Admin clicks "View Device" — opens device detail with current location
8. **[02:00]** Admin marks incident "Resolved" with notes
9. **[02:30]** Show full audit trail

---

## Video 4: UWB Precision Tracking (2 min)

### Setup
- Two devices with UWB support (or BLE fallback demo)
- Admin dashboard showing radar

### Script
1. **[00:00]** Show UWB Tracker panel on device detail page (empty/no signal)
2. **[00:15]** Start UWB ranging on target device
3. **[00:30]** Radar shows device blip with distance and direction
4. **[00:45]** Slowly move device away — distance increases in real-time
5. **[01:00]** Move device to left — azimuth arrow updates to "Turn left"
6. **[01:15]** Move very close — distance shows centimeters, "Right here!" message
7. **[01:30]** Demonstrate BLE fallback on non-UWB device — note lower accuracy
8. **[01:50]** Show ranging history in admin dashboard

---

## Video 5: IMEI + Device Identity (1 min)

1. Open Device Detail → scroll to "Device Identity" panel
2. Show IMEI (masked by default) → click "Show" to reveal
3. Show Serial Number, Android ID, Hardware Fingerprint
4. Explain: "This information is collected with company policy and employee consent"
5. Show backend API returning identity payload

---

## Video 6: Factory Reset Protection (2 min)

1. Show enrolled device with FRP enabled
2. Go to Settings → General Management → Reset → Factory Reset
3. **Expected:** Shows "Reset disabled by IT policy" OR after reset, requires company Google account
4. Show log: `tamper_detected` event with IP and timestamp
5. Admin receives notification in dashboard

---

## Recording Tips
- Use 1920×1080, 30fps minimum
- Add lower-third text overlays for each feature name
- Use zoom-in on important UI moments
- Narrate in English or Hindi (add subtitles)
- Ideal total demo: 12–15 minutes across all videos
- Export as MP4 H.264 for submission
