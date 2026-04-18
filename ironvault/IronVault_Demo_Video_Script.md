# IronVault — Demo Video Script (Sales Pitch)

**Total Duration:** 8–10 minutes  
**Format:** Screen recording + phone camera + narration  
**Tools:** OBS Studio, scrcpy (Android mirror), browser for admin panel

---

## VIDEO 1: Device Enrollment + Stealth Mode (2 min)

### Setup
- Admin panel open in browser (left half)
- Android phone with IronVault APK installed (right half, mirrored via scrcpy)

### Script

**[00:00]** Open admin panel — empty device list  
**[00:10]** On phone: open IronVault app → enrollment screen appears  
**[00:25]** Fill: Device Name "LAPTOP-SALES-01", Owner "Rahul Sharma", Department "Sales"  
**[00:40]** Tap **Enroll Device** — loading spinner...  
**[00:55]** Admin panel → device appears in list automatically  
**[01:10]** Show device card: IMEI, hardware fingerprint, status = Active  
**[01:25]** Enable **Stealth Mode** in admin panel → app icon disappears from phone launcher  
**[01:40]** Dial `*#*#1234#*#*` on phone → admin panel appears (PIN prompt)  
**[01:55]** Enter PIN → secret admin dashboard with location, SIM status, tamper log  

---

## VIDEO 2: Real-Time GPS Tracking (2 min)

### Script

**[00:00]** Admin panel → click **Live Map**  
**[00:10]** Device appears as green dot on Leaflet.js map  
**[00:20]** Move phone to another room — dot updates every 15 seconds  
**[00:40]** Click device dot → popup: device name, owner, last seen  
**[00:55]** Click "View Device" → Device Detail with full location history trail  
**[01:15]** Show list of 50+ location points from the past 24 hours  
**[01:30]** Turn off WiFi on phone — device goes offline  
**[01:45]** Turn WiFi back on — all offline-cached locations sync automatically  

---

## VIDEO 3: SIM Swap Detection + Auto-Response (2 min)

### Setup
- Physical device with SIM card
- Admin panel on laptop

### Script

**[00:00]** Show admin panel → SIM Events tab — empty  
**[00:10]** Remove SIM card from phone (slot 1)  
**[00:20]** Within 3 seconds — red alert badge appears on SIM Events  
**[00:30]** Click alert → shows: event type "REMOVED", ICCID, carrier, timestamp  
**[00:45]** Security photo captured automatically by front camera  
**[01:00]** Insert a different SIM — new alert: "INSERTED" with new ICCID  
**[01:15]** Admin sees both alerts in sequence — full audit trail  
**[01:30]** Admin clicks "View on Map" — location at time of SIM swap shown  

---

## VIDEO 4: Remote Commands — Lock, Alarm, Photo (1.5 min)

### Script

**[00:00]** Admin opens Device Detail page  
**[00:10]** Click **Lock Device** → phone locks instantly  
**[00:20]** Click **Trigger Alarm** → phone blasts alarm at max volume  
**[00:35]** Click **Stop Alarm** → silence  
**[00:45]** Click **Front Camera** → 3 second wait → security photo appears in admin panel  
**[01:00]** Photo shows person holding phone — captured silently with no notification  
**[01:15]** Click **SIM Dump** → ICCID, carrier, roaming status returned in 5 seconds  

---

## VIDEO 5: Brick Mode — Stolen Device Response (1.5 min)

### Script

**[00:00]** Admin panel → device list → mark device as "Stolen"  
**[00:10]** Confirm dialog: "This will activate brick mode — are you sure?"  
**[00:15]** Click confirm  
**[00:20]** Phone screen: full-screen red overlay appears immediately  
**[00:30]** Text: "⛔ STOLEN DEVICE — RETURN FOR REWARD"  
**[00:40]** Back button doesn't work — screen cannot be dismissed  
**[00:50]** Phone continues to broadcast location to backend every 2 minutes  
**[01:00]** Admin panel shows real-time beacon updates from bricked device  
**[01:15]** Service center generates unlock token → admin sends UNBRICK command → device unbricked  

---

## VIDEO 6: Hardware Anti-Resale Detection (1 min)

### Script

**[00:00]** Admin panel → Tools → Hardware Registry → click "Run Scan"  
**[00:10]** Report shows: "0 duplicate IMEIs, 0 duplicate fingerprints" — all clean  
**[00:20]** Simulate: register same IMEI with different hardware fingerprint  
**[00:35]** Scan again → "IMEI 490154... seen with 2 different hardware fingerprints"  
**[00:45]** This means: device was opened and motherboard/IMEI was changed — flagged  
**[00:55]** Admin can remotely brick the suspect device immediately  

---

## Key Talking Points for Sales

### For Company Owners / HR Managers
> "If an employee loses a device or leaves with it, you can remotely wipe it, lock it, or track it in real time. No cooperation from the employee needed."

### For IT Administrators
> "Full Device Owner enrollment means we block factory reset, uninstall attempts, and airplane mode. The app survives everything except a hardware flash."

### For Security Teams
> "Every event is logged with timestamp, admin ID, and device ID. ICCID history, hardware fingerprints, and location history are all queryable. Full audit trail."

### For Fleet Managers
> "Zero-touch enrollment via Android Enterprise. Devices are automatically enrolled the moment they boot. No manual setup required."

---

## Recording Tips
- Use 1920×1080, 30fps minimum
- Zoom in on phone screen during commands (OBS zoom filter)
- Add text overlay: feature name at bottom-left of screen
- Narrate in English (add Hindi subtitles for Indian market)
- Background music: subtle corporate track, 5% volume
- Export: MP4, H.264, 8 Mbps bitrate
