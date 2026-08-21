# -*- coding: utf-8 -*-
# CiefpSRTplayer v1.0 (OpenATV 7.6 / Python3)
from __future__ import absolute_import, print_function
from Plugins.Plugin import PluginDescriptor
from Screens.Screen import Screen
from Screens.MessageBox import MessageBox
from Screens.LocationBox import LocationBox
from Screens.ChoiceBox import ChoiceBox
from Components.MenuList import MenuList
from Components.ScrollLabel import ScrollLabel
from Components.ActionMap import ActionMap
from Components.Label import Label
from Components.FileList import FileList
from Components.ConfigList import ConfigListScreen
from Components.ActionMap import HelpableActionMap
from Components.config import (
    config, ConfigSubsection, ConfigInteger, ConfigSelection, ConfigText, getConfigListEntry
)
from enigma import gRGB
from enigma import ePoint
from enigma import eTimer, gFont

from time import time
import keymapparser
import codecs
import re
import os

PLUGIN_NAME = "CiefpSRTplayer"
PLUGIN_VERSION = "1.1"


# ---------------- Config ----------------
config.plugins.ciefpsrt = ConfigSubsection()
config.plugins.ciefpsrt.default_dir = ConfigText(default="/media/hdd/subtitles/", fixed_size=False)
config.plugins.ciefpsrt.srt_path     = ConfigText(default="", fixed_size=False)

config.plugins.ciefpsrt.offset_ms = ConfigInteger(default=0, limits=(-600000, 600000))  # +/- 10 min
config.plugins.ciefpsrt.y_pos     = ConfigInteger(default=850, limits=(0, 1080))

config.plugins.ciefpsrt.font_size = ConfigInteger(default=44, limits=(24, 90))

config.plugins.ciefpsrt.color = ConfigSelection(default="yellow", choices=[
    ("yellow", "Yellow"),
    ("white",  "White"),
    ("cyan",   "Cyan"),
    ("purple", "Purple"),
    ("orange", "Orange"),
    ("green",  "Green"),
    ("blue",   "Blue"),
    ("red",    "Red"),
])

config.plugins.ciefpsrt.bg_mode = ConfigSelection(default="none", choices=[
    ("none", "No background"),
    ("black", "Black background"),
])

config.plugins.ciefpsrt.encoding = ConfigSelection(default="cee", choices=[
    ("auto", "AUTO (try multiple)"),
    ("cee", "Central and Eastern Europe"),
    ("we",  "Western Europe"),
    ("ru",  "Russia"),
    ("ar",  "Arabic"),
    ("tr",  "Turkish"),
    ("gr",  "Greek"),
    ("he",  "Hebrew"),
    ("utf8", "UTF-8 only"),
    ("utf16", "UTF-16 only"),
])

config.plugins.ciefpsrt.scale_mode = ConfigSelection(default="none", choices=[
    ("none", "No FPS scale"),
    ("23976_to_25", "23.976 -> 25"),
    ("25_to_23976", "25 -> 23.976"),
    ("24_to_25", "24 -> 25"),
    ("25_to_24", "25 -> 24"),
])

# Quick presets
config.plugins.ciefpsrt.quick_preset = ConfigSelection(default="none", choices=[
    ("none", "OFF - Manual settings"),
    ("live_tv_dvb", "Live TV (DVB) - normal"),
    ("live_tv_film", "Live TV Film (24->25)"),
    ("iptv_1080p", "IPTV 1080p (as is)"),
    ("iptv_720p_film", "IPTV 720p Film (23.976->25)"),
    ("webdl_23976", "WEB-DL 23.976 (23.976->25)"),
    ("custom_1", "Custom preset 1"),
    ("custom_2", "Custom preset 2"),
])
# ---------------- Quick Presets ----------------
QUICK_PRESETS = {
    "none": {
        "name": "OFF - Manual settings",
        "fps": "none",
        "offset": 0,
        "color": None,  # None znači ne menjati
        "bg_mode": None,
        "font_size": None,
        "y_pos": None,
        "encoding": None,
    },
    "live_tv_dvb": {
        "name": "Live TV (DVB) - normal",
        "fps": "none",
        "offset": 0,
        "color": "yellow",
        "bg_mode": "black",
        "font_size": 44,
        "y_pos": 850,
        "encoding": "cee",
    },
    "live_tv_film": {
        "name": "Live TV Film (24->25)",
        "fps": "24_to_25",
        "offset": 0,
        "color": "yellow",
        "bg_mode": "black",
        "font_size": 44,
        "y_pos": 850,
        "encoding": "cee",
    },
    "iptv_1080p": {
        "name": "IPTV 1080p (as is)",
        "fps": "none",
        "offset": 0,
        "color": "green",
        "bg_mode": "none",
        "font_size": 50,
        "y_pos": 920,
        "encoding": "auto",
    },
    "iptv_720p_film": {
        "name": "IPTV 720p Film (23.976->25)",
        "fps": "23976_to_25",
        "offset": 0,
        "color": "green",
        "bg_mode": "none",
        "font_size": 48,
        "y_pos": 900,
        "encoding": "auto",
    },
    "webdl_23976": {
        "name": "WEB-DL 23.976 (23.976->25)",
        "fps": "23976_to_25",
        "offset": 0,
        "color": "white",
        "bg_mode": "black",
        "font_size": 46,
        "y_pos": 880,
        "encoding": "utf8",
    },
    "custom_1": {
        "name": "Custom preset 1",
        "fps": "none",
        "offset": 0,
        "color": "yellow",
        "bg_mode": "black",
        "font_size": 44,
        "y_pos": 850,
        "encoding": "cee",
    },
    "custom_2": {
        "name": "Custom preset 2",
        "fps": "none",
        "offset": 0,
        "color": "yellow",
        "bg_mode": "black",
        "font_size": 44,
        "y_pos": 850,
        "encoding": "cee",
    },
}


def _ensure_dir_slash(p):
    if not p:
        return p
    return p if p.endswith("/") else (p + "/")

# ---------------- SRT parsing ----------------
def parse_srt_time(t):
    hh, mm, rest = t.split(":")
    ss, ms = rest.split(",")
    return (int(hh) * 3600 + int(mm) * 60 + int(ss)) * 1000 + int(ms)


# ---------------- Encoding groups (like SubsSupport) ----------------
ALL_LANGUAGES_ENCODINGS = ["utf-8", "utf-16"]

CENTRAL_EASTERN_EUROPE_ENCODINGS = ["utf-8", "windows-1250", "iso-8859-2", "maclatin2", "IBM852"]
WESTERN_EUROPE_ENCODINGS = ["windows-1252", "iso-8859-15", "macroman", "ibm1140", "IBM850"]
RUSSIAN_ENCODINGS = ["windows-1251", "cyrillic", "maccyrillic", "koi8_r", "IBM866"]
ARABIC_ENCODINGS = ["windows-1256", "iso-8859-6", "IBM864"]
TURKISH_ENCODINGS = ["windows-1254", "iso-8859-9", "latin5", "macturkish", "ibm1026", "IBM857"]
GREEK_ENCODINGS = ["windows-1253", "iso-8859-7", "macgreek"]
HEBREW_ENCODINGS = ["windows-1255", "iso-8859-8", "IBM862"]

