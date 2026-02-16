# 🎬 CiefpSRTplayer

Advanced external SRT subtitle overlay player for Enigma2.

CiefpSRTplayer is a lightweight and precise SRT subtitle engine designed for Enigma2-based receivers.
It provides manual and automatic subtitle synchronization, FPS conversion, cue-based positioning, and advanced file browsing.

The plugin prioritizes real playback time (PTS) for accurate subtitle sync and 
uses EPG time only as a fallback on live services when playback position is unavailable.

# ✨ Features

- ✅ Accurate sync based on playback time (PTS)
- ✅ EPG time fallback for live TV
- ✅ Manual subtitle offset adjustment (fine sync)
- ✅ FPS conversion (23.976 ↔ 24 ↔ 25)
- ✅ Cue Picker – direct subtitle positioning
- ✅ SRT preview (first cues before loading)
- ✅ Built-in file explorer
- ✅ Delete SRT files directly from browser
- ✅ On-screen status panel (subtitle, timing, encoding, etc.)
- ✅ Adjustable font size and vertical position
- ✅ No auto-load of last subtitle (clean start every time)

# 🎮 Controls
## ⏱ Time Synchronization
- CH+ / CH- → Fine sync forward / backward
- LEFT arrow → Negative offset (subtitle earlier)
- RIGHT arrow → Positive offset (subtitle later)

Offset shifts subtitles linearly without changing speed.

# 🎞 FPS Control
BLUE button → Cycle through FPS modes

## Available modes:
- None (original SRT timing)
- 23.976 → 25
- 25 → 23.976
- 24 → 25
- 25 → 24

FPS conversion changes subtitle playback speed.
Offset only shifts timing.

# 🔤 Subtitle Appearance
- GREEN → Increase font size
- RED → Decrease font size
- UP arrow → Move subtitle up
- DOWN arrow → Move subtitle down

# 📊 Information Panel
- YELLOW → Show status info

## Displays:
- Loaded file name
- Current subtitle index (e.g. 207 / 839)
- Subtitle time (start → end)
- Current playback time
- EPG elapsed time
- Program duration
- Offset value
- FPS mode
- Encoding type
- Font size and vertical position

# 📂 File Explorer
- Preview first subtitle cues
- Pick cue & sync from selected position
- Delete SRT files

Quick positioning based on current playback time

# 🧠 How Sync Works
The plugin reads playback position (PTS) from the Enigma2 service.
Subtitles are rendered according to real playback time.
If playback position is unavailable (some live services), EPG elapsed time is used as fallback.
Manual offset can be applied at any time.
FPS conversion adjusts subtitle timing ratio.

# ⚠️ About EPG Timing
Some TV channels broadcast with delay compared to their published EPG schedule.
This is channel/provider-dependent and not related to the plugin.

CiefpSRTplayer always prioritizes real playback time when available.

# 🧩 Compatibility
- Enigma2-based receivers
- DVB services
- IPTV services
- Local media playback

# 🚀 Version 1.0
- Initial public release:
- Playback-time-based sync engine
- FPS conversion system
- Cue Picker navigation
- Encoding auto-detection
- File explorer with preview
- Clean startup behavior

## ..:: CiefpSettings ::..
