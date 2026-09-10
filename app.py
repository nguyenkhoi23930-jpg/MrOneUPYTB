#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
MrOneUPYTB — Auto upload video YouTube
Tiêu đề/mô tả form + {TEN_TRUYEN}, multi-channel OAuth,
random tag theo chủ đề, thumb, hẹn giờ, ưu tiên tập 1→10,
license key theo máy, update GitHub.
"""

from __future__ import annotations

import hashlib
import json
import platform
import random
import re
import sys
import threading
import time
import traceback
import urllib.request
import zipfile
from datetime import datetime, timedelta
from pathlib import Path

import customtkinter as ctk
from tkinter import filedialog, messagebox

# ---------- version / branding ----------
APP_NAME = "MrOneUPYTB"
APP_VERSION = "1.0.4"
MASTER_KEY = "MrOne781933"
# GitHub Releases — chỉ up file .exe, tag = version (vd v1.0.1)
GITHUB_OWNER = "nguyenkhoi23930-jpg"
GITHUB_REPO = "MrOneUPYTB"
GITHUB_RELEASES_API = f"https://api.github.com/repos/{GITHUB_OWNER}/{GITHUB_REPO}/releases/latest"
GITHUB_RELEASES_PAGE = f"https://github.com/{GITHUB_OWNER}/{GITHUB_REPO}/releases"


def app_dir() -> Path:
    """Thư mục ghi được cạnh exe (hoặc folder script)."""
    if getattr(sys, "frozen", False):
        return Path(sys.executable).resolve().parent
    return Path(__file__).resolve().parent


def bundle_dir() -> Path:
    """Thư mục resource đóng trong exe (PyInstaller _MEIPASS)."""
    if getattr(sys, "frozen", False) and hasattr(sys, "_MEIPASS"):
        return Path(sys._MEIPASS)
    return app_dir()


def resolve_resource(*names: str) -> Path | None:
    """Ưu tiên file cạnh exe, không có thì lấy bản nhúng trong exe."""
    for name in names:
        ext = app_dir() / name
        if ext.exists():
            return ext
        bun = bundle_dir() / name
        if bun.exists():
            return bun
    return None


# ---------- paths (data luôn cạnh exe để ghi được) ----------
ROOT = app_dir()
DATA = ROOT / "data"
DATA.mkdir(exist_ok=True)
CONFIG_FILE = DATA / "config.json"
UPLOADED_FILE = DATA / "uploaded.json"
LICENSE_FILE = DATA / "license.json"
TOKENS_DIR = DATA / "tokens"
TOKENS_DIR.mkdir(exist_ok=True)
LOG_FILE = DATA / "log.txt"
THUMB_TMP = DATA / "thumb_tmp"
THUMB_TMP.mkdir(exist_ok=True)

# client_secret: cạnh exe HOẶC nhúng trong exe
_cs = resolve_resource("client_secret.json")
CLIENT_SECRET = _cs if _cs else (ROOT / "client_secret.json")

_logo = resolve_resource("logo_mrone.png")
LOGO_FILE = _logo if _logo else (ROOT / "logo_mrone.png")
_ico = resolve_resource("logo_mrone.ico")
ICON_FILE = _ico if _ico else (ROOT / "logo_mrone.ico")


def apply_window_icon(win) -> None:
    """Gắn icon MrONE lên title bar / taskbar Windows."""
    try:
        if ICON_FILE.exists():
            win.iconbitmap(default=str(ICON_FILE))
            win.iconbitmap(str(ICON_FILE))
    except Exception:
        pass
    try:
        from PIL import Image, ImageTk
        if LOGO_FILE.exists():
            img = Image.open(LOGO_FILE).convert("RGBA").resize((32, 32), Image.Resampling.LANCZOS)
            photo = ImageTk.PhotoImage(img)
            win.iconphoto(True, photo)
            win._icon_photo = photo  # giữ ref, tránh GC
    except Exception:
        pass

SCOPES = [
    "https://www.googleapis.com/auth/youtube",
    "https://www.googleapis.com/auth/youtube.upload",
    "https://www.googleapis.com/auth/youtube.force-ssl",
    "https://www.googleapis.com/auth/youtube.readonly",
    "https://www.googleapis.com/auth/userinfo.email",
    "openid",
]

VIDEO_EXTS = {".mp4", ".mov", ".mkv", ".avi", ".webm", ".m4v"}

DEFAULT_TITLE = "TRUYỆN MA ĐÌNH SOẠN : {TEN_TRUYEN} | CHUYỆN MA KINH DỊ ĐÊM KHUYA"
DEFAULT_DESC = """🔴 TRUYỆN MA ĐÌNH SOẠN: {TEN_TRUYEN}

🎧 Nghe truyện ma đêm khuya — chuyện ma kinh dị, oán hồn, nghiệp báo.

⚠️ Nội dung hư cấu, chỉ mang tính giải trí.