ENCODING_GROUPS = {
    "cee": CENTRAL_EASTERN_EUROPE_ENCODINGS,
    "we":  WESTERN_EUROPE_ENCODINGS,
    "ru":  RUSSIAN_ENCODINGS,
    "ar":  ARABIC_ENCODINGS,
    "tr":  TURKISH_ENCODINGS,
    "gr":  GREEK_ENCODINGS,
    "he":  HEBREW_ENCODINGS,
    "utf8": ["utf-8"],
    "utf16": ["utf-16"],
    # auto: try common encodings first
    "auto": ALL_LANGUAGES_ENCODINGS + CENTRAL_EASTERN_EUROPE_ENCODINGS + RUSSIAN_ENCODINGS + ARABIC_ENCODINGS,
}

ENC_LABEL = {
    "auto": "AUTO",
    "cee": "Central/Eastern",
    "we": "Western",
    "ru": "Russia",
    "ar": "Arabic",
    "tr": "Turkish",
    "gr": "Greek",
    "he": "Hebrew",
    "utf8": "UTF-8",
    "utf16": "UTF-16",
}

def load_srt(path, encoding_key):
    with open(path, "rb") as f:
        raw = f.read()

    enc_list = ENCODING_GROUPS.get(encoding_key, ["utf-8"])

    data = None
    for enc in enc_list:
        try:
            # UTF-16 probaj samo ako fajl ima BOM
            if enc in ("utf-16", "utf-16-le", "utf-16-be"):
                if not (raw.startswith(codecs.BOM_UTF16_LE) or raw.startswith(codecs.BOM_UTF16_BE)):
                    continue

            data = raw.decode(enc, errors="strict")
            break
        except Exception:
            data = None

    if data is None:
        data = raw.decode("utf-8", errors="replace")

    blocks = re.split(r"\n\s*\n", data.strip(), flags=re.MULTILINE)
    cues = []
    for b in blocks:
        lines = [x.strip("\r") for x in b.splitlines() if x.strip() != ""]
        if len(lines) < 2:
            continue
        time_line = lines[1] if ("-->" in lines[1]) else lines[0]
        m = re.match(r"(\d\d:\d\d:\d\d,\d\d\d)\s*-->\s*(\d\d:\d\d:\d\d,\d\d\d)", time_line)
        if not m:
            continue
        start = parse_srt_time(m.group(1))
        end = parse_srt_time(m.group(2))
        text_start_idx = 2 if ("-->" in lines[1]) else 1
        text = "\n".join(lines[text_start_idx:]).strip()
        cues.append([start, end, text])
    return cues

def scale_cues(cues, mode):
    if mode == "none":
        return cues
    if mode == "23976_to_25":
        scale = 23.976 / 25.0
    elif mode == "25_to_23976":
        scale = 25.0 / 23.976
    elif mode == "24_to_25":
        scale = 24.0 / 25.0
    elif mode == "25_to_24":
        scale = 25.0 / 24.0
    else:
        scale = 1.0
    out = []
    for s, e, t in cues:
        out.append([int(s * scale), int(e * scale), t])
    return out

# ---------------- Helpers: playback position ----------------
def get_real_now_ms(session):
    """
    Unified 'current time' resolver.

    Priority:
      1) playback/PTS (seek.getPlayPosition) if available
      2) EPG elapsed fallback (only when playback is unavailable)
    """

    # 1) playback first
    play = None
    try:
        play = get_playback_ms(session)  # returns ms or None
        if play is not None:
            return int(play)
    except Exception:
        play = None

    # 2) EPG elapsed fallback
    epg_ms = None
    try:
        service = session.nav.getCurrentService()
        if service:
            info = service.info()
            if info:
                ev = info.getEvent(0)
                if ev:
                    begin = ev.getBeginTime()
                    if begin:
                        now_s = int(time())
                        elapsed_s = now_s - int(begin)
                        if elapsed_s < 0:
                            elapsed_s = 0
                        epg_ms = elapsed_s * 1000
    except Exception:
        epg_ms = None

    if epg_ms is not None:
        return int(epg_ms)

    return None

def get_playback_ms(session):
    try:
        service = session.nav.getCurrentService()
        if not service:
            return None
        seek = service.seek()
        if not seek:
            return None
        r = seek.getPlayPosition()
        pos = None
        if isinstance(r, tuple) and len(r) >= 2:
            err, pos = r[0], r[1]
            if err != 0:
                return None
        elif isinstance(r, int):
            pos = r
        else:
            return None
        if pos is None or pos < 0:
            return None
        if pos > 1000000:  # likely 90kHz ticks
            return int(pos / 90)
        return int(pos)
    except Exception:
        return None

# ---------------- Screens ----------------
class SRTFileBrowser(Screen):
    skin = """
    <screen name="SRTFileBrowser" position="center,center" size="1200,700" title="Select SRT">
        <widget name="filelist" position="20,20" size="1160,620" />
        <widget name="hint" position="20,650" size="1160,40" font="Regular;26" foregroundColor="#30fc03" halign="left" transparent="1" />
    </screen>
    """

    def __init__(self, session, start_dir, on_selected):
        Screen.__init__(self, session)
        self.on_selected = on_selected
        self["hint"] = Label("OK: open/select   YELLOW/MENU: actions   EXIT: cancel")
        start_dir = start_dir or "/"
        if not os.path.isdir(start_dir):
            start_dir = "/"
        self["filelist"] = FileList(start_dir, matchingPattern=r"^.*\.(srt|SRT)$", showDirectories=True)
        self["actions"] = ActionMap(
            ["OkCancelActions", "DirectionActions", "MenuActions", "ColorActions", "InfoActions"],
            {
                "ok": self.ok,
                "cancel": self.close,

                # Actions menu (više tastera da radi na svim daljincima/image-ovima)
                "menu": self.menuActions,
                "yellow": self.menuActions,
                "info": self.menuActions,
            },
            1  # <-- VAŽNO: viši prioritet da FileList ne “pojede” taster
        )

    def menuActions(self):
        print("[CiefpSRT] menuActions pressed")
        sel = self["filelist"].getSelection()
        if not sel:
            return
        path = sel[0]
        isDir = sel[1] if len(sel) > 1 else False
        if isDir:
            return  # za folder ne nudimo akcije

        choices = [
            ("Preview (first cues)", "preview"),
            ("Pick cue & Sync from here", "cuepick"),
            ("Delete file", "delete"),
        ]
        self.session.openWithCallback(lambda c: self._menu_cb(c, path), ChoiceBox,
                                      title="SRT actions", list=choices)

    def _menu_cb(self, choice, path):
        if not choice:
            return
        key = choice[1]
        if key == "preview":
            self.session.open(SRTPreviewScreen, path)
        elif key == "delete":
            self._deleteFile(path)
        elif key == "cuepick":
            # otvori cue picker; callback vrati cue_start_ms
            self.session.openWithCallback(lambda cue_ms: self._cuePicked(path, cue_ms),
                                          CuePickerScreen, self.session, path)

    def _deleteFile(self, path):
        def _confirm(ans):
            if not ans:
                return
            try:
                os.remove(path)
                self["filelist"].refresh()
            except Exception as e:
                self.session.open(MessageBox, "Delete failed:\n%s" % str(e), MessageBox.TYPE_ERROR, timeout=6)

        self.session.openWithCallback(_confirm, MessageBox,
                                      "Delete this file?\n\n%s" % os.path.basename(path),
                                      MessageBox.TYPE_YESNO)

    def _cuePicked(self, path, cue_ms):
        if cue_ms is None:
            return
        # prosledi nazad browser callback-u (overlay će primeniti sync)
        # ideja: vrati tuple (path, cue_ms)
        try:
            self.on_selected((path, int(cue_ms)))
        except Exception:
            # fallback: samo path
            self.on_selected(path)
        self.close()

    def ok(self):
        sel = self["filelist"].getSelection()
        if not sel:
            return

        # FileList može da vrati tuple sa više elemenata:
        # npr. (path, isDir) ili (path, isDir, name) itd.
        path = sel[0]
        isDir = sel[1] if len(sel) > 1 else False

        if isDir:
            self["filelist"].changeDir(path)
        else:
            self.on_selected(path)
            self.close()

class SRTPreviewScreen(Screen):
    skin = """
    <screen name="SRTPreviewScreen" position="center,center" size="1920,1080" title="SRT Preview">
        <widget name="text" position="40,40" size="1840,920" font="Regular;28" />
        <widget name="hint" position="40,1000" size="1840,60" font="Regular;28" foregroundColor="#30fc03" transparent="1" />
    </screen>
    """

    def __init__(self, session, path):
        Screen.__init__(self, session)
        self.path = path
        self["text"] = ScrollLabel("")
        self["hint"] = Label("OK/EXIT: close")
        self["actions"] = ActionMap(["OkCancelActions"], {
            "ok": self.close,
            "cancel": self.close,
        }, -1)
        self.onLayoutFinish.append(self._load)

    def _load(self):
        try:
            # koristi trenutno izabranu grupu enkodovanja iz settings-a
            cues = load_srt(self.path, config.plugins.ciefpsrt.encoding.value)
            # pokaži prvih 10 cue-ova
            out = []
            for i, (s, e, t) in enumerate(cues[:10]):
                out.append("%d)\n%s --> %s\n%s\n" % (i + 1, self._ms(s), self._ms(e), t))
            if not out:
                out = ["(No cues parsed)"]
            self["text"].setText("\n".join(out))
        except Exception as e:
            self["text"].setText("Preview failed:\n%s" % str(e))

    def _ms(self, ms):
        ms = int(ms)
        hh = ms // 3600000
        mm = (ms % 3600000) // 60000
        ss = (ms % 60000) // 1000
        mss = ms % 1000
        return "%02d:%02d:%02d,%03d" % (hh, mm, ss, mss)

class CuePickerScreen(Screen):
    skin = """
    <screen name="CuePickerScreen" position="center,center" size="1920,1080" title="Pick subtitle position">
        <widget name="list" position="40,40" size="1840,920" font="Regular;28" itemHeight="34" halign="left" valign="center" scrollbarMode="showOnDemand" />
        <widget name="hint" position="40,1000" size="1840,60" font="Regular;28" halign="left" valign="center" foregroundColor="#30fc03" transparent="1" />
    </screen>
    """

    def __init__(self, session, overlay_session, path):
        Screen.__init__(self, session)
        self.overlay_session = overlay_session
        self.path = path
        self.cues = []
        self.list_data = []  # [(display, idx), ...]

        self["hint"] = Label("OK: select cue | BLUE: jump to current | EXIT: cancel")
        self["list"] = MenuList([])

        self["actions"] = ActionMap(
            ["OkCancelActions", "ColorActions", "DirectionActions"],
            {
                "ok": self._ok,
                "cancel": self._cancel,
                "blue": self._jumpToCurrent,
                "up": self._up,
                "down": self._down,
                "left": self._pageUp,
                "right": self._pageDown,
                "pageUp": self._pageUp,
                "pageDown": self._pageDown,
            },
            -1
        )

        self.onLayoutFinish.append(self._load)

    def _pageStep(self):
        """
        Pokušava da izračuna koliko stavki staje na ekran (jedna strana).
        Ako ne može (različiti image-ovi), koristi fallback.
        """
        try:
            lb = self["list"].l  # eListboxPythonStringContent / listbox
            item_h = lb.getItemHeight()
            if item_h <= 0:
                raise Exception("bad item height")

            # visina widget-a
            h = self["list"].instance.size().height()
            step = max(5, int(h / item_h) - 1)  # -1 da ne “preskoči” previše
            return step
        except Exception:
            return 20  # fallback: jedna strana ~20 linija

    def _load(self):
        try:
            cues = load_srt(self.path, config.plugins.ciefpsrt.encoding.value)
            cues = scale_cues(cues, config.plugins.ciefpsrt.scale_mode.value)
            self.cues = cues

            lst = []
            total = len(cues)
            for i, (s, e, t) in enumerate(cues):
                first = (t.split("\n")[0] if t else "").strip()
                if len(first) > 60:
                    first = first[:60] + "…"
                disp = "%d/%d  %s → %s  %s" % (i + 1, total, self._ms(s), self._ms(e), first)
                lst.append((disp, i))

            self.list_data = lst
            self["list"].setList([x[0] for x in lst])  # MenuList prikazuje samo string
            self._autoSelectCurrent()
        except Exception as e:
            self.session.open(MessageBox, "Cue load failed:\n%s" % str(e), MessageBox.TYPE_ERROR, timeout=6)
            self.close(None)

    def _autoSelectCurrent(self):
        """
        Postavi selektor na cue najbliži trenutnom vremenu (playback/EPG).
        Koristi now_ms iz overlay-a, plus trenutno podešen offset.
        """
        try:
            now_ms = None

            # 1) pokušaj iz overlay-a ako je stvarno CiefpOverlay
            if self.overlay_session is not None:
                try:
                    now_ms = self.overlay_session._get_now_ms()
                except Exception:
                    now_ms = None

            # 2) fallback preko session playback/EPG
            if now_ms is None:
                now_ms = self._get_now_ms()

            if now_ms is None or not self.cues:
                return
            # trenutna "subtitle timeline" tačka = now + offset
            t_ms = int(now_ms) + int(config.plugins.ciefpsrt.offset_ms.value)

            # nađi najbliži cue (brzo – linearno je ok za 1-2k cue-ova)
            best = 0
            for i, (s, e, _) in enumerate(self.cues):
                if s <= t_ms <= e:
                    best = i
                    break
                if t_ms < s:
                    best = max(0, i - 1)
                    break
                best = i

            self["list"].moveToIndex(best)
        except Exception:
            pass

    def _getSelectedIndex(self):
        try:
            pos = self["list"].getSelectionIndex()
            if pos is None:
                return None
            if pos < 0 or pos >= len(self.list_data):
                return None
            return self.list_data[pos][1]
        except Exception:
            return None

    def _get_now_ms(self):
        return get_real_now_ms(self.session)

    def _ok(self):
        idx = self._getSelectedIndex()
        if idx is None:
            self.close(None)
            return
        try:
            cue_start = int(self.cues[idx][0])
        except Exception:
            cue_start = None
        self.close(cue_start)

    def _cancel(self):
        self.close(None)

    def _jumpToCurrent(self):
        try:
            now_ms = None

            if self.overlay_session is not None:
                try:
                    now_ms = self.overlay_session._get_now_ms()
                except Exception:
                    now_ms = None

            if now_ms is None:
                now_ms = self._get_now_ms()

            if now_ms is None or not self.cues:
                return

            t_ms = int(now_ms) + int(config.plugins.ciefpsrt.offset_ms.value)

            idx = 0
            for i, (s, e, _) in enumerate(self.cues):
                if s <= t_ms <= e:
                    idx = i
                    break
                if t_ms < s:
                    idx = max(0, i - 1)
                    break
                idx = i

            self["list"].moveToIndex(idx)
        except Exception:
            pass

    # navigacija
    def _up(self):
        try:
            self["list"].up()
        except Exception:
            pass

    def _down(self):
        try:
            self["list"].down()
        except Exception:
            pass

    def _pageUp(self):
        try:
            step = self._pageStep()
            for _ in range(step):
                self["list"].up()
        except Exception:
            pass

    def _pageDown(self):
        try:
            step = self._pageStep()
            for _ in range(step):
                self["list"].down()
        except Exception:
            pass

    def _ms(self, ms):
        ms = int(ms)
        hh = ms // 3600000
        mm = (ms % 3600000) // 60000
        ss = (ms % 60000) // 1000
        mss = ms % 1000
        return "%02d:%02d:%02d,%03d" % (hh, mm, ss, mss)