#truyenma #truyenmakinhdi #chuyenmademkhuya #truyenmadinhsoan
"""
DEFAULT_TAGS = "truyện ma,truyện ma kinh dị,chuyện ma đêm khuya,truyện ma đình soạn,kinh dị"

TOPIC_TAGS = {
    "Truyện ma": [
        "truyện ma", "truyện ma kinh dị", "chuyện ma đêm khuya", "truyện ma đình soạn",
        "kinh dị", "oán hồn", "nghiệp báo", "ma nữ", "truyện ma audio", "kể chuyện ma",
        "truyện ma có thật", "hồn ma", "truyện ma Việt Nam", "ma quỷ", "truyện kinh dị",
        "đêm khuya kể chuyện", "linh dị", "truyện ma rùng rợn", "âm binh", "tà thuật",
        "bà đồng", "nghĩa địa", "nhà bỏ hoang", "hồn thiêng", "trả nghiệp",
        "truyện ma hay", "nghe truyện ma", "truyện ma mới nhất", "ma đói", "quỷ nhập tràng",
    ],
    "Truyện ngôn tình": [
        "ngôn tình", "truyện ngôn tình", "tổng tài", "ngược tâm", "ngôn tình hay",
        "truyện tình cảm", "thanh xuân", "ngôn tình audio", "đam mỹ", "bách hợp",
        "ngôn tình Trung", "cổ đại", "hiện đại", "sủng", "trọng sinh",
        "xuyên không", "ngôn tình full", "kể chuyện đêm", "truyện hay", "tình yêu",
    ],
    "Truyện tiên hiệp": [
        "tiên hiệp", "tu tiên", "huyền huyễn", "tu chân", "đấu phá thương khung",
        "truyện tiên hiệp", "tu luyện", "kiếm hiệp", "pháp bảo", "luyện đan",
        "đại thừa", "tiên nhân", "yêu thú", "truyện audio", "kể chuyện",
        "tu tiên audio", "huyền huyễn hay", "truyện full", "đô thị tu tiên", "hệ thống",
    ],
    "Review / khác": [
        "review phim", "tóm tắt phim", "phim hay", "giải trí", "youtube việt nam",
        "nội dung hay", "xem ngay", "mới nhất", "trending", "viral",
        "kể chuyện", "audio", "podcast việt", "giải trí đêm khuya", "content hay",
    ],
}


def log(msg: str) -> None:
    line = f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] {msg}"
    print(line)
    try:
        with LOG_FILE.open("a", encoding="utf-8") as f:
            f.write(line + "\n")
    except Exception:
        pass


def load_json(path: Path, default):
    if path.exists():
        try:
            return json.loads(path.read_text(encoding="utf-8"))
        except Exception:
            return default
    return default


def save_json(path: Path, obj) -> None:
    path.write_text(json.dumps(obj, ensure_ascii=False, indent=2), encoding="utf-8")


def machine_id() -> str:
    raw = f"{platform.node()}|{platform.system()}|{platform.machine()}"
    try:
        import uuid
        raw += f"|{uuid.getnode()}"
    except Exception:
        pass
    return hashlib.sha256(raw.encode()).hexdigest()[:16].upper()


def make_machine_key(mid: str) -> str:
    h = hashlib.sha256(f"{MASTER_KEY}:{mid}".encode()).hexdigest()[:12].upper()
    return f"MRONE-{mid[:4]}-{h}"


def check_license(key: str) -> bool:
    key = (key or "").strip()
    if key == MASTER_KEY:
        return True
    mid = machine_id()
    if key == make_machine_key(mid):
        return True
    lic = load_json(LICENSE_FILE, {})
    if lic.get("key") == key and lic.get("machine_id") == mid:
        return True
    return False


def save_license(key: str) -> None:
    save_json(LICENSE_FILE, {
        "key": key.strip(),
        "machine_id": machine_id(),
        "activated_at": datetime.now().isoformat(timespec="seconds"),
    })


def parse_user_datetime(text: str) -> datetime | None:
    """Nhận nhiều kiểu giờ: 2026-09-09 12:00, 12:00, 12h, 12h00, 09/09/2026 12:00."""
    s = (text or "").strip()
    if not s:
        return None
    s = s.lower().replace("trưa", "").replace("sang", "").replace("sáng", "")
    s = s.replace("chieu", "").replace("chiều", "").replace("toi", "").replace("tối", "")
    s = re.sub(r"\s+", " ", s).strip()
    s = s.replace("h", ":")
    if s.endswith(":"):
        s = s + "00"
    # chỉ giờ: 12:00 / 12:00:00
    for fmt in ("%Y-%m-%d %H:%M", "%Y-%m-%d %H:%M:%S", "%d/%m/%Y %H:%M", "%d-%m-%Y %H:%M"):
        try:
            return datetime.strptime(s, fmt)
        except ValueError:
            pass
    for fmt in ("%H:%M", "%H:%M:%S"):
        try:
            t = datetime.strptime(s, fmt)
            now = datetime.now()
            dt = now.replace(hour=t.hour, minute=t.minute, second=0, microsecond=0)
            if dt <= now + timedelta(minutes=1):
                dt += timedelta(days=1)
            return dt
        except ValueError:
            pass
    return None


def story_name_from_file(path: Path) -> str:
    name = path.stem.strip()
    name = re.sub(r"^\s*\d+\s*[-._)]\s*", "", name)
    name = re.sub(r"^(tập|tap|ep|episode)\s*\d+\s*[-._:]?\s*", "", name, flags=re.I)
    return name.strip() or path.stem.strip()


def extract_episode(path: Path) -> int | None:
    s = path.stem
    patterns = [
        r"(?:tập|tap|ep|episode)\s*[-._]?\s*(\d{1,3})",
        r"(?:^|[\s_\-\.\[\(])(\d{1,3})(?:\s*[-._]\s*|\s*$)",
        r"[\(\[]\s*(\d{1,3})\s*[\)\]]",
    ]
    for pat in patterns:
        m = re.search(pat, s, flags=re.IGNORECASE)
        if m:
            n = int(m.group(1))
            if 1 <= n <= 999:
                return n
    return None


def random_tags_for_topic(topic: str, n: int = 10) -> str:
    pool = list(TOPIC_TAGS.get(topic) or TOPIC_TAGS["Truyện ma"])
    chosen = pool if len(pool) <= n else random.sample(pool, n)
    return ",".join(chosen)


def yt_available():
    try:
        import google_auth_oauthlib.flow  # noqa
        from googleapiclient.discovery import build  # noqa
        return True
    except ImportError:
        return False


def connect_channel() -> dict | None:
    # refresh path (exe nhúng hoặc file cạnh exe)
    cs = resolve_resource("client_secret.json")
    if cs is None or not cs.exists():
        raise FileNotFoundError(
            "Thiếu client_secret.json.\n"
            "• Bản exe: build lại kèm file này, hoặc để cạnh file .exe\n"
            "• Bản Python: đặt client_secret.json cạnh app.py"
        )
    global CLIENT_SECRET
    CLIENT_SECRET = cs
    from google_auth_oauthlib.flow import InstalledAppFlow
    from googleapiclient.discovery import build

    flow = InstalledAppFlow.from_client_secrets_file(str(CLIENT_SECRET), SCOPES)
    # prompt=consent + login để mỗi lần chọn đúng Gmail / Brand Account
    creds = flow.run_local_server(port=0, prompt="consent")
    youtube = build("youtube", "v3", credentials=creds)
    resp = youtube.channels().list(part="id,snippet", mine=True).execute()
    items = resp.get("items") or []
    if not items:
        raise RuntimeError("Không lấy được kênh. Hãy chọn đúng Brand Account lúc Google hỏi.")
    ch = items[0]
    ch_id = ch["id"]
    title = ch["snippet"]["title"]

    email = ""
    try:
        oauth2 = build("oauth2", "v2", credentials=creds)
        info = oauth2.userinfo().get().execute()
        email = (info.get("email") or "").strip()
    except Exception:
        email = ""

    token_path = TOKENS_DIR / f"{ch_id}.json"
    token_path.write_text(creds.to_json(), encoding="utf-8")
    return {"id": ch_id, "title": title, "email": email, "token_file": str(token_path)}


def youtube_from_token(token_file: str):
    from google.oauth2.credentials import Credentials
    from google.auth.transport.requests import Request
    from googleapiclient.discovery import build

    creds = Credentials.from_authorized_user_file(token_file, SCOPES)
    if creds and creds.expired and creds.refresh_token:
        creds.refresh(Request())
        Path(token_file).write_text(creds.to_json(), encoding="utf-8")
    if not creds or not creds.valid:
        raise RuntimeError("Token hết hạn / lỗi. Kết nối lại kênh.")
    return build("youtube", "v3", credentials=creds)


class JobCancelled(Exception):
    pass


def upload_video(youtube, file_path: Path, title: str, description: str, tags: list[str],
                 category_id: str, made_for_kids: bool, publish_at_iso: str | None,
                 should_cancel=None, notify_subscribers: bool = True):
    from googleapiclient.http import MediaFileUpload

    status = {"selfDeclaredMadeForKids": bool(made_for_kids)}
    if publish_at_iso:
        # private đến đúng giờ → YouTube tự công chiếu
        status["privacyStatus"] = "private"
        status["publishAt"] = publish_at_iso
        status["embeddable"] = True
        status["publicStatsViewable"] = True
    else:
        status["privacyStatus"] = "public"

    body = {
        "snippet": {
            "title": title[:100],
            "description": description[:5000],
            "tags": tags[:30],
            "categoryId": str(category_id),
        },
        "status": status,
    }
    media = MediaFileUpload(str(file_path), chunksize=8 * 1024 * 1024, resumable=True)
    request = youtube.videos().insert(
        part="snippet,status",
        body=body,
        media_body=media,
        notifySubscribers=bool(notify_subscribers),
    )
    response = None
    while response is None:
        if should_cancel and should_cancel():
            raise JobCancelled("Người dùng hủy job")
        status_u, response = request.next_chunk()
        if status_u:
            log(f"  upload {int(status_u.progress() * 100)}%")
    return response


def apply_schedule_on_video(youtube, video_id: str, publish_at_iso: str, made_for_kids: bool = False):
    """Gắn lại Lên lịch đúng giờ trên video vừa up (Studio: Lên lịch + ngày/giờ)."""
    existing = youtube.videos().list(part="status,snippet", id=video_id).execute()
    items = existing.get("items") or []
    if not items:
        raise RuntimeError("Không thấy video vừa up để gắn lịch.")
    st = dict(items[0].get("status") or {})
    st["privacyStatus"] = "private"
    st["publishAt"] = publish_at_iso
    st["embeddable"] = True
    st["publicStatsViewable"] = True
    st["selfDeclaredMadeForKids"] = bool(made_for_kids)
    return youtube.videos().update(
        part="status",
        body={"id": video_id, "status": st},
    ).execute()


STUDIO_INNERTUBE_KEY = "AIzaSyCjc_pVEDi4qsv5MtC2dMXzpF5598ayT8w"


def _youtube_access_token(youtube) -> str | None:
    try:
        creds = getattr(getattr(youtube, "_http", None), "credentials", None)
        if creds is None:
            return None
        if getattr(creds, "expired", False) and getattr(creds, "refresh_token", None):
            from google.auth.transport.requests import Request
            creds.refresh(Request())
        return getattr(creds, "token", None)
    except Exception:
        return None


def studio_set_schedule_premiere(youtube, video_id: str, local_dt: datetime, want_premiere: bool) -> str:
    """
    Gọi YouTube Studio metadata_update để gắn Lên lịch + tick Công chiếu.
    Dùng OAuth token sẵn có. Nếu Studio từ chối, vẫn còn lịch qua Data API.
    """
    token = _youtube_access_token(youtube)
    if not token:
        raise RuntimeError("Không lấy được OAuth token.")
    ts = vn_unix(local_dt)
    context = {
        "client": {
            "clientName": "WEB_CREATOR",
            "clientVersion": "1.20240901.01.00",
            "hl": "vi",
            "gl": "VN",
            "utcOffsetMinutes": 420,
        }
    }
    payloads = []
    sched = {"timeSec": str(ts), "privacy": "PUBLIC"}
    base = {
        "context": context,
        "encryptedVideoId": video_id,
        "videoReadMask": {
            "privacyState": True,
            "scheduledPublishing": True,
            "premiere": {"all": True},
        },
        "privacyState": {"newPrivacy": "PRIVATE"},
        "scheduledPublishing": {"set": dict(sched)},
        "draftState": {
            "operation": "MDE_DRAFT_STATE_UPDATE_OPERATION_REMOVE_DRAFT_STATE"
        },
        "flowType": "MDE_FLOW_TYPE_EDIT",
    }
    payloads.append(base)
    if want_premiere:
        for extra in (
            {"premiere": {"operation": "PREMIERE_OPERATION_ENABLE"}},
            {"premiere": {"set": True}},
            {"premiere": {"enable": True}},
            {"scheduledPremiere": {"set": True}},
            {"publicPremiere": {"set": True}},
        ):
            p = dict(base)
            p.update(extra)
            p["scheduledPublishing"] = {
                "set": {**sched, "isPremiere": True, "premiere": True}
            }
            payloads.append(p)

    url = (
        "https://studio.youtube.com/youtubei/v1/video_manager/metadata_update"
        f"?alt=json&key={STUDIO_INNERTUBE_KEY}"
    )
    last_err = "Studio không nhận request"
    for body in payloads:
        req = urllib.request.Request(
            url,
            data=json.dumps(body).encode("utf-8"),
            method="POST",
            headers={
                "Authorization": f"Bearer {token}",
                "Content-Type": "application/json",
                "X-Goog-AuthUser": "0",
                "Origin": "https://studio.youtube.com",
                "Referer": "https://studio.youtube.com/",
                "User-Agent": "Mozilla/5.0",
            },
        )
        try:
            with urllib.request.urlopen(req, timeout=30) as resp:
                raw = resp.read().decode("utf-8", errors="replace")
            if resp.status >= 400:
                last_err = raw[:300]
                continue
            return "ok"
        except Exception as e:
            last_err = str(e)
            continue
    raise RuntimeError(last_err)


def setup_premiere_event(youtube, video_id: str, title: str, description: str, start_iso: str):
    """
    Cố gắng bật Công chiếu.
    API v3 không có đúng nút Studio 'Đặt làm video Công chiếu' trên video VOD đã up.
    Cách gần nhất: tạo liveBroadcast cùng giờ. Kênh phải bật livestream.
    """
    body = {
        "snippet": {
            "title": title[:100],
            "description": (description or title)[:5000],
            "scheduledStartTime": start_iso,
        },
        "status": {
            "privacyStatus": "public",
            "selfDeclaredMadeForKids": False,
        },
        "contentDetails": {
            "enableAutoStart": True,
            "enableAutoStop": True,
            "enableDvr": True,
            "recordFromStart": True,
            "enableClosedCaptions": False,
        },
    }
    # Thử xem video đã là broadcast chưa (hiếm, nhưng không tạo video mới nếu được)
    try:
        listed = youtube.liveBroadcasts().list(part="id,snippet,status", id=video_id).execute()
        if listed.get("items"):
            br = listed["items"][0]
            br.setdefault("snippet", {})["scheduledStartTime"] = start_iso
            br.setdefault("snippet", {})["title"] = title[:100]
            return youtube.liveBroadcasts().update(
                part="snippet,status,contentDetails",
                body=br,
            ).execute(), "update"
    except Exception:
        pass
    created = youtube.liveBroadcasts().insert(
        part="snippet,status,contentDetails",
        body=body,
    ).execute()
    return created, "insert"


def find_thumb_for_video(video: Path) -> Path | None:
    folder = video.parent
    stem = video.stem
    suffixes = [
        f"{stem}+Thumb", f"{stem} Thumb", f"{stem}_Thumb", f"{stem}-Thumb",
        f"{stem}Thumb", f"{stem}_thumb", f"{stem}-thumb", f"{stem} thumb", stem,
    ]
    for base in suffixes:
        for ext in (".jpg", ".jpeg", ".png", ".webp"):
            p = folder / f"{base}{ext}"
            if p.exists() and p.is_file():
                return p
    return None


def overlay_story_on_thumb(src: Path, ten_truyen: str, out_dir: Path) -> Path:
    from PIL import Image, ImageDraw, ImageFont

    out_dir.mkdir(parents=True, exist_ok=True)
    img = Image.open(src).convert("RGB")
    w, h = img.size
    draw = ImageDraw.Draw(img)
    text = ten_truyen.strip()
    size = max(28, int(w * 0.055))
    font = None
    for fp in (
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
        "C:/Windows/Fonts/arialbd.ttf",
        "C:/Windows/Fonts/arial.ttf",
        "C:/Windows/Fonts/tahomabd.ttf",
    ):
        if Path(fp).exists():
            try:
                font = ImageFont.truetype(fp, size)
                break
            except Exception:
                pass
    if font is None:
        font = ImageFont.load_default()

    def text_w(s: str) -> int:
        box = draw.textbbox((0, 0), s, font=font)
        return box[2] - box[0]

    words = text.split()
    lines, cur = [], ""
    max_w = int(w * 0.90)
    for word in words:
        trial = (cur + " " + word).strip()
        if text_w(trial) <= max_w:
            cur = trial
        else:
            if cur:
                lines.append(cur)
            cur = word
    if cur:
        lines.append(cur)
    if not lines:
        lines = [text]

    line_h = size + 8
    block_h = line_h * len(lines) + 20
    y0 = h - block_h - int(h * 0.04)
    overlay = Image.new("RGBA", img.size, (0, 0, 0, 0))
    od = ImageDraw.Draw(overlay)
    od.rectangle([0, y0 - 8, w, h], fill=(0, 0, 0, 170))
    img = Image.alpha_composite(img.convert("RGBA"), overlay).convert("RGB")
    draw = ImageDraw.Draw(img)
    y = y0
    for line in lines:
        tw = text_w(line)
        x = (w - tw) // 2
        for dx, dy in ((-2, 0), (2, 0), (0, -2), (0, 2), (-2, -2), (2, 2)):
            draw.text((x + dx, y + dy), line, font=font, fill=(0, 0, 0))
        draw.text((x, y), line, font=font, fill=(255, 230, 80))
        y += line_h
    dest = out_dir / f"{src.stem}_overlay.jpg"
    img.save(dest, "JPEG", quality=90)
    return dest


def set_thumbnail(youtube, video_id: str, image_path: Path):
    from googleapiclient.http import MediaFileUpload
    media = MediaFileUpload(str(image_path), mimetype="image/jpeg", resumable=True)
    youtube.thumbnails().set(videoId=video_id, media_body=media).execute()


def ensure_playlist(youtube, title: str, description: str = "") -> str:
    body = {
        "snippet": {
            "title": title[:150],
            "description": (description or title)[:5000],
        },
        "status": {"privacyStatus": "public"},
    }
    resp = youtube.playlists().insert(part="snippet,status", body=body).execute()
    return resp["id"]


def add_video_to_playlist(youtube, playlist_id: str, video_id: str) -> None:
    youtube.playlistItems().insert(
        part="snippet",
        body={
            "snippet": {
                "playlistId": playlist_id,
                "resourceId": {"kind": "youtube#video", "videoId": video_id},
            }
        },
    ).execute()


def vn_localize(local_dt: datetime, tz_name: str = "Asia/Ho_Chi_Minh"):
    import pytz
    tz = pytz.timezone(tz_name or "Asia/Ho_Chi_Minh")
    if local_dt.tzinfo is None:
        return tz.localize(local_dt)
    return local_dt.astimezone(tz)


def to_rfc3339_utc(local_dt: datetime, tz_name: str) -> str:
    aware = vn_localize(local_dt, tz_name)
    utc = aware.astimezone(__import__("pytz").UTC)
    # gửi kèm offset để Studio hiện đúng giờ VN, không lệch 00:00
    return aware.strftime("%Y-%m-%dT%H:%M:%S%z")


def vn_unix(local_dt: datetime, tz_name: str = "Asia/Ho_Chi_Minh") -> int:
    return int(vn_localize(local_dt, tz_name).timestamp())


class Store:
    def __init__(self):
        self.cfg = load_json(
            CONFIG_FILE,
            {
                "channels": {},
                "active_channel": "",
                "title_tpl": DEFAULT_TITLE,
                "desc_tpl": DEFAULT_DESC,
                "tags": DEFAULT_TAGS,
                "topic": "Truyện ma",
                "category_id": "24",
                "made_for_kids": False,
                "schedule_enabled": True,
                "public_now": False,
                "premiere_on": True,
                "next_publish": "",
                "interval_hours": 24,
                "process_buffer_min": 45,
                "schedule_slots": [],
                "timezone": "Asia/Ho_Chi_Minh",
                "auto_thumb": True,
                "overlay_thumb_text": True,
                "series_priority": True,
                "playlist_enabled": True,
                "playlist_tpl": "{TEN_TRUYEN} | Full tập",
                "batch_n": 3,
            },
        )
        self.uploaded = load_json(UPLOADED_FILE, {})

    def save(self):
        save_json(CONFIG_FILE, self.cfg)
        save_json(UPLOADED_FILE, self.uploaded)

    def used_names(self, ch_id: str) -> set:
        return set(self.uploaded.get(ch_id, []))

    def mark_used(self, ch_id: str, filename: str):
        self.uploaded.setdefault(ch_id, [])
        if filename not in self.uploaded[ch_id]:
            self.uploaded[ch_id].append(filename)
        self.save()


ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("dark-blue")


class LicenseDialog(ctk.CTkToplevel):
    def __init__(self, parent, on_ok):
        super().__init__(parent)
        self.on_ok = on_ok
        self.title(f"{APP_NAME} — Kích hoạt")
        self.geometry("480x480")
        self.resizable(False, False)
        self.configure(fg_color="#12080e")
        self.grab_set()
        apply_window_icon(self)
        self._mid = machine_id()

        try:
            from PIL import Image
            if LOGO_FILE.exists():
                img = Image.open(LOGO_FILE).convert("RGBA")
                # hiện logo to, rõ
                self._logo = ctk.CTkImage(light_image=img, dark_image=img, size=(160, 160))
                ctk.CTkLabel(self, image=self._logo, text="").pack(pady=(18, 6))
        except Exception as e:
            log(f"logo license: {e}")

        ctk.CTkLabel(
            self, text=f"{APP_NAME}  v{APP_VERSION}",
            font=ctk.CTkFont(size=20, weight="bold"), text_color="#ff4da6",
        ).pack(pady=(2, 2))
        ctk.CTkLabel(self, text="Gửi mã máy cho admin để nhận key", text_color="#888").pack()

        mid_row = ctk.CTkFrame(self, fg_color="transparent")
        mid_row.pack(pady=(12, 4))
        ctk.CTkLabel(
            mid_row, text=f"Mã máy:  {self._mid}",
            font=ctk.CTkFont(size=14, weight="bold"), text_color="#ff66cc",
        ).pack(side="left", padx=(0, 8))
        ctk.CTkButton(
            mid_row, text="Copy", width=70, height=28,
            fg_color="#4a148c", hover_color="#6a1b9a",
            command=self._copy_mid,
        ).pack(side="left")

        ctk.CTkLabel(self, text="Nhập key kích hoạt:").pack(pady=(14, 4))
        self.key_var = ctk.StringVar()
        ctk.CTkEntry(self, textvariable=self.key_var, width=320, show="*").pack()
        ctk.CTkButton(
            self, text="Kích hoạt", width=160, height=36, command=self._go,
            fg_color="#c2185b", hover_color="#ad1457",
        ).pack(pady=18)

    def _copy_mid(self):
        try:
            self.clipboard_clear()
            self.clipboard_append(self._mid)
            self.update()
            messagebox.showinfo("Copied", f"Đã copy mã máy:\n{self._mid}", parent=self)
        except Exception as e:
            messagebox.showerror("Lỗi", str(e), parent=self)

    def _go(self):
        k = self.key_var.get().strip()
        if check_license(k):
            save_license(k)
            self.on_ok()
            self.destroy()
        else:
            messagebox.showerror("Key sai", "Key không hợp lệ cho máy này.", parent=self)


class App(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title(f"{APP_NAME} v{APP_VERSION}")
        self.geometry("1120x860")
        self.minsize(980, 740)
        apply_window_icon(self)
        self.store = Store()
        self._busy = False
        self._cancel = False
        self._licensed = False
        self._cfg_lock = threading.Lock()
        self._ui_cid = None
        self._build()
        self.after(100, self._gate_license)

    def _gate_license(self):
        lic = load_json(LICENSE_FILE, {})
        if lic.get("key") and check_license(lic["key"]):
            self._licensed = True
            self.refresh_channels()
            self.after(200, self._check_deps)
            self.after(800, self._resume_after_reboot)
            return
        self.withdraw()

        def ok():
            self._licensed = True
            self.deiconify()
            self.refresh_channels()
            self.after(200, self._check_deps)
            self.after(800, self._resume_after_reboot)

        LicenseDialog(self, ok)

    def _check_deps(self):
        if not yt_available():
            self._log_ui("THIẾU THƯ VIỆN. Chạy BAM_VAO_DAY.bat hoặc:\npip install -r requirements.txt")
        if not CLIENT_SECRET.exists():
            self._log_ui("⚠ Chưa có client_secret.json — xem README.txt")

    def _build(self):
        pad = {"padx": 10, "pady": 6}

        head = ctk.CTkFrame(self, fg_color="#1a0a14")
        head.pack(fill="x", padx=10, pady=(10, 4))
        try:
            from PIL import Image
            if LOGO_FILE.exists():
                img = Image.open(LOGO_FILE).convert("RGBA")
                self._logo_img = ctk.CTkImage(light_image=img, dark_image=img, size=(88, 88))
                ctk.CTkLabel(head, image=self._logo_img, text="").pack(side="left", padx=10, pady=8)
        except Exception:
            pass
        title_box = ctk.CTkFrame(head, fg_color="transparent")
        title_box.pack(side="left", fill="y", pady=8)
        ctk.CTkLabel(title_box, text=APP_NAME,
                     font=ctk.CTkFont(size=22, weight="bold"),
                     text_color="#ff4da6").pack(anchor="w")
        ctk.CTkLabel(title_box, text=f"Auto Upload YouTube  ·  v{APP_VERSION}",
                     text_color="#aaa").pack(anchor="w")
        ctk.CTkButton(head, text="Cập nhật GitHub", width=130, height=32,
                      fg_color="#4a148c", hover_color="#6a1b9a",
                      command=self.on_update).pack(side="right", padx=10, pady=12)
        ctk.CTkLabel(head, text=f"Máy: {machine_id()}",
                     text_color="#666", font=ctk.CTkFont(size=11)).pack(side="right", padx=6)

        top = ctk.CTkFrame(self)
        top.pack(fill="x", **pad)
        ctk.CTkLabel(top, text="Kênh YouTube", font=ctk.CTkFont(size=14, weight="bold")).pack(
            anchor="w", padx=8, pady=(8, 2))
        row = ctk.CTkFrame(top, fg_color="transparent")
        row.pack(fill="x", padx=8, pady=4)
        self.ch_combo = ctk.CTkComboBox(row, values=["(chưa có kênh)"], width=520, command=self.on_channel_pick)
        self.ch_combo.pack(side="left", padx=(0, 8))
        ctk.CTkButton(row, text="Kết nối kênh (OAuth)", width=180, command=self.on_connect).pack(side="left", padx=4)
        ctk.CTkButton(row, text="Xóa kênh", width=100, fg_color="#7a2d2d",
                      command=self.on_remove_channel).pack(side="left", padx=4)

        row2 = ctk.CTkFrame(top, fg_color="transparent")
        row2.pack(fill="x", padx=8, pady=(4, 10))
        ctk.CTkLabel(row2, text="Thư mục video:").pack(side="left")
        self.folder_var = ctk.StringVar(value="")
        ctk.CTkEntry(row2, textvariable=self.folder_var, width=420).pack(side="left", padx=8)
        ctk.CTkButton(row2, text="Chọn thư mục", width=120, command=self.on_pick_folder).pack(side="left")
        ctk.CTkButton(row2, text="Quét file", width=90, command=self.on_scan).pack(side="left", padx=4)

        mid = ctk.CTkFrame(self)
        mid.pack(fill="x", **pad)
        ctk.CTkLabel(mid, text="Form tiêu đề / mô tả  —  dùng {TEN_TRUYEN}",
                     font=ctk.CTkFont(size=14, weight="bold")).pack(anchor="w", padx=8, pady=(8, 2))
        self.title_var = ctk.StringVar(value=self.store.cfg.get("title_tpl", DEFAULT_TITLE))
        ctk.CTkEntry(mid, textvariable=self.title_var).pack(fill="x", padx=8, pady=4)
        self.desc_box = ctk.CTkTextbox(mid, height=100)
        self.desc_box.pack(fill="x", padx=8, pady=4)
        self.desc_box.insert("1.0", self.store.cfg.get("desc_tpl", DEFAULT_DESC))

        tagframe = ctk.CTkFrame(mid, fg_color="transparent")
        tagframe.pack(fill="x", padx=8, pady=(0, 8))
        ctk.CTkLabel(tagframe, text="Chủ đề:").pack(side="left")
        topics = list(TOPIC_TAGS.keys())
        self.topic_var = ctk.StringVar(value=self.store.cfg.get("topic", "Truyện ma"))
        self.topic_combo = ctk.CTkComboBox(tagframe, values=topics, variable=self.topic_var, width=160)
        self.topic_combo.pack(side="left", padx=6)
        ctk.CTkButton(tagframe, text="Random 10 tag", width=120, fg_color="#c2185b",
                      hover_color="#ad1457", command=self.on_random_tags).pack(side="left", padx=4)
        ctk.CTkLabel(tagframe, text="Tags:").pack(side="left", padx=(12, 4))
        self.tags_var = ctk.StringVar(value=self.store.cfg.get("tags", DEFAULT_TAGS))
        ctk.CTkEntry(tagframe, textvariable=self.tags_var).pack(side="left", fill="x", expand=True)

        sch = ctk.CTkFrame(self)
        sch.pack(fill="x", **pad)
        ctk.CTkLabel(sch, text="Hẹn giờ / Thumb / Tập phim",
                     font=ctk.CTkFont(size=14, weight="bold")).pack(anchor="w", padx=8, pady=(8, 2))
        srow = ctk.CTkFrame(sch, fg_color="transparent")
        srow.pack(fill="x", padx=8, pady=4)
        self.sched_on = ctk.CTkCheckBox(srow, text="Hẹn giờ công chiếu")
        self.sched_on.pack(side="left")
        if self.store.cfg.get("schedule_enabled", True):
            self.sched_on.select()
        self.public_now = ctk.CTkCheckBox(srow, text="Công chiếu ngay")
        self.public_now.pack(side="left", padx=(10, 0))
        if self.store.cfg.get("public_now", False):
            self.public_now.select()
        self.premiere_on = ctk.CTkCheckBox(srow, text="Đặt làm video Công chiếu")
        self.premiere_on.pack(side="left", padx=(10, 0))
        if self.store.cfg.get("premiere_on", True):
            self.premiere_on.select()
        self.auto_daily = ctk.CTkCheckBox(srow, text="Tự up mỗi ngày khi tool mở")
        self.auto_daily.pack(side="left", padx=(16, 0))
        if self.store.cfg.get("auto_daily", True):
            self.auto_daily.select()

        slotrow = ctk.CTkFrame(sch, fg_color="transparent")
        slotrow.pack(fill="x", padx=8, pady=(4, 2))
        ctk.CTkLabel(
            slotrow,
            text="Giờ LẶP MỖI NGÀY (12:00 / 21:00 / 22:00). Hôm nay tập 1-2-3, mai 4-5-6 cùng các giờ đó — không trùng mốc đã up.",
        ).pack(anchor="w")
        slbtn = ctk.CTkFrame(slotrow, fg_color="transparent")
        slbtn.pack(fill="x", pady=(2, 2))
        ctk.CTkButton(slbtn, text="Thêm 1 dòng", width=100, command=self._slot_add_one).pack(side="left", padx=(0, 4))
        ctk.CTkButton(slbtn, text="Thêm 5 dòng", width=100, command=self._slot_add_five).pack(side="left", padx=4)
        ctk.CTkButton(slbtn, text="Xóa hết dòng", width=100, fg_color="#7a2d2d",
                      command=self._slot_clear).pack(side="left", padx=4)
        ctk.CTkButton(slbtn, text="Sắp xếp sớm nhất", width=140, fg_color="#2d5a7a",
                      command=self._slot_sort_earliest).pack(side="left", padx=4)
        self.slot_box = ctk.CTkTextbox(slotrow, height=72)
        self.slot_box.pack(fill="x")
        saved_slots = self.store.cfg.get("schedule_slots") or []
        if saved_slots:
            self.slot_box.insert("1.0", "\n".join(self._daily_times_from_lines(saved_slots)))
        self.next_preview = ctk.CTkLabel(slotrow, text="", text_color="#9ad", anchor="w", justify="left")
        self.next_preview.pack(fill="x", pady=(2, 0))
        self.after(200, self._refresh_slot_preview)

        trow = ctk.CTkFrame(sch, fg_color="transparent")
        trow.pack(fill="x", padx=8, pady=(0, 4))
        self.auto_thumb = ctk.CTkCheckBox(trow, text="Tự gắn thumb (cùng tên / +Thumb.jpg)")
        self.auto_thumb.pack(side="left")
        if self.store.cfg.get("auto_thumb", True):
            self.auto_thumb.select()
        self.overlay_thumb = ctk.CTkCheckBox(trow, text="Đè chữ TÊN TRUYỆN lên thumb")
        self.overlay_thumb.pack(side="left", padx=12)
        if self.store.cfg.get("overlay_thumb_text", True):
            self.overlay_thumb.select()
        self.series_on = ctk.CTkCheckBox(trow, text="Ưu tiên tập 1→10 (không random)")
        self.series_on.pack(side="left", padx=12)
        if self.store.cfg.get("series_priority", True):
            self.series_on.select()

        prow = ctk.CTkFrame(sch, fg_color="transparent")
        prow.pack(fill="x", padx=8, pady=(0, 4))
        self.playlist_on = ctk.CTkCheckBox(prow, text="Tạo playlist khi là tập")
        self.playlist_on.pack(side="left")
        if self.store.cfg.get("playlist_enabled", True):
            self.playlist_on.select()
        ctk.CTkLabel(prow, text="  Tên list:").pack(side="left", padx=(10, 4))
        self.playlist_var = ctk.StringVar(
            value=self.store.cfg.get("playlist_tpl", "{TEN_TRUYEN} | Full tập")
        )
        ctk.CTkEntry(prow, textvariable=self.playlist_var, width=280).pack(side="left")

        ctk.CTkLabel(
            sch,
            text="Mỗi dòng = 1 giờ trong ngày (gõ 12:00 rồi thêm dòng 21:00). Tool mở / qua ngày sẽ tự up đúng số mốc. Mất điện: chọn kênh → Tiếp tục.",
            text_color="#888",
        ).pack(anchor="w", padx=8, pady=(0, 8))

        act = ctk.CTkFrame(self)
        act.pack(fill="x", **pad)
        ctk.CTkButton(act, text="Đăng 1 video", height=40, width=140,
                      command=lambda: self.start_job(1)).pack(side="left", padx=8, pady=10)
        ctk.CTkButton(act, text="Up 1 ngày", height=40, width=120,
                      fg_color="#1f6aa5", command=self.start_one_day).pack(side="left", padx=4)
        ctk.CTkButton(act, text="Hàng loạt theo giờ", height=40, width=150,
                      fg_color="#1f6aa5", command=self.start_hang_loat).pack(side="left", padx=8)
        ctk.CTkButton(act, text="Lưu cấu hình", height=40, width=130,
                      fg_color="#3d6b3d", command=self.save_ui).pack(side="left", padx=8)
        self.btn_resume = ctk.CTkButton(
            act, text="Tiếp tục", height=40, width=110,
            fg_color="#8a6d00", hover_color="#6e5600", command=self.resume_pending,
        )
        self.btn_resume.pack(side="left", padx=4)
        self.btn_cancel = ctk.CTkButton(
            act, text="Hủy job", height=40, width=110,
            fg_color="#8b1e1e", hover_color="#6d1616", command=self.cancel_job,
        )
        self.btn_cancel.pack(side="left", padx=8)
        self.status_lbl = ctk.CTkLabel(act, text="Sẵn sàng")
        self.status_lbl.pack(side="left", padx=12)

        bot = ctk.CTkFrame(self, fg_color="#16161c")
        bot.pack(fill="both", expand=True, **pad)
        left = ctk.CTkFrame(bot, fg_color="#1c1c24")
        left.pack(side="left", fill="both", expand=True, padx=(8, 4), pady=8)
        lhead = ctk.CTkFrame(left, fg_color="transparent")
        lhead.pack(fill="x", padx=8, pady=(6, 2))
        ctk.CTkLabel(lhead, text="FILE CHƯA ĐĂNG", font=ctk.CTkFont(size=13, weight="bold"),
                     text_color="#e8c36a").pack(side="left")
        self.file_list = ctk.CTkTextbox(left, height=200, font=ctk.CTkFont(family="Consolas", size=13))
        self.file_list.pack(fill="both", expand=True, padx=8, pady=(0, 8))
        right = ctk.CTkFrame(bot, fg_color="#1c1c24")
        right.pack(side="left", fill="both", expand=True, padx=(4, 8), pady=8)
        rhead = ctk.CTkFrame(right, fg_color="transparent")
        rhead.pack(fill="x", padx=8, pady=(6, 2))
        ctk.CTkLabel(rhead, text="NHẬT KÝ", font=ctk.CTkFont(size=13, weight="bold"),
                     text_color="#7ec8e3").pack(side="left")
        ctk.CTkButton(rhead, text="Xóa log", width=70, height=24, fg_color="#333",
                      command=self._clear_log).pack(side="right")
        self.logbox = ctk.CTkTextbox(right, height=200, font=ctk.CTkFont(family="Consolas", size=13))
        self.logbox.pack(fill="both", expand=True, padx=8, pady=(0, 8))
        self._init_log_tags()

    def _init_log_tags(self):
        try:
            tb = self.logbox._textbox
            tb.configure(bg="#121218", fg="#d8d8e0", insertbackground="#d8d8e0")
            tb.tag_config("ok", foreground="#6ee7a8")
            tb.tag_config("warn", foreground="#f0c14b")
            tb.tag_config("err", foreground="#ff7b7b")
            tb.tag_config("info", foreground="#8ecae6")
            tb.tag_config("go", foreground="#c4b5fd")
            tb.tag_config("time", foreground="#8888a0")
        except Exception:
            pass

    def _log_tag(self, msg: str) -> str:
        s = msg.strip()
        if s.startswith("✓") or " OK " in s or s.startswith("✓"):
            return "ok"
        if s.startswith("⚠") or s.startswith("⏸"):
            return "warn"
        if s.startswith("✗") or s.startswith("⛔") or s.startswith("Lỗi"):
            return "err"
        if s.startswith("→") or s.startswith("▶") or s.startswith("↗"):
            return "go"
        if s.startswith("=== ") or s.startswith("☀") or s.startswith("⏯"):
            return "info"
        return "info"

    def _log_ui(self, msg: str):
        log(msg)
        try:
            stamp = datetime.now().strftime("%H:%M:%S")
            line = f"[{stamp}] {msg}\n"
            tag = self._log_tag(msg)
            tb = getattr(self.logbox, "_textbox", None)
            if tb is not None:
                tb.insert("end", line, tag)
                tb.see("end")
            else:
                self.logbox.insert("end", line)
                self.logbox.see("end")
        except Exception:
            pass

    def _clear_log(self):
        try:
            self.logbox.delete("1.0", "end")
        except Exception:
            pass

    def on_random_tags(self):
        topic = self.topic_var.get()
        tags = random_tags_for_topic(topic, 10)
        self.tags_var.set(tags)
        self._log_ui(f"Random 10 tag chủ đề [{topic}]: {tags}")

    def on_update(self):
        """Kiểm tra GitHub Releases — tải MrOneUPYTB.exe bản mới nếu có."""
        def work():
            try:
                self.after(0, lambda: self._log_ui("Đang kiểm tra GitHub Releases…"))
                req = urllib.request.Request(
                    GITHUB_RELEASES_API,
                    headers={"User-Agent": f"{APP_NAME}/{APP_VERSION}", "Accept": "application/vnd.github+json"},
                )
                with urllib.request.urlopen(req, timeout=20) as r:
                    data = json.loads(r.read().decode())
                tag = (data.get("tag_name") or "").lstrip("vV").strip()
                if not tag:
                    raise RuntimeError("Release chưa có tag_name")
                if tag == APP_VERSION:
                    self.after(0, lambda: messagebox.showinfo("Update", f"Đã là bản mới nhất (v{APP_VERSION})."))
                    self.after(0, lambda: self._log_ui(f"Không có bản mới (v{APP_VERSION})."))
                    return

                # tìm asset .exe
                exe_url = None
                exe_name = f"{APP_NAME}.exe"
                for a in data.get("assets") or []:
                    name = a.get("name") or ""
                    if name.lower().endswith(".exe"):
                        exe_url = a.get("browser_download_url")
                        exe_name = name
                        break
                if not exe_url:
                    self.after(0, lambda: messagebox.showinfo(
                        "Update",
                        f"Có release v{tag} nhưng chưa có file .exe.\n"
                        f"Mở trang Releases để tải tay.",
                    ))
                    import webbrowser
                    webbrowser.open(GITHUB_RELEASES_PAGE)
                    return

                if not messagebox.askyesno(
                    "Update",
                    f"Có bản mới v{tag} (đang dùng v{APP_VERSION}).\n"
                    f"Tải {exe_name} về cạnh tool?",
                ):
                    return

                self.after(0, lambda: self._log_ui(f"Tải {exe_name} v{tag}…"))
                dest = ROOT / exe_name
                tmp = ROOT / (exe_name + ".download")
                urllib.request.urlretrieve(exe_url, tmp)
                # nếu đang chạy chính file exe này thì chỉ tải cạnh với tên mới
                try:
                    if dest.exists():
                        bak = ROOT / f"{APP_NAME}_v{APP_VERSION}.exe.bak"
                        try:
                            dest.replace(bak)
                        except Exception:
                            dest = ROOT / f"{APP_NAME}_v{tag}.exe"
                    tmp.replace(dest)
                except Exception:
                    dest = ROOT / f"{APP_NAME}_v{tag}.exe"
                    tmp.replace(dest)

                self.after(0, lambda d=str(dest): self._log_ui(f"Đã tải: {d}"))
                self.after(0, lambda d=str(dest): messagebox.showinfo(
                    "OK",
                    f"Đã tải bản v{tag}:\n{d}\n\n"
                    "Đóng tool, chạy file .exe mới.\n"
                    "client_secret.json giữ nguyên cạnh exe.",
                ))
            except Exception as e:
                self.after(0, lambda: self._log_ui(f"Update lỗi: {e}"))
                self.after(0, lambda: messagebox.showerror(
                    "Update",
                    f"Không kiểm tra được Releases.\n{e}\n\n"
                    f"Repo: {GITHUB_OWNER}/{GITHUB_REPO}\n"
                    "Tạo Release + đính file MrOneUPYTB.exe.",
                ))

        threading.Thread(target=work, daemon=True).start()

    def current_channel_id(self) -> str | None:
        val = (self.ch_combo.get() or "").strip()
        if not val or val.startswith("(chưa"):
            return None
        # "mail · tên · UCxxxx" hoặc "tên | UCxxxx"
        for sep in (" · ", " ·", "·", "|"):
            if sep in val:
                tail = val.split(sep)[-1].strip()
                if tail.startswith("UC") or len(tail) >= 10:
                    return tail
        # fallback: so khớp với id đã lưu
        chs = self.store.cfg.get("channels", {})
        for cid in chs:
            if cid in val:
                return cid
        return None

    def _channel_label(self, ch_id: str, meta: dict) -> str:
        """mail · tên kênh · UCxxxx — dễ phân biệt nhiều Gmail / nhiều kênh."""
        mail = (meta.get("email") or "").strip() or "?"
        title = meta.get("title") or "?"
        return f"{mail}  ·  {title}  ·  {ch_id}"

    def refresh_channels(self):
        chs = self.store.cfg.get("channels", {})
        labels = [self._channel_label(k, v) for k, v in chs.items()]
        if not labels:
            labels = ["(chưa có kênh)"]
        self.ch_combo.configure(values=labels)
        active = self.store.cfg.get("active_channel")
        pick = None
        for lb in labels:
            if active and active in lb:
                pick = lb
        self.ch_combo.set(pick or labels[0])
        self.on_channel_pick(self.ch_combo.get())

    def on_channel_pick(self, _=None):
        cid = self.current_channel_id()
        if not cid:
            self.folder_var.set("")
            return
        # đổi kênh → lưu kênh cũ trước (bản trên màn hình là mới nhất)
        if self._ui_cid and self._ui_cid != cid:
            try:
                self._apply_ui_to_store(self._ui_cid, silent=True)
            except Exception:
                pass
        self._ui_cid = cid
        ch = self.store.cfg["channels"].get(cid, {})
        self.folder_var.set(ch.get("folder", ""))
        # lịch riêng từng kênh
        self._write_slots(ch.get("schedule_slots") or [])
        if ch.get("used_publish_slots") is not None:
            self.store.cfg["used_publish_slots"] = list(ch.get("used_publish_slots") or [])
        if ch.get("pending_job"):
            self.store.cfg["pending_job"] = dict(ch["pending_job"])
            self.store.cfg["pending_job"]["cid"] = cid
        self._refresh_slot_preview()
        self._refresh_resume_btn()
        if ch.get("title_tpl"):
            self.title_var.set(ch["title_tpl"])
        if ch.get("desc_tpl"):
            self.desc_box.delete("1.0", "end")
            self.desc_box.insert("1.0", ch["desc_tpl"])
        if ch.get("tags"):
            self.tags_var.set(ch["tags"])
        if ch.get("topic"):
            self.topic_var.set(ch["topic"])
        if ch.get("playlist_tpl"):
            self.playlist_var.set(ch["playlist_tpl"])
        self.store.cfg["active_channel"] = cid
        self.on_scan()

    def on_connect(self):
        if not yt_available():
            messagebox.showerror("Lỗi", "Chưa cài thư viện Google. Chạy BAM_VAO_DAY.bat")
            return

        def work():
            try:
                self._log_ui("Mở trình duyệt Google → chọn Gmail → chọn kênh…")
                info = connect_channel()
                chs = self.store.cfg.setdefault("channels", {})
                old = chs.get(info["id"], {})
                chs[info["id"]] = {
                    "title": info["title"],
                    "email": info.get("email") or old.get("email") or "",
                    "token_file": info["token_file"],
                    "folder": old.get("folder", ""),
                }
                self.store.cfg["active_channel"] = info["id"]
                self.store.save()
                self.after(0, self.refresh_channels)
                mail = info.get("email") or "?"
                self.after(0, lambda: self._log_ui(
                    f"Đã kết nối: {mail} · {info['title']} ({info['id']})"
                ))
            except Exception as e:
                self.after(0, lambda: self._log_ui(f"Lỗi kết nối: {e}"))
                self.after(0, lambda: messagebox.showerror("OAuth", str(e)))

        threading.Thread(target=work, daemon=True).start()

    def on_remove_channel(self):
        cid = self.current_channel_id()
        if not cid:
            return
        if not messagebox.askyesno("Xóa", "Xóa kênh khỏi tool?"):
            return
        ch = self.store.cfg["channels"].pop(cid, None)
        if ch and ch.get("token_file"):
            try:
                Path(ch["token_file"]).unlink(missing_ok=True)
            except Exception:
                pass
        self.store.save()
        self.refresh_channels()

    def on_pick_folder(self):
        d = filedialog.askdirectory()
        if not d:
            return
        self.folder_var.set(d)
        cid = self.current_channel_id()
        if cid and cid in self.store.cfg["channels"]:
            self.store.cfg["channels"][cid]["folder"] = d
            self.store.save()
        self.on_scan()

    def pending_files(self, cid: str | None = None) -> list[Path]:
        cid = cid or self.current_channel_id()
        folder = None
        if cid and cid in self.store.cfg.get("channels", {}):
            raw = self.store.cfg["channels"][cid].get("folder") or ""
            if raw:
                folder = Path(raw)
        if folder is None and self.folder_var.get().strip():
            folder = Path(self.folder_var.get().strip())
        if not folder or not folder.is_dir() or not cid:
            return []
        used = self.store.used_names(cid)
        out = []
        for p in sorted(folder.iterdir()):
            if p.is_file() and p.suffix.lower() in VIDEO_EXTS and p.name not in used:
                out.append(p)
        return out

    def pick_next_file(self, pending: list[Path]) -> Path | None:
        if not pending:
            return None
        if not self.store.cfg.get("series_priority", True):
            return random.choice(pending)
        with_ep = []
        no_ep = []
        for p in pending:
            ep = extract_episode(p)
            if ep is not None:
                with_ep.append((ep, p))
            else:
                no_ep.append(p)
        if with_ep:
            with_ep.sort(key=lambda x: x[0])
            return with_ep[0][1]
        return random.choice(no_ep)

    def on_scan(self):
        files = self.pending_files()
        self.file_list.delete("1.0", "end")
        if not files:
            self.file_list.insert("end", "(hết file chưa đăng, hoặc chưa chọn thư mục)\n")
        else:
            for p in files:
                th = find_thumb_for_video(p)
                ep = extract_episode(p)
                ep_m = f"  [tập {ep}]" if ep is not None else ""
                mark = f"  [thumb: {th.name}]" if th else "  [chưa có thumb]"
                self.file_list.insert("end", f"{p.name}{ep_m}{mark}\n")
        mode = "ưu tiên tập" if self.store.cfg.get("series_priority", True) else "random"
        self.status_lbl.configure(text=f"Còn {len(files)} video · mode: {mode}")

    def _daily_times_from_lines(self, slots: list[str] | None) -> list[str]:
        """Lấy các giờ trong ngày (HH:MM), bỏ trùng, sắp sớm → muộn."""
        seen: set[str] = set()
        out: list[tuple[int, str]] = []
        for s in slots or []:
            raw = str(s).strip()
            if not raw:
                continue
            dt = parse_user_datetime(raw)
            if dt:
                key = dt.strftime("%H:%M")
            else:
                m = re.search(r"(\d{1,2})[:hH](\d{2})", raw)
                if not m:
                    continue
                key = f"{int(m.group(1)):02d}:{m.group(2)}"
            if key in seen:
                continue
            seen.add(key)
            hh, mm = key.split(":")
            out.append((int(hh) * 60 + int(mm), key))
        out.sort(key=lambda x: x[0])
        return [k for _, k in out]

    def _normalize_slots(self, slots: list[str] | None, drop_past: bool = False) -> list[str]:
        return self._daily_times_from_lines(slots)

    def _parse_slot_lines(self) -> list[str]:
        raw = self.slot_box.get("1.0", "end").strip()
        lines = [ln.strip() for ln in raw.splitlines() if ln.strip()]
        return self._daily_times_from_lines(lines)

    def _used_slot_set(self) -> set[str]:
        used = set()
        for s in self.store.cfg.get("used_publish_slots") or []:
            dt = parse_user_datetime(str(s))
            if dt:
                used.add(dt.strftime("%Y-%m-%d %H:%M"))
            else:
                used.add(str(s).strip())
        cur = self.store.cfg.get("_slot_in_use")
        if cur:
            used.add(str(cur).strip())
        return used

    def _save_used_slots(self, used: set[str], cid: str | None = None):
        ordered = sorted(used)
        self.store.cfg["used_publish_slots"] = ordered
        cid = cid or self.current_channel_id()
        if cid and cid in self.store.cfg.get("channels", {}):
            self.store.cfg["channels"][cid]["used_publish_slots"] = ordered
        self.store.save()

    def _next_repeating_slots(self, daily: list[str], count: int = 6) -> list[str]:
        """Sinh mốc datetime tiếp theo: lặp giờ mỗi ngày, bỏ mốc đã dùng / đã qua."""
        daily = self._daily_times_from_lines(daily)
        if not daily:
            return []
        used = self._used_slot_set()
        cut = datetime.now() + timedelta(minutes=1)
        out: list[str] = []
        start_day = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
        for d in range(0, 400):
            day = start_day + timedelta(days=d)
            for hhmm in daily:
                hh, mm = hhmm.split(":")
                cand = day.replace(hour=int(hh), minute=int(mm))
                if cand <= cut:
                    continue
                key = cand.strftime("%Y-%m-%d %H:%M")
                if key in used:
                    continue
                out.append(key)
                if len(out) >= count:
                    return out
        return out

    def _refresh_slot_preview(self):
        if not hasattr(self, "next_preview"):
            return
        daily = self._parse_slot_lines()
        nxt = self._next_repeating_slots(daily, 6)
        used_n = len(self._used_slot_set())
        if not daily:
            self.next_preview.configure(text="Chưa có giờ lặp. Ví dụ mỗi dòng: 12:00")
            return
        extra = f"  · đã khóa {used_n} mốc" if used_n else ""
        self.next_preview.configure(
            text="Giờ lặp: " + ", ".join(daily) + extra
            + ("\nMốc kế: " + "  →  ".join(nxt) if nxt else "")
        )

    def _write_slots(self, slots: list[str]):
        slots = self._daily_times_from_lines(slots)
        self.slot_box.delete("1.0", "end")
        if slots:
            self.slot_box.insert("1.0", "\n".join(slots))
        self._refresh_slot_preview()

    def _slot_add_one(self):
        slots = self._parse_slot_lines()
        taken = set(slots)
        if slots:
            last = datetime.strptime(slots[-1], "%H:%M")
            cand = last
            for _ in range(24):
                cand = cand + timedelta(hours=1)
                key = cand.strftime("%H:%M")
                if key not in taken:
                    slots.append(key)
                    break
        else:
            slots.append("12:00")
        self._write_slots(slots)
        self._log_ui("Giờ lặp: " + ", ".join(slots))

    def _slot_add_five(self):
        for _ in range(5):
            self._slot_add_one()

    def _slot_clear(self):
        self.slot_box.delete("1.0", "end")
        self._refresh_slot_preview()

    def _slot_sort_earliest(self):
        self._write_slots(self._parse_slot_lines())
        self._log_ui("Đã sắp giờ lặp trong ngày (sớm → muộn), bỏ trùng.")

    def _persist_pending_job(self, cid: str, remaining: int):
        if remaining <= 0:
            self.store.cfg.pop("pending_job", None)
            if cid and cid in self.store.cfg.get("channels", {}):
                self.store.cfg["channels"][cid].pop("pending_job", None)
        else:
            item = {
                "cid": cid,
                "max_n": remaining,
                "saved_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            }
            self.store.cfg["pending_job"] = item
            if cid and cid in self.store.cfg.get("channels", {}):
                self.store.cfg["channels"][cid]["pending_job"] = dict(item)
        self.store.save()
        self.after(0, self._refresh_resume_btn)

    def _clear_pending_job(self):
        item = self.store.cfg.pop("pending_job", None)
        cid = (item or {}).get("cid") or self.current_channel_id()
        if cid and cid in self.store.cfg.get("channels", {}):
            self.store.cfg["channels"][cid].pop("pending_job", None)
        if item is not None:
            self.store.save()
        self.after(0, self._refresh_resume_btn)

    def _channel_pending(self, cid: str | None = None) -> dict:
        cid = cid or self.current_channel_id()
        if not cid:
            return {}
        ch = self.store.cfg.get("channels", {}).get(cid, {})
        p = ch.get("pending_job") or {}
        g = self.store.cfg.get("pending_job") or {}
        if p.get("max_n"):
            return p
        if g.get("cid") == cid and g.get("max_n"):
            return g
        return {}

    def _refresh_resume_btn(self):
        if not hasattr(self, "btn_resume"):
            return
        p = self._channel_pending()
        n = int(p.get("max_n") or 0)
        if n > 0:
            self.btn_resume.configure(text=f"Tiếp tục ({n})", state="normal")
        else:
            self.btn_resume.configure(text="Tiếp tục", state="normal")

    def resume_pending(self):
        if self._busy:
            messagebox.showinfo("Đang chạy", "Job hiện tại chưa xong.")
            return
        p = self._channel_pending()
        n = int(p.get("max_n") or 0)
        if n <= 0:
            messagebox.showinfo(
                "Tiếp tục",
                "Kênh này không có job dở.\nĐổi kênh nếu bạn up kênh khác lúc mất điện.",
            )
            return
        self._log_ui(f"⏯ Tiếp tục job dở của kênh — còn {n} video")
        self.start_job(n, skip_today_warn=True, parallel=n > 1)

    def _resume_after_reboot(self):
        if not self._licensed:
            return
        self._refresh_resume_btn()
        pending = self.store.cfg.get("pending_job") or {}
        n = int(pending.get("max_n") or 0)
        cid = pending.get("cid")
        if n > 0 and cid in self.store.cfg.get("channels", {}):
            title = self.store.cfg["channels"][cid].get("title", cid)
            self._log_ui(
                f"⚠ Máy vừa mở lại — kênh [{title}] còn job dở ({n} video). "
                "Chọn đúng kênh rồi bấm TIẾP TỤC."
            )
            labels = self.ch_combo.cget("values")
            for lb in labels:
                if cid in str(lb):
                    self.ch_combo.set(lb)
                    break
            self.on_channel_pick()
        self.after(1500, self._tick_auto_daily)

    def _mark_auto_day(self, cid: str):
        today = datetime.now().strftime("%Y-%m-%d")
        self.store.cfg["auto_day_done"] = today
        if cid and cid in self.store.cfg.get("channels", {}):
            self.store.cfg["channels"][cid]["auto_day_done"] = today
        self.store.save()

    def _tick_auto_daily(self):
        self.after(30000, self._tick_auto_daily)
        if self._busy or not self._licensed:
            return
        if hasattr(self, "auto_daily") and not self.auto_daily.get():
            return
        if self._channel_pending():
            return
        cid = self.current_channel_id()
        if not cid:
            return
        ch = self.store.cfg.get("channels", {}).get(cid, {})
        today = datetime.now().strftime("%Y-%m-%d")
        if ch.get("auto_day_done") == today or self.store.cfg.get("auto_day_done") == today:
            return
        if not self.pending_files(cid):
            return
        if not (self.store.cfg.get("schedule_enabled", True) or bool(self.sched_on.get())):
            return
        n = len(self._parse_slot_lines()) or 1
        self._log_ui(f"☀ Ngày mới / vừa bật tool — tự up {n} video theo giờ lặp.")
        self.start_one_day()

    def _apply_ui_to_store(self, cid: str | None = None, silent: bool = False):
        """Màn hình hiện tại = nguồn đúng. Ghi đè kênh, không giữ bản lưu cũ."""
        self.store.cfg["title_tpl"] = self.title_var.get()
        self.store.cfg["desc_tpl"] = self.desc_box.get("1.0", "end").strip()
        self.store.cfg["tags"] = self.tags_var.get()
        self.store.cfg["topic"] = self.topic_var.get()
        self.store.cfg["schedule_enabled"] = bool(self.sched_on.get())
        self.store.cfg["public_now"] = bool(self.public_now.get())
        self.store.cfg["premiere_on"] = bool(self.premiere_on.get())
        self.store.cfg["auto_thumb"] = bool(self.auto_thumb.get())
        self.store.cfg["overlay_thumb_text"] = bool(self.overlay_thumb.get())
        self.store.cfg["series_priority"] = bool(self.series_on.get())
        self.store.cfg["playlist_enabled"] = bool(self.playlist_on.get())
        self.store.cfg["playlist_tpl"] = self.playlist_var.get().strip() or "{TEN_TRUYEN} | Full tập"
        self.store.cfg["auto_daily"] = bool(self.auto_daily.get()) if hasattr(self, "auto_daily") else True
        slots = self._parse_slot_lines()
        self.store.cfg["schedule_slots"] = slots
        self.store.cfg.pop("next_publish", None)
        cid = cid or self.current_channel_id()
        if cid and cid in self.store.cfg.get("channels", {}):
            ch = self.store.cfg["channels"][cid]
            ch["folder"] = self.folder_var.get().strip()
            ch["schedule_slots"] = list(slots)
            ch["used_publish_slots"] = list(self.store.cfg.get("used_publish_slots") or [])
            ch["auto_daily"] = self.store.cfg.get("auto_daily", True)
            ch["title_tpl"] = self.store.cfg.get("title_tpl", "")
            ch["desc_tpl"] = self.store.cfg.get("desc_tpl", "")
            ch["tags"] = self.store.cfg.get("tags", "")
            ch["topic"] = self.store.cfg.get("topic", "")
            ch["playlist_tpl"] = self.store.cfg.get("playlist_tpl", "")
            ch["schedule_enabled"] = self.store.cfg.get("schedule_enabled", True)
            ch["public_now"] = self.store.cfg.get("public_now", False)
            ch["premiere_on"] = self.store.cfg.get("premiere_on", True)
            ch["auto_thumb"] = self.store.cfg.get("auto_thumb", True)
            ch["overlay_thumb_text"] = self.store.cfg.get("overlay_thumb_text", True)
            ch["series_priority"] = self.store.cfg.get("series_priority", True)
            ch["playlist_enabled"] = self.store.cfg.get("playlist_enabled", True)
            ch["saved_at"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            self.store.cfg["active_channel"] = cid
        self.store.save()
        if not silent:
            when = datetime.now().strftime("%H:%M:%S")
            self._log_ui(f"Đã lưu cấu hình kênh lúc {when} — job sau dùng bản này.")

    def save_ui(self):
        self._apply_ui_to_store(silent=False)
        self._write_slots(self.store.cfg.get("schedule_slots") or [])

    def _today_up_count(self) -> int:
        today = datetime.now().strftime("%Y-%m-%d")
        return sum(1 for s in self._used_slot_set() if str(s).startswith(today))

    def start_one_day(self):
        self.start_hang_loat()

    def start_hang_loat(self):
        times = self._parse_slot_lines()
        n = len(times)
        if n <= 0:
            messagebox.showerror(
                "Thiếu giờ",
                "Ghi các giờ lặp, mỗi dòng 1 mốc:\n13:00\n14:00\n15:00\n\n"
                "3 dòng = up SONG SONG 3 video.",
            )
            return
        self._log_ui(
            f"▶ HÀNG LOẠT SONG SONG: {n} mốc ({', '.join(times)}) — up {n} video cùng lúc."
        )
        self.start_job(n, parallel=True)

    def start_job(self, max_n: int, skip_today_warn: bool = False, parallel: bool = False):
        if not self._licensed:
            messagebox.showerror("License", "Chưa kích hoạt key.")
            return
        self._apply_ui_to_store(silent=True)
        cid = self.current_channel_id()
        daily_n = len(self._parse_slot_lines()) or 1
        today_n = self._today_up_count()
        if (not skip_today_warn) and daily_n > 0 and today_n >= daily_n:
            ok = messagebox.askyesno(
                "Hôm nay đã up đủ",
                f"Hôm nay kênh này đã up {today_n} video "
                f"(đúng {daily_n} mốc giờ lặp/ngày).\n\n"
                "Bạn vẫn muốn UP TIẾP?\n"
                "Có = tiếp tục upload + lên lịch + Công chiếu\n"
                "Không = dừng",
            )
            if not ok:
                self._log_ui(
                    f"⏸ Dừng: hôm nay đã up {today_n}/{daily_n}. Bấm Có nếu muốn up thêm."
                )
                return
            self._log_ui(f"▶ Bạn chọn UP TIẾP (hôm nay đã {today_n}/{daily_n}).")
        if self._busy:
            q = self.store.cfg.setdefault("job_queue", [])
            q.append({"cid": cid, "max_n": max_n})
            self.store.save()
            title = self.store.cfg["channels"].get(cid, {}).get("title", cid)
            self._log_ui(f"📌 Đã xếp hàng đợi kênh: {title} (chạy sau job hiện tại)")
            messagebox.showinfo(
                "Hàng đợi",
                f"Job kênh [{title}] đã lưu.\n"
                "Đổi kênh / lên lịch kênh khác rồi bấm chạy để xếp tiếp.\n"
                "App phải MỞ mới upload được. Đóng app = dừng chờ.",
            )
            return
        if not cid:
            messagebox.showerror("Thiếu kênh", "Kết nối / chọn kênh trước.")
            return
        ch = self.store.cfg["channels"][cid]
        if not ch.get("folder") or not Path(ch["folder"]).is_dir():
            messagebox.showerror("Thiếu thư mục", "Chọn thư mục video khớp kênh này.")
            return
        if not Path(ch.get("token_file", "")).exists():
            messagebox.showerror("Token", "Kênh chưa OAuth hoặc token mất. Kết nối lại.")
            return
        self._busy = True
        self._cancel = False
        self._persist_pending_job(cid, max_n)
        self.after(0, lambda: self.status_lbl.configure(text="Đang chạy…"))
        target = self._job_parallel if (parallel and max_n > 1) else self._job
        threading.Thread(target=target, args=(cid, max_n), daemon=True).start()

    def cancel_job(self):
        if not self._busy:
            messagebox.showinfo("Hủy", "Không có job đang chạy.")
            return
        self._cancel = True
        self._apply_ui_to_store(silent=True)
        self._log_ui("⏹ Đã gửi lệnh HỦY — đợi chunk hiện tại xong. Bản cấu hình trên màn hình được giữ cho job sau.")
        self.status_lbl.configure(text="Đang hủy…")

    def _pick_n_files(self, cid: str, n: int) -> list[Path]:
        pending = list(self.pending_files(cid))
        out: list[Path] = []
        taken: set[str] = set()
        for _ in range(n):
            left = [p for p in pending if p.name not in taken]
            pick = self.pick_next_file(left)
            if pick is None:
                break
            out.append(pick)
            taken.add(pick.name)
        return out

    def _lock_n_slots(self, cid: str, n: int) -> list[str]:
        daily = self._daily_times_from_lines(
            self.store.cfg.get("schedule_slots") or self._parse_slot_lines()
        )
        if not daily:
            return []
        slots = self._next_repeating_slots(daily, n)
        locked = self._used_slot_set()
        for s in slots:
            locked.add(s)
        self._save_used_slots(locked, cid)
        return slots

    def _job_parallel(self, cid: str, max_n: int):
        done_holder = {"n": 0}
        try:
            ch = self.store.cfg["channels"][cid]
            self.after(0, lambda: self._log_ui(
                f"=== {APP_NAME} · SONG SONG {max_n} video · {ch.get('title')} ==="
            ))
            files = self._pick_n_files(cid, max_n)
            if not files:
                self.after(0, lambda: self._log_ui("⛔ HẾT video chưa đăng."))
                self._clear_pending_job()
                return
            slots = []
            if self.store.cfg.get("schedule_enabled") and not self.store.cfg.get("public_now"):
                slots = self._lock_n_slots(cid, len(files))
                if len(slots) < len(files):
                    self.after(0, lambda: self._log_ui("⚠ Không đủ mốc giờ trống."))
                    files = files[:len(slots)]
            plan = []
            for i, pick in enumerate(files):
                slot = slots[i] if i < len(slots) else None
                plan.append((pick, slot))
                self.after(0, lambda p=pick.name, s=slot: self._log_ui(
                    f"  ↗ hàng đợi song song: {p}" + (f" → PUBLIC {s}" if s else "")
                ))
            threads = []
            for pick, slot in plan:
                if self._cancel:
                    break
                t = threading.Thread(
                    target=self._upload_one_file,
                    args=(cid, pick, slot, done_holder),
                    daemon=True,
                )
                threads.append(t)
                t.start()
            for t in threads:
                t.join()
            remain = max(0, max_n - done_holder["n"])
            if remain > 0 and not self._cancel:
                self._persist_pending_job(cid, remain)
            else:
                self._clear_pending_job()
                self._mark_auto_day(cid)
            self.after(0, lambda n=done_holder["n"]: self._log_ui(
                f"✓ Xong lô song song: {n} video."
            ))
            self.after(0, self.on_scan)
        except Exception as e:
            tb = traceback.format_exc()
            self.after(0, lambda: self._log_ui(f"Lỗi job song song: {e}\n{tb}"))
        finally:
            self._busy = False
            self.after(0, lambda: self.status_lbl.configure(text="Xong / sẵn sàng"))
            self.after(0, self._refresh_resume_btn)
            self.after(200, self._start_next_queued)

    def _upload_one_file(self, cid: str, pick: Path, slot: str | None, done_holder: dict):
        try:
            if self._cancel:
                if slot:
                    locked = self._used_slot_set()
                    locked.discard(slot)
                    self._save_used_slots(locked, cid)
                return
            ch = self.store.cfg["channels"][cid]
            youtube = youtube_from_token(ch["token_file"])
            ten = story_name_from_file(pick)
            title = self.store.cfg["title_tpl"].replace("{TEN_TRUYEN}", ten)
            desc = self.store.cfg["desc_tpl"].replace("{TEN_TRUYEN}", ten)
            tags = [t.strip() for t in self.store.cfg.get("tags", "").split(",") if t.strip()]
            tags = list(dict.fromkeys(tags + [ten]))
            publish_iso = None
            if slot and not self.store.cfg.get("public_now"):
                local = datetime.strptime(slot, "%Y-%m-%d %H:%M")
                publish_iso = to_rfc3339_utc(local, self.store.cfg.get("timezone", "Asia/Ho_Chi_Minh"))
                self.after(0, lambda t=title, s=slot: self._log_ui(
                    f"→ UPLOAD SONG SONG: {t}\n   YouTube PUBLIC lúc: {s}"
                ))
            resp = upload_video(
                youtube, pick, title, desc, tags,
                self.store.cfg.get("category_id", "24"),
                self.store.cfg.get("made_for_kids", False),
                publish_iso,
                should_cancel=lambda: self._cancel,
                notify_subscribers=bool(
                    self.store.cfg.get("premiere_on", True)
                    or self.store.cfg.get("public_now")
                ),
            )
            vid = resp.get("id", "?")
            if self.store.cfg.get("auto_thumb", True):
                th = find_thumb_for_video(pick)
                if th:
                    try:
                        upload_img = th
                        if self.store.cfg.get("overlay_thumb_text", True):
                            upload_img = overlay_story_on_thumb(th, ten, THUMB_TMP)
                        set_thumbnail(youtube, vid, upload_img)
                    except Exception as te:
                        self.after(0, lambda err=str(te): self._log_ui(f"  ⚠ thumb: {err}"))
            with self._cfg_lock:
                self.store.mark_used(cid, pick.name)
            self.after(0, lambda v=vid, n=pick.name: self._log_ui(
                f"✓ OK youtube.com/watch?v={v}  ({n})"
            ))
            if publish_iso and slot:
                time.sleep(1)
                try:
                    apply_schedule_on_video(
                        youtube, vid, publish_iso,
                        bool(self.store.cfg.get("made_for_kids", False)),
                    )
                    self.after(0, lambda s=slot: self._log_ui(f"  ✓ Lên lịch: {s}"))
                except Exception as se:
                    self.after(0, lambda err=str(se): self._log_ui(f"  ⚠ lịch: {err}"))
                if self.store.cfg.get("premiere_on", True):
                    try:
                        local_dt = datetime.strptime(slot, "%Y-%m-%d %H:%M")
                        studio_set_schedule_premiere(youtube, vid, local_dt, True)
                    except Exception:
                        pass
                    try:
                        apply_schedule_on_video(
                            youtube, vid, publish_iso,
                            bool(self.store.cfg.get("made_for_kids", False)),
                        )
                    except Exception:
                        pass
            if self.store.cfg.get("playlist_enabled", True) and extract_episode(pick) is not None:
                try:
                    pl_title = self.store.cfg.get("playlist_tpl", "{TEN_TRUYEN} | Full tập").replace("{TEN_TRUYEN}", ten)
                    with self._cfg_lock:
                        chs = self.store.cfg.setdefault("channels", {})
                        chm = chs.setdefault(cid, {})
                        maps = chm.setdefault("playlists", {})
                        key = ten.strip().lower()
                        pid = maps.get(key)
                    if not pid:
                        pid = ensure_playlist(youtube, pl_title, f"Full tập: {ten}")
                        with self._cfg_lock:
                            maps[key] = pid
                            self.store.save()
                    add_video_to_playlist(youtube, pid, vid)
                except Exception:
                    pass
            done_holder["n"] = done_holder.get("n", 0) + 1
        except JobCancelled:
            if slot:
                locked = self._used_slot_set()
                locked.discard(slot)
                self._save_used_slots(locked, cid)
        except Exception as e:
            if slot:
                locked = self._used_slot_set()
                locked.discard(slot)
                self._save_used_slots(locked, cid)
            self.after(0, lambda err=str(e): self._log_ui(f"✗ Lỗi {pick.name}: {err}"))

    def _job(self, cid: str, max_n: int):
        done = 0
        try:
            ch = self.store.cfg["channels"][cid]
            self.after(0, lambda: self._log_ui(f"=== {APP_NAME} · kênh: {ch.get('title')} ==="))
            youtube = youtube_from_token(ch["token_file"])
            done = 0
            while done < max_n:
                if self._cancel:
                    self.after(0, lambda: self._log_ui("⏹ Đã hủy job. Không đăng video tiếp."))
                    break
                pending = self.pending_files(cid)
                if not pending:
                    self.after(0, lambda: self._log_ui("⛔ HẾT video chưa đăng. Tạm dừng."))
                    self.after(0, lambda: messagebox.showwarning("HẾT", "Hết truyện trong thư mục kênh này."))
                    self._clear_pending_job()
                    break
                pick = self.pick_next_file(pending)
                if pick is None:
                    break
                ten = story_name_from_file(pick)
                title = self.store.cfg["title_tpl"].replace("{TEN_TRUYEN}", ten)
                desc = self.store.cfg["desc_tpl"].replace("{TEN_TRUYEN}", ten)
                tags = [t.strip() for t in self.store.cfg.get("tags", "").split(",") if t.strip()]
                tags = list(dict.fromkeys(tags + [ten]))

                publish_iso = None
                if self.store.cfg.get("public_now"):
                    self.after(0, lambda t=title: self._log_ui(f"→ Upload CÔNG CHIẾU NGAY: {t}"))
                elif self.store.cfg.get("schedule_enabled"):
                    daily = self._daily_times_from_lines(
                        self.store.cfg.get("schedule_slots") or self._parse_slot_lines()
                    )
                    if not daily:
                        self.after(0, lambda: self._log_ui(
                            "  ⚠ chưa có giờ lặp. Ghi mỗi dòng một giờ, ví dụ: 12:00"
                        ))
                        self.after(0, lambda: messagebox.showerror(
                            "Thiếu giờ",
                            "Điền giờ lặp mỗi ngày, mỗi dòng 1 giờ:\n12:00\n21:00\n22:00",
                        ))
                        break
                    self.store.cfg["schedule_slots"] = daily
                    nxt_list = self._next_repeating_slots(daily, 1)
                    if not nxt_list:
                        self.after(0, lambda: self._log_ui("  ⚠ hết mốc lịch hợp lệ (400 ngày)."))
                        self.after(0, lambda: messagebox.showerror("Lịch", "Không còn mốc giờ trống."))
                        break
                    used = nxt_list[0]
                    locked = self._used_slot_set()
                    locked.add(used)
                    self.store.cfg["_slot_in_use"] = used
                    self._save_used_slots(locked, cid)
                    self.after(0, self._refresh_slot_preview)
                    local = datetime.strptime(used, "%Y-%m-%d %H:%M")
                    publish_iso = to_rfc3339_utc(local, self.store.cfg.get("timezone", "Asia/Ho_Chi_Minh"))
                    self.after(0, lambda t=title, pub=used: self._log_ui(
                        f"→ UPLOAD NGAY: {t}\n   YouTube tự PUBLIC lúc: {pub}"
                    ))
                else:
                    self.after(0, lambda t=title: self._log_ui(f"→ Upload public ngay: {t}"))

                try:
                    resp = upload_video(
                        youtube, pick, title, desc, tags,
                        self.store.cfg.get("category_id", "24"),
                        self.store.cfg.get("made_for_kids", False),
                        publish_iso,
                        should_cancel=lambda: self._cancel,
                        notify_subscribers=bool(
                            self.store.cfg.get("premiere_on", True)
                            or self.store.cfg.get("public_now")
                        ),
                    )
                    vid = resp.get("id", "?")
                    if self.store.cfg.get("auto_thumb", True):
                        th = find_thumb_for_video(pick)
                        if th:
                            try:
                                upload_img = th
                                if self.store.cfg.get("overlay_thumb_text", True):
                                    upload_img = overlay_story_on_thumb(th, ten, THUMB_TMP)
                                    self.after(0, lambda: self._log_ui("  đã đè chữ tên truyện lên thumb"))
                                set_thumbnail(youtube, vid, upload_img)
                                self.after(0, lambda n=th.name: self._log_ui(f"  ✓ gắn thumb {n}"))
                            except Exception as te:
                                self.after(0, lambda err=str(te): self._log_ui(f"  ⚠ gắn thumb lỗi: {err}"))
                        else:
                            self.after(0, lambda: self._log_ui("  ⚠ không thấy file thumb cùng tên"))
                    self.store.mark_used(cid, pick.name)
                    self.after(0, lambda v=vid, n=pick.name: self._log_ui(f"✓ OK youtube.com/watch?v={v}  ({n})"))
                    if publish_iso and not self.store.cfg.get("public_now"):
                        used_slot = self.store.cfg.get("_slot_in_use") or ""
                        local_dt = datetime.strptime(used_slot, "%Y-%m-%d %H:%M") if used_slot else None
                        time.sleep(2)
                        try:
                            apply_schedule_on_video(
                                youtube, vid, publish_iso,
                                bool(self.store.cfg.get("made_for_kids", False)),
                            )
                            self.after(0, lambda s=used_slot: self._log_ui(
                                f"  ✓ Lên lịch Studio (Data API): {s} (giờ VN)"
                            ))
                        except Exception as se:
                            self.after(0, lambda err=str(se): self._log_ui(
                                f"  ⚠ Gắn lịch Data API: {err}"
                            ))
                        if local_dt is not None and self.store.cfg.get("premiere_on", True):
                            try:
                                studio_set_schedule_premiere(youtube, vid, local_dt, True)
                                self.after(0, lambda: self._log_ui(
                                    "  ✓ Đã gửi Studio: Lên lịch + Công chiếu"
                                ))
                            except Exception as ste:
                                self.after(0, lambda err=str(ste): self._log_ui(
                                    "  ⚠ Studio chưa tick được ô Công chiếu (cần cookie Studio, "
                                    "OAuth không mở nút này). " + err
                                ))
                            # Studio đôi khi ghi đè giờ thành 00:00 — gắn lại giờ VN
                            try:
                                apply_schedule_on_video(
                                    youtube, vid, publish_iso,
                                    bool(self.store.cfg.get("made_for_kids", False)),
                                )
                            except Exception:
                                pass
                            try:
                                setup_premiere_event(youtube, vid, title, desc, publish_iso)
                            except Exception:
                                pass
                    # playlist cho video có số tập
                    if self.store.cfg.get("playlist_enabled", True) and extract_episode(pick) is not None:
                        try:
                            pl_title = self.store.cfg.get("playlist_tpl", "{TEN_TRUYEN} | Full tập").replace("{TEN_TRUYEN}", ten)
                            chs = self.store.cfg.setdefault("channels", {})
                            chm = chs.setdefault(cid, {})
                            maps = chm.setdefault("playlists", {})
                            key = ten.strip().lower()
                            pid = maps.get(key)
                            if not pid:
                                pid = ensure_playlist(youtube, pl_title, f"Full tập: {ten}")
                                maps[key] = pid
                                self.store.save()
                                self.after(0, lambda t=pl_title, i=pid: self._log_ui(f"  ✓ tạo playlist: {t} ({i})"))
                            add_video_to_playlist(youtube, pid, vid)
                            self.after(0, lambda: self._log_ui("  ✓ đã thêm video vào playlist"))
                        except Exception as pe:
                            self.after(0, lambda err=str(pe): self._log_ui(f"  ⚠ playlist: {err}"))
                    if self.store.cfg.get("schedule_enabled"):
                        self.store.cfg.pop("_slot_in_use", None)
                        self.store.save()
                        self.after(0, self._refresh_slot_preview)
                    done += 1
                    remain = max_n - done
                    if remain > 0:
                        self._persist_pending_job(cid, remain)
                    else:
                        self._clear_pending_job()
                    self.after(0, self.on_scan)
                except JobCancelled:
                    used = self.store.cfg.pop("_slot_in_use", None)
                    if used:
                        locked = self._used_slot_set()
                        locked.discard(used)
                        self._save_used_slots(locked, cid)
                        self.after(0, self._refresh_slot_preview)
                    self.after(0, lambda: self._log_ui("⏹ Đã hủy giữa lúc upload. Video này có thể chưa lên YouTube."))
                    break
                except Exception as e:
                    used = self.store.cfg.pop("_slot_in_use", None)
                    if used:
                        locked = self._used_slot_set()
                        locked.discard(used)
                        self._save_used_slots(locked, cid)
                        self.after(0, self._refresh_slot_preview)
                    self.after(0, lambda err=str(e): self._log_ui(f"✗ Lỗi upload {pick.name}: {err}"))
                    # không dừng cả lô — thử video kế
                    done += 1
                    remain = max_n - done
                    if remain > 0:
                        self._persist_pending_job(cid, remain)
                    continue
        except Exception as e:
            tb = traceback.format_exc()
            self.after(0, lambda: self._log_ui(f"Lỗi job: {e}\n{tb}"))
        finally:
            self._busy = False
            if self._cancel:
                pass
            elif done >= max_n or done > 0:
                if done >= max_n:
                    self._clear_pending_job()
                    self._mark_auto_day(cid)
            elif pending := (self.store.cfg.get("pending_job") or {}):
                if int(pending.get("max_n") or 0) <= 0:
                    self._clear_pending_job()
            self.after(0, lambda: self.status_lbl.configure(text="Xong / sẵn sàng"))
            self.after(0, self._refresh_resume_btn)
            self.after(200, self._start_next_queued)

    def _start_next_queued(self):
        if self._busy:
            return
        q = self.store.cfg.get("job_queue") or []
        if not q:
            return
        item = q.pop(0)
        self.store.cfg["job_queue"] = q
        self.store.save()
        cid = item.get("cid")
        max_n = int(item.get("max_n") or 999)
        if not cid or cid not in self.store.cfg.get("channels", {}):
            self._start_next_queued()
            return
        # nạp lịch kênh đó rồi chạy
        labels = self.ch_combo.cget("values")
        for lb in labels:
            if cid in str(lb):
                self.ch_combo.set(lb)
                break
        self.on_channel_pick()
        self._log_ui(f"▶ Lấy job hàng đợi: {self.store.cfg['channels'][cid].get('title')}")
        self.start_job(max_n)


if __name__ == "__main__":
    import sys
    # Admin: tạo key gắn máy — python app.py --genkey <MA_MAY>
    if len(sys.argv) >= 3 and sys.argv[1] == "--genkey":
        mid = sys.argv[2].strip().upper()
        print(make_machine_key(mid))
        sys.exit(0)
    App().mainloop()