class CiefpSettings(Screen, ConfigListScreen):
    skin = """
    <screen name="CiefpSettings" position="center,center" size="1200,760" title="CiefpSRTplayer Settings">
        <widget name="config" position="30,20" size="1140,640" itemHeight="33" font="Regular;28" scrollbarMode="showOnDemand" />
        <widget name="hint" position="30,680" size="1140,60" font="Regular;26" foregroundColor="#30fc03" transparent="1" />
    </screen>
    """

    def __init__(self, session, on_apply=None):
        Screen.__init__(self, session)
        self.on_apply = on_apply
        self["hint"] = Label("GREEN: Save   RED: Cancel   OK: Change   MENU: Select folder / file")
        cfg = []
        cfg.append(getConfigListEntry("Subtitles folder (default)", config.plugins.ciefpsrt.default_dir))
        cfg.append(getConfigListEntry("Selected .srt file", config.plugins.ciefpsrt.srt_path))
        cfg.append(getConfigListEntry("QUICK PRESETS", config.plugins.ciefpsrt.quick_preset))
        cfg.append(getConfigListEntry("Encoding group", config.plugins.ciefpsrt.encoding))
        cfg.append(getConfigListEntry("Text color", config.plugins.ciefpsrt.color))
        cfg.append(getConfigListEntry("Background", config.plugins.ciefpsrt.bg_mode))
        cfg.append(getConfigListEntry("Font size", config.plugins.ciefpsrt.font_size))
        cfg.append(getConfigListEntry("Vertical position (Y)", config.plugins.ciefpsrt.y_pos))
        cfg.append(getConfigListEntry("Time offset (ms)", config.plugins.ciefpsrt.offset_ms))
        cfg.append(getConfigListEntry("FPS scale preset", config.plugins.ciefpsrt.scale_mode))
        ConfigListScreen.__init__(self, cfg, session=session)
        self["actions"] = ActionMap(["OkCancelActions", "ColorActions", "MenuActions"], {
            "green": self.save,
            "red": self.cancel,
            "cancel": self.cancel,
            "menu": self.menu,
        }, -1)

    def menu(self):
        choices = [
            ("Pick subtitles folder", "pick_folder"),
            ("Browse and select .srt", "pick_srt"),
        ]
        self.session.openWithCallback(self._menu_cb, ChoiceBox, title="Settings actions", list=choices)

    def _menu_cb(self, choice):
        if not choice:
            return
        key = choice[1]
        if key == "pick_folder":
            curr = config.plugins.ciefpsrt.default_dir.value or "/"
            self.session.openWithCallback(self._folder_cb, LocationBox, text="Select subtitles folder", currDir=curr)
        elif key == "pick_srt":
            start_dir = config.plugins.ciefpsrt.default_dir.value or "/"
            self.session.open(SRTFileBrowser, start_dir, self._srt_cb)

    def _folder_cb(self, newdir):
        if newdir:
            config.plugins.ciefpsrt.default_dir.value = _ensure_dir_slash(newdir)

    def _srt_cb(self, path):
        if path:
            config.plugins.ciefpsrt.srt_path.value = path

    def save(self):
        config.plugins.ciefpsrt.default_dir.value = _ensure_dir_slash(config.plugins.ciefpsrt.default_dir.value)
        for x in (
            config.plugins.ciefpsrt.default_dir,
            # config.plugins.ciefpsrt.srt_path,
            config.plugins.ciefpsrt.encoding,
            config.plugins.ciefpsrt.color,
            config.plugins.ciefpsrt.bg_mode,
            config.plugins.ciefpsrt.font_size,
            config.plugins.ciefpsrt.y_pos,
            config.plugins.ciefpsrt.offset_ms,
            config.plugins.ciefpsrt.scale_mode,
        ):
            try:
                x.save()
            except Exception:
                pass
        if callable(self.on_apply):
            self.on_apply()
        self.close()

    def keyOK(self):
        # Ovo je već postojeća metoda, ali treba da dodamo proveru za presets
        current = self["config"].getCurrent()
        if current and current[1] == config.plugins.ciefpsrt.quick_preset:
            # Ako je selektovan quick_preset, pitaj da li želi da primeni
            self.session.openWithCallback(
                self._applyPreset,
                MessageBox,
                "Apply this preset? This will change FPS, offset, color and position settings.",
                MessageBox.TYPE_YESNO
            )
        else:
            # Normalno ponašanje
            ConfigListScreen.keyOK(self)

    def _applyPreset(self, answer):
        if answer:
            preset_key = config.plugins.ciefpsrt.quick_preset.value
            preset = QUICK_PRESETS.get(preset_key)
            if preset:
                # Sačuvaj trenutne vrednosti pre primene
                if preset["fps"] is not None:
                    config.plugins.ciefpsrt.scale_mode.value = preset["fps"]
                if preset["offset"] is not None:
                    config.plugins.ciefpsrt.offset_ms.value = preset["offset"]
                if preset["color"] is not None:
                    config.plugins.ciefpsrt.color.value = preset["color"]
                if preset["bg_mode"] is not None:
                    config.plugins.ciefpsrt.bg_mode.value = preset["bg_mode"]
                if preset["font_size"] is not None:
                    config.plugins.ciefpsrt.font_size.value = preset["font_size"]
                if preset["y_pos"] is not None:
                    config.plugins.ciefpsrt.y_pos.value = preset["y_pos"]
                if preset["encoding"] is not None:
                    config.plugins.ciefpsrt.encoding.value = preset["encoding"]

                # Osveži prikaz
                self["config"].invalidate()

                self.session.open(MessageBox,
                                  f"Preset '{preset['name']}' applied!\nYou can still adjust individual settings.",
                                  MessageBox.TYPE_INFO, timeout=3)

        # Vrati se na normalan edit mod
        ConfigListScreen.keyOK(self)

    def cancel(self):
        self.close()

class CiefpOverlay(Screen):
    skin = """
    <screen name="CiefpOverlay" position="0,0" size="1920,1080"
        zPosition="2" backgroundColor="transparent" flags="wfNoBorder">
    <!-- pozadina samo iza titla -->
    <widget name="sub_bg" position="80,850" size="1760,170"
        backgroundColor="#000000" transparent="0" zPosition="1" />
    <!-- tekst titla -->
    <widget name="subtitle" position="80,850" size="1760,170"
            font="Regular;44" halign="center" valign="center"
            foregroundColor="#00FFFF00" backgroundColor="#00000000"
            transparent="1" shadowColor="#40101010" shadowOffset="2,2" zPosition="2" />
    <!-- status gore (2 reda, odvojeno da se ne sece) -->
    <widget name="status1" position="60,10" size="1800,34"
        font="Regular;28" halign="left" valign="top"
        transparent="1" foregroundColor="#00FFFF00" zPosition="3" />
    <widget name="status2" position="60,44" size="1800,70"
        font="Regular;28" halign="left" valign="top"
        transparent="1" foregroundColor="#00FFFF00" zPosition="3" />
    <widget name="status3" position="60,78" size="1800,60"
        font="Regular;28" halign="left" valign="top"
        transparent="1" foregroundColor="#00FFFF00" zPosition="3" />
    </screen>
    """

    def __init__(self, session):
        Screen.__init__(self, session)

        # Widgets
        self["sub_bg"] = Label("")
        self["subtitle"] = Label("")
        self["status1"] = Label("")
        self["status2"] = Label("")
        self["status3"] = Label("")

        self.manual_index = -1
        self.manual_mode = False
        self.manualAutoTimer = eTimer()
        self.manualAutoTimer.callback.append(self._manualAutoApply)



        self.cues_raw = []
        self.cues = []
        self.active_path = None

        self.paused = False
        self._statusVisible = False
        self.fallback_now_ms = 0

        # Timers
        self.timer = eTimer()
        self.timer.callback.append(self.onTick)

        self.statusTimer = eTimer()
        self.statusTimer.callback.append(self._hideStatus)
        # --- Load our keymap (for CH+/CH- -> nextSub/prevSub) ---
        try:
            from Tools.Directories import resolveFilename, SCOPE_PLUGINS
            keymap_path = resolveFilename(SCOPE_PLUGINS, "Extensions/CiefpSRTplayer/keymap.xml")
        except Exception:
            keymap_path = "/usr/lib/enigma2/python/Plugins/Extensions/CiefpSRTplayer/keymap.xml"

        try:
            keymapparser.readKeymap(keymap_path)
        except Exception:
            pass

        # --- CH+/CH- actions from our keymap context ---
        self["ch_actions"] = ActionMap(
            ["CiefpSRTplayerActions"],
            {
                "nextSub": self.cueNext,
                "prevSub": self.cuePrev,
            },
            1
        )

        # --- Normal actions (existing controls) ---
        self["actions"] = ActionMap(
            ["OkCancelActions", "DirectionActions", "ColorActions", "MenuActions", "NumberActions"],
            {
                "cancel": self.close,
                "ok": self.togglePause,

                "left": self.subBack,
                "right": self.subFwd,
                "up": self.posUp,
                "down": self.posDown,

                "red": self.fontDown,
                "green": self.fontUp,
                "yellow": self.openCuePicker,  # Sada otvara Cue Picker umesto toggle info
                "blue": self.fpsNext,

                "menu": self.openMenu,
            },
            1
        )

        # Apply after layout is finished (instances exist)
        self.onLayoutFinish.append(self._onLayoutFinished)

    def _onLayoutFinished(self):
        # sada instance postoje
        self.applyY()
        self.applyStyle()
        self.applyBackground()
        try:
            p = config.plugins.ciefpsrt.srt_path.value
            if p and not os.path.exists(p):
                config.plugins.ciefpsrt.srt_path.value = ""
                config.plugins.ciefpsrt.srt_path.save()
        except Exception:
            pass

        self.reloadSrt(show_error=False)

        # ako nemamo seek i offset je 0, pokušaj da se odmah “uhvati” EPG elapsed
        if get_playback_ms(self.session) is None and int(config.plugins.ciefpsrt.offset_ms.value) == 0:
            epg_ms = self._get_epg_elapsed_ms()
            if epg_ms is not None:
                # offset ostaje 0, ali fallback_now_ms postavi da tick odmah “zna” gde je
                self.fallback_now_ms = int(epg_ms)
                self.showStatus("EPG sync: %ds" % (epg_ms // 1000), timeout_s=6)

        self.timer.start(200, False)
        self.showStatus(timeout_s=15)

    def _get_epg_elapsed_ms(self):
        try:
            service = self.session.nav.getCurrentService()
            if not service:
                return None
            info = service.info()
            if not info:
                return None
            ev = info.getEvent(0)  # current event
            if not ev:
                return None
            begin = ev.getBeginTime()
            if not begin:
                return None
            now_s = int(time())
            elapsed_s = now_s - int(begin)
            if elapsed_s < 0:
                elapsed_s = 0
            return elapsed_s * 1000
        except Exception:
            return None

    def _get_now_ms(self):
        now = get_real_now_ms(self.session)
        if now is not None:
            return now

        # fallback tick
        self.fallback_now_ms += 200
        return int(self.fallback_now_ms)

    def _fps_label(self, mode):
        labels = {
            "none": "None (as SRT)",
            "23976_to_25": "23.976 → 25",
            "25_to_23976": "25 → 23.976",
            "24_to_25": "24 → 25",
            "25_to_24": "25 → 24",
        }
        return labels.get(mode, str(mode))

    def _fps_suggestion(self):
        # treba nam EPG duration i SRT duration
        epg_elapsed_ms, epg_dur_sec = self._get_epg_info()
        if not epg_dur_sec or epg_dur_sec <= 0:
            return None
        if not self.cues:
            return None

        srt_dur_ms = int(self.cues[-1][1])  # kraj poslednjeg cue-a
        if srt_dur_ms <= 0:
            return None

        epg_ms = int(epg_dur_sec) * 1000

        # ako su već vrlo blizu (npr. < 1.5%), ne predlaži ništa
        diff_ratio = abs(srt_dur_ms - epg_ms) / float(epg_ms)
        if diff_ratio < 0.015:
            return None

        # očekivani odnosi (kako scale_cues radi: ms * scale)
        # mode -> očekivani scale faktor
        candidates = {
            "none": 1.0,
            "23976_to_25": 23.976 / 25.0,
            "25_to_23976": 25.0 / 23.976,
            "24_to_25": 24.0 / 25.0,
            "25_to_24": 25.0 / 24.0,
        }

        best_mode = None
        best_err = None

        # pretpostavimo da je SRT “u nekom fps-u”, a mi želimo da ga približimo EPG duration-u.
        # Ako bismo primenili scale, novi SRT duration bi bio srt_dur_ms * scale.
        for mode, scale in candidates.items():
            new_ms = srt_dur_ms * scale
            err = abs(new_ms - epg_ms) / float(epg_ms)
            if best_err is None or err < best_err:
                best_err = err
                best_mode = mode

        # ne predlaži "none" ako je očigledno daleko
        if best_mode == "none":
            return None

        # predloži samo ako nakon predloga postaje dovoljno bolje (npr. < 2%)
        if best_err is not None and best_err < 0.02:
            return best_mode

        return None

    def _manualAutoApply(self):
        # ako je korisnik u manual modu i izabrao nešto, primeni i vrati u AUTO
        if self.manual_mode and self.manual_index >= 0:
            self.applyManualSync()

    def _ms_to_srt(self, ms):
        if ms is None:
            return "--:--:--,---"
        ms = int(ms)
        if ms < 0:
            ms = 0
        hh = ms // 3600000
        mm = (ms % 3600000) // 60000
        ss = (ms % 60000) // 1000
        mss = ms % 1000
        return "%02d:%02d:%02d,%03d" % (hh, mm, ss, mss)

    def _sec_to_hms(self, sec):
        if sec is None:
            return "--:--:--"
        sec = int(sec)
        if sec < 0:
            sec = 0
        hh = sec // 3600
        mm = (sec % 3600) // 60
        ss = sec % 60
        return "%d:%02d:%02d" % (hh, mm, ss)

    def _get_epg_info(self):
        """
        return (elapsed_ms, duration_sec) ili (None, None)
        """
        try:
            service = self.session.nav.getCurrentService()
            if not service:
                return (None, None)
            info = service.info()
            if not info:
                return (None, None)
            ev = info.getEvent(0)
            if not ev:
                return (None, None)
            begin = ev.getBeginTime()
            dur = ev.getDuration()  # u sekundama
            if not begin:
                return (None, dur)
            now_s = int(time())
            elapsed_s = now_s - int(begin)
            if elapsed_s < 0:
                elapsed_s = 0
            return (elapsed_s * 1000, dur)
        except Exception:
            return (None, None)

    def _find_cue_index(self, t_ms):
        """
        Nađe najbolji cue za dati t_ms (subtitle timeline).
        """
        if not self.cues:
            return -1
        # brza linearna pretraga (može i binarna kasnije)
        idx = 0
        for i, (s, e, _) in enumerate(self.cues):
            if s <= t_ms <= e:
                return i
            if t_ms < s:
                return max(0, i - 1)
            idx = i
        return idx

    def _get_current_sub_index(self):
        """
        Trenutni cue po "real time" = now + offset
        """
        now = self._get_now_ms()
        t_ms = int(now) + int(config.plugins.ciefpsrt.offset_ms.value)
        return self._find_cue_index(t_ms)

    def applyY(self):
        y = int(config.plugins.ciefpsrt.y_pos.value)

        if self["subtitle"].instance is not None:
            p = self["subtitle"].instance.position()
            self["subtitle"].instance.move(ePoint(p.x(), y))

        if self["sub_bg"].instance is not None:
            p = self["sub_bg"].instance.position()
            self["sub_bg"].instance.move(ePoint(p.x(), y))

    def applyStyle(self):
        if self["subtitle"].instance is None:
            return

        fs = int(config.plugins.ciefpsrt.font_size.value)
        self["subtitle"].instance.setFont(gFont("Regular", fs))

        colors = {
            "yellow": 0x00FFFF00,  # Žuta
            "white": 0x00FFFFFF,  # Bela
            "cyan": 0x0000FFFF,  # Cijan
            "purple": 0x00800080,  # Ljubičasta
            "orange": 0x00FFA500,  # Narandžasta
            "green": 0x0000FF00,  # Zelena
            "blue": 0x000000FF,  # Plava
            "red": 0x00FF0000,  # Crvena
        }

        c = colors.get(config.plugins.ciefpsrt.color.value, 0x00FFFF00)
        self["subtitle"].instance.setForegroundColor(gRGB(c))

    def applyBackground(self):
        if self["sub_bg"].instance is None:
            return
        if config.plugins.ciefpsrt.bg_mode.value == "none":
            self["sub_bg"].hide()
        else:
            self["sub_bg"].show()
            self["sub_bg"].instance.setBackgroundColor(gRGB(0x000000))

    def applyQuickPreset(self, preset_key=None):
        """Primeni quick preset (poziva se iz menija)"""
        if preset_key is None:
            preset_key = config.plugins.ciefpsrt.quick_preset.value

        preset = QUICK_PRESETS.get(preset_key)
        if not preset or preset_key == "none":
            return

        # Sačuvaj stare vrednosti za eventualni undo
        self._old_preset_values = {
            "fps": config.plugins.ciefpsrt.scale_mode.value,
            "offset": config.plugins.ciefpsrt.offset_ms.value,
            "color": config.plugins.ciefpsrt.color.value,
            "bg_mode": config.plugins.ciefpsrt.bg_mode.value,
            "font_size": config.plugins.ciefpsrt.font_size.value,
            "y_pos": config.plugins.ciefpsrt.y_pos.value,
            "encoding": config.plugins.ciefpsrt.encoding.value,
        }

        # Primeni nove vrednosti
        changed = False
        if preset["fps"] is not None:
            config.plugins.ciefpsrt.scale_mode.value = preset["fps"]
            changed = True
        if preset["offset"] is not None:
            config.plugins.ciefpsrt.offset_ms.value = preset["offset"]
            changed = True
        if preset["color"] is not None:
            config.plugins.ciefpsrt.color.value = preset["color"]
            changed = True
        if preset["bg_mode"] is not None:
            config.plugins.ciefpsrt.bg_mode.value = preset["bg_mode"]
            changed = True
        if preset["font_size"] is not None:
            config.plugins.ciefpsrt.font_size.value = preset["font_size"]
            changed = True
        if preset["y_pos"] is not None:
            config.plugins.ciefpsrt.y_pos.value = preset["y_pos"]
            changed = True
        if preset["encoding"] is not None:
            config.plugins.ciefpsrt.encoding.value = preset["encoding"]
            changed = True

        if changed:
            # Primeni promene na UI
            self.applyY()
            self.applyStyle()
            self.applyBackground()
            self.cues = scale_cues(self.cues_raw, config.plugins.ciefpsrt.scale_mode.value)
            self.showStatus(f"Preset: {preset['name']}", timeout_s=5)

    def _hideStatus(self):
        try:
            self["status1"].setText("")
            self["status2"].setText("")
            self["status3"].setText("")
        except Exception:
            pass
        self._statusVisible = False

    def _showStatusTimed(self, seconds=15):
        try:
            self.statusTimer.stop()
        except Exception:
            pass
        try:
            self.statusTimer.start(int(seconds * 1000), True)
        except Exception:
            pass

    def cueNext(self):
        if not self.cues:
            return

        self.manual_mode = True
        if self.manual_index < 0:
            self.manual_index = self._get_current_sub_index()
            if self.manual_index < 0:
                self.manual_index = 0
        else:
            self.manual_index = min(len(self.cues) - 1, self.manual_index + 1)

        self["subtitle"].setText(self.cues[self.manual_index][2])
        self.showStatus("Manual %d/%d (OK=Apply)" % (self.manual_index + 1, len(self.cues)), timeout_s=5)
        try:
            self.manualAutoTimer.stop()
        except Exception:
            pass
        self.manualAutoTimer.start(800, True)  # 800ms posle poslednjeg klika -> apply

    def cuePrev(self):
        if not self.cues:
            return

        self.manual_mode = True
        if self.manual_index < 0:
            self.manual_index = self._get_current_sub_index()
            if self.manual_index < 0:
                self.manual_index = 0
        else:
            self.manual_index = max(0, self.manual_index - 1)

        self["subtitle"].setText(self.cues[self.manual_index][2])
        self.showStatus("Manual %d/%d (OK=Apply)" % (self.manual_index + 1, len(self.cues)), timeout_s=5)
        try:
            self.manualAutoTimer.stop()
        except Exception:
            pass
        self.manualAutoTimer.start(800, True)  # 800ms posle poslednjeg klika -> apply

    def applyManualSync(self):
        if not self.cues or self.manual_index < 0:
            return
        self._syncToCueIndex(self.manual_index)

    def _syncToCueIndex(self, idx):
        now = self._get_now_ms()
        now = int(now)
        cue_start = int(self.cues[idx][0])

        config.plugins.ciefpsrt.offset_ms.value = cue_start - now

        self.manual_mode = False
        self.showStatus("Synced at %d/%d" % (idx + 1, len(self.cues)), timeout_s=5)

        # odmah prikaži titl koji si izabrao
        self["subtitle"].setText(self.cues[idx][2])

    def showStatus(self, extra="", timeout_s=15):
        path = os.path.basename(config.plugins.ciefpsrt.srt_path.value or "(no file)")

        # 1. red
        line1 = "CiefpSRTplayer v%s | %s" % (PLUGIN_VERSION, path)

        # 2. red (podešavanja) + lep FPS label
        fps_mode = config.plugins.ciefpsrt.scale_mode.value
        try:
            fps_txt = self._fps_label(fps_mode)
        except Exception:
            fps_txt = str(fps_mode)

        line2 = "Offset:%dms | Y:%d | Font:%d | Color:%s | BG:%s | Enc:%s | FPS:%s" % (
            config.plugins.ciefpsrt.offset_ms.value,
            config.plugins.ciefpsrt.y_pos.value,
            config.plugins.ciefpsrt.font_size.value,
            config.plugins.ciefpsrt.color.value,
            config.plugins.ciefpsrt.bg_mode.value,
            ENC_LABEL.get(config.plugins.ciefpsrt.encoding.value, config.plugins.ciefpsrt.encoding.value),
            fps_txt,
        )
        if self.paused:
            line2 += " | PAUSED"

        # 3. red (subtitle/epg info + hint + extra)
        line3 = ""
        try:
            idx = self.manual_index if self.manual_mode else self._get_current_sub_index()

            if getattr(self, "cues", None) and idx is not None and 0 <= idx < len(self.cues):
                s, e, _ = self.cues[idx]
                line3 = "Subtitle:%d/%d  %s --> %s" % (
                    idx + 1, len(self.cues),
                    self._ms_to_srt(s),
                    self._ms_to_srt(e),
                )

            epg_elapsed_ms, epg_dur_sec = self._get_epg_info()
            epg_part = ""
            if epg_elapsed_ms is not None:
                epg_part = "EPG:%s" % self._ms_to_srt(epg_elapsed_ms).split(",")[0]
            if epg_dur_sec is not None:
                epg_part += "  Dur:%s" % self._sec_to_hms(epg_dur_sec)

            if epg_part:
                line3 = (line3 + " | " if line3 else "") + epg_part

            # --- Auto FPS hint (EPG duration vs SRT duration) ---
            try:
                suggest = self._fps_suggestion()
            except Exception:
                suggest = None

            if suggest:
                try:
                    hint_txt = self._fps_label(suggest)
                except Exception:
                    hint_txt = str(suggest)
                line3 = (line3 + " | " if line3 else "") + ("Hint FPS: %s" % hint_txt)

        except Exception:
            pass

        if extra:
            line3 = (line3 + " | " if line3 else "") + extra

        self["status1"].setText(line1)
        self["status2"].setText(line2)
        self["status3"].setText(line3)
        self._statusVisible = True
        self._showStatusTimed(timeout_s)

    def reloadSrt(self, show_error=True):
        path = config.plugins.ciefpsrt.srt_path.value
        if not path or not os.path.exists(path):
            self.cues_raw, self.cues = [], []
            self["subtitle"].setText("")
            if show_error:
                self.session.open(MessageBox, "No .srt selected.\nUse MENU -> Settings to select a file.", MessageBox.TYPE_INFO, timeout=5)
            return
        try:
            self.cues_raw = load_srt(path, config.plugins.ciefpsrt.encoding.value)
            self.cues = scale_cues(self.cues_raw, config.plugins.ciefpsrt.scale_mode.value)
            self.showStatus("Loaded %d cues" % len(self.cues))
        except Exception as e:
            self.cues_raw, self.cues = [], []
            self["subtitle"].setText("")
            if show_error:
                self.session.open(MessageBox, "Failed to load SRT:\n%s" % str(e), MessageBox.TYPE_ERROR, timeout=6)

    def toggleInfo(self):
        if getattr(self, "_statusVisible", False):
            try:
                self.statusTimer.stop()
            except Exception:
                pass
            self._hideStatus()
            return
        self.showStatus(timeout_s=15)

    def togglePause(self):
        # Ako si u manual browse modu, OK = Apply sync i vrati u AUTO
        if self.manual_mode:
            self.applyManualSync()
            return

        # inače normalno Pause/Resume
        self.paused = not self.paused
        if self.paused:
            self["subtitle"].setText("")
        self.showStatus(timeout_s=15)

    def openCuePicker(self):
        """Otvara Cue Picker za sinhronizaciju"""
        path = config.plugins.ciefpsrt.srt_path.value
        if not path or not os.path.exists(path):
            self.session.open(MessageBox, "No .srt selected.\nUse MENU -> Settings to select a file.", MessageBox.TYPE_INFO, timeout=5)
            return
        
        # Otvori CuePicker sa callback-om
        self.session.openWithCallback(
            self._cuePickerCallback,
            CuePickerScreen,
            self.session,  # overlay_session
            path
        )

    def _cuePickerCallback(self, cue_ms):
        """Callback nakon što korisnik izabere cue u CuePicker-u"""
        if cue_ms is not None:
            now = self._get_now_ms()
            if now is not None:
                config.plugins.ciefpsrt.offset_ms.value = int(cue_ms) - int(now)
                self.showStatus("Synced from Cue Picker", timeout_s=6)
            else:
                self.showStatus("Could not get current time", timeout_s=3)

    def subBack(self):
        config.plugins.ciefpsrt.offset_ms.value -= 1000
        self.showStatus()

    def subFwd(self):
        config.plugins.ciefpsrt.offset_ms.value += 1000
        self.showStatus()

    def posUp(self):
        config.plugins.ciefpsrt.y_pos.value = max(0, int(config.plugins.ciefpsrt.y_pos.value) - 10)
        self.applyY(); self.showStatus(timeout_s=15)

    def posDown(self):
        config.plugins.ciefpsrt.y_pos.value = min(1080, int(config.plugins.ciefpsrt.y_pos.value) + 10)
        self.applyY(); self.showStatus(timeout_s=15)

    def fontUp(self):
        config.plugins.ciefpsrt.font_size.value = min(90, int(config.plugins.ciefpsrt.font_size.value) + 2)
        self.applyStyle(); self.showStatus(timeout_s=15)

    def fontDown(self):
        config.plugins.ciefpsrt.font_size.value = max(24, int(config.plugins.ciefpsrt.font_size.value) - 2)
        self.applyStyle(); self.showStatus(timeout_s=15)

    def cycleColor(self):
        choices = [c[0] for c in config.plugins.ciefpsrt.color.choices]
        i = choices.index(config.plugins.ciefpsrt.color.value)
        config.plugins.ciefpsrt.color.value = choices[(i + 1) % len(choices)]
        self.applyStyle(); self.showStatus(timeout_s=15)

    def cycleBackground(self):
        choices = [c[0] for c in config.plugins.ciefpsrt.bg_mode.choices]
        i = choices.index(config.plugins.ciefpsrt.bg_mode.value)
        config.plugins.ciefpsrt.bg_mode.value = choices[(i + 1) % len(choices)]
        self.applyBackground(); self.showStatus(timeout_s=15)

    def fpsPrev(self):
        choices = [c[0] for c in config.plugins.ciefpsrt.scale_mode.choices]
        i = choices.index(config.plugins.ciefpsrt.scale_mode.value)
        config.plugins.ciefpsrt.scale_mode.value = choices[(i - 1) % len(choices)]
        self.cues = scale_cues(self.cues_raw, config.plugins.ciefpsrt.scale_mode.value)
        self.showStatus()

    def fpsNext(self):
        # U Enigma2 choices nekad budu tuple-ovi, nekad stringovi, nekad wrapper objekti.
        raw = getattr(config.plugins.ciefpsrt.scale_mode, "choices", None)

        choices = []
        if raw:
            for it in list(raw):
                try:
                    # tuple/list: ("none","No FPS scale")
                    if isinstance(it, (tuple, list)) and len(it) > 0:
                        choices.append(str(it[0]))
                    else:
                        # string ili neki objekat -> probaj kao string
                        s = str(it)
                        # ako izgleda kao "('none', 'No FPS scale')" pokušaj da izvučeš prvo
                        if s.startswith("(") and "," in s:
                            head = s.split(",", 1)[0].lstrip("(").strip().strip("'\"")
                            choices.append(head)
                        else:
                            choices.append(s.strip())
                except Exception:
                    pass

        # fallback ako je ispalo prazno
        if not choices:
            choices = ["none", "23976_to_25", "25_to_23976", "24_to_25", "25_to_24"]

        cur = (config.plugins.ciefpsrt.scale_mode.value or "").strip()

        # ako trenutna vrednost nije u listi, kreni od prve (ne pucaj)
        if cur in choices:
            i = choices.index(cur)
        else:
            i = -1

        nxt = choices[(i + 1) % len(choices)]

        config.plugins.ciefpsrt.scale_mode.value = nxt
        try:
            config.plugins.ciefpsrt.scale_mode.save()
        except Exception:
            pass

        # brže nego reloadSrt()
        self.cues = scale_cues(self.cues_raw, nxt)

        self.showStatus("FPS: %s" % self._fps_label(nxt), timeout_s=6)

    def openMenu(self):
        choices = [
            ("Quick Presets", "presets"),
            ("Settings", "settings"),
            ("Select .srt file", "pick_srt"),
            ("Change subtitles folder", "pick_folder"),
            ("Reload current SRT", "reload"),
            ("Pick cue & Sync", "cue_picker"),      # NOVO
            ("Toggle Info bar", "toggle_info"),      # NOVO (ovo je bilo na žutom)
            ("Close", "close"),
        ]
        self.session.openWithCallback(self.menuCb, ChoiceBox, title="CiefpSRTplayer Menu", list=choices)

    def menuCb(self, choice):
        if not choice:
            return
        key = choice[1]
        if key == "presets":
            self.showPresetsMenu()
        elif key == "settings":
            self.session.open(CiefpSettings, self.applyAllAndReload)
        elif key == "pick_srt":
            start_dir = config.plugins.ciefpsrt.default_dir.value or "/"
            self.session.open(SRTFileBrowser, start_dir, self.onSrtSelected)
        elif key == "pick_folder":
            curr = config.plugins.ciefpsrt.default_dir.value or "/"
            self.session.openWithCallback(self.onDirChosen, LocationBox, text="Select subtitles folder", currDir=curr)
        elif key == "reload":
            self.reloadSrt(show_error=True)
        elif key == "cue_picker":
            self.openCuePicker()
        elif key == "toggle_info":
            self.toggleInfo()  # <-- originalna funkcija sa žutog
        elif key == "close":
            self.close()

    def showPresetsMenu(self):
        """Prikaži meni sa presetima"""
        preset_list = []
        for key, preset in QUICK_PRESETS.items():
            preset_list.append((preset["name"], key))

        self.session.openWithCallback(
            self.applyPresetFromMenu,
            ChoiceBox,
            title="Select Quick Preset",
            list=preset_list
        )

    def applyPresetFromMenu(self, choice):
        if choice and choice[1]:
            self.applyQuickPreset(choice[1])

    def onDirChosen(self, newdir):
        if newdir:
            config.plugins.ciefpsrt.default_dir.value = _ensure_dir_slash(newdir)
            self.showStatus("Folder set")

    def onSrtSelected(self, sel):
        # sel može biti string path ili tuple (path, cue_start_ms)
        cue_ms = None
        path = sel
        if isinstance(sel, (tuple, list)) and len(sel) >= 1:
            path = sel[0]
            if len(sel) >= 2:
                cue_ms = sel[1]

        if path:
            config.plugins.ciefpsrt.srt_path.value = path
            self.reloadSrt(show_error=True)

            # ako imamo cue_ms, odmah sync
            if cue_ms is not None and self.cues:
                now = self._get_now_ms()
                config.plugins.ciefpsrt.offset_ms.value = int(cue_ms) - int(now)
                self.showStatus("Synced from file browser", timeout_s=6)

    def applyAllAndReload(self):
        self.applyY(); self.applyStyle(); self.applyBackground(); self.reloadSrt(show_error=False); self.showStatus(timeout_s=15)

    def onTick(self):
        if self.paused:
            return
        if self.manual_mode:
            return
        t_ms = self._get_now_ms() + int(config.plugins.ciefpsrt.offset_ms.value)

        txt = ""
        for s, e, text in self.cues:
            if s <= t_ms <= e:
                txt = text
                break
        if txt:
            if config.plugins.ciefpsrt.bg_mode.value != "none":
                self["sub_bg"].show()
            self["subtitle"].setText(txt)
        else:
            self["subtitle"].setText("")
            if config.plugins.ciefpsrt.bg_mode.value != "none":
                self["sub_bg"].hide()

def main(session, **kwargs):
    session.open(CiefpOverlay)

def Plugins(**kwargs):
    return [
        PluginDescriptor(
            name="%s v%s" % (PLUGIN_NAME, PLUGIN_VERSION),
            description="SRT overlay player (offset/position/color/bg/encoding/font/fps)",
            where=PluginDescriptor.WHERE_PLUGINMENU,
            icon="icon.png",
            fnc=main
        )
    ]