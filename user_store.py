"""회원 · 여행 사물함 · 찜(하트) · 공유 정보를 저장하는 파일 (해커톤 데모용).

- 저장 위치: 이 폴더 안의 user_data/ (JSON 파일 + 사진). .gitignore에 넣어서 GitHub에는 올라가지 않는다.
  → 각자 컴퓨터에서 가입한 계정과 여행은 그 컴퓨터에만 있다.
- 비밀번호는 그대로 저장하지 않고, 되돌릴 수 없는 해시(hash) 값으로 바꿔서 저장한다.
- 오류가 있으면 문자열(화면에 보여줄 메시지)을, 성공하면 None을 돌려준다.

여행(trip) 하나의 모양
{
  "trip_id": "t_1a2b3c4d",
  "owner": "juhyeong",                      # 만든 사람
  "title": "성수 11.11~11.13",             # 사물함에 보이는 이름 (주인이 바꿀 수 있음)
  "notes": "",                              # 나의 소감 (주인만 보고 고칠 수 있음)
  "photo": null,                            # user_data/photos/ 안의 파일 이름
  "conditions": {"region", "start_date", "end_date", "categories"},
  "favorites": {"juhyeong": ["P001"], "friend01": ["P010"]},   # 사람별 찜
  "shared_with": ["friend01"],
  "created_at", "updated_at"
}
"""

import hashlib
import hmac
import json
import os
import re
import secrets
from datetime import date, datetime
from pathlib import Path

STORE_DIR = Path(__file__).parent / "user_data"
USERS_PATH = STORE_DIR / "users.json"
TRIPS_PATH = STORE_DIR / "trips.json"
PHOTO_DIR = STORE_DIR / "photos"

ID_PATTERN = re.compile(r"^[A-Za-z0-9_]{3,20}$")
MIN_PASSWORD_LEN = 4
PHOTO_TYPES = {".png", ".jpg", ".jpeg", ".webp"}
MAX_PHOTO_BYTES = 5 * 1024 * 1024  # 사진 한 장 5MB까지


def _now() -> str:
    return datetime.now().isoformat(timespec="seconds")


def _read(path: Path, default):
    if not path.exists():
        return default
    with open(path, encoding="utf-8") as file:
        return json.load(file)


def _write(path: Path, data) -> None:
    STORE_DIR.mkdir(exist_ok=True)
    temp = path.with_suffix(".tmp")
    with open(temp, "w", encoding="utf-8") as file:
        json.dump(data, file, ensure_ascii=False, indent=2)
    os.replace(temp, path)  # 다 쓴 다음 한 번에 바꿔치기 → 쓰다가 멈춰도 파일이 깨지지 않음


def _hash_password(password: str, salt_hex: str) -> str:
    return hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), bytes.fromhex(salt_hex), 100_000).hex()


# ---------------------------------------------------------------------
# 회원가입 / 로그인
# ---------------------------------------------------------------------
def create_user(user_id: str, password: str, agreed: bool) -> str | None:
    user_id = user_id.strip()
    if not ID_PATTERN.match(user_id):
        return "아이디는 영문·숫자·밑줄(_)로 3~20자로 만들어 주세요."
    if len(password) < MIN_PASSWORD_LEN:
        return f"비밀번호는 {MIN_PASSWORD_LEN}자 이상이어야 해요."
    if not agreed:
        return "약관(개인정보 수집·이용)에 동의해야 가입할 수 있어요."

    users = _read(USERS_PATH, {})
    if user_id in users:
        return "이미 사용 중인 아이디예요."

    salt = secrets.token_hex(16)
    users[user_id] = {"salt": salt, "password_hash": _hash_password(password, salt), "created_at": _now()}
    _write(USERS_PATH, users)
    return None


def check_login(user_id: str, password: str) -> bool:
    user = _read(USERS_PATH, {}).get(user_id.strip())
    if user is None:
        return False
    return hmac.compare_digest(user["password_hash"], _hash_password(password, user["salt"]))


def user_exists(user_id: str) -> bool:
    return user_id.strip() in _read(USERS_PATH, {})


# ---------------------------------------------------------------------
# 여행 사물함
# ---------------------------------------------------------------------
def auto_title(conditions: dict) -> str:
    """목적지 + 날짜로 기본 이름 만들기. 예: '성수 11.11~11.13'"""
    start = date.fromisoformat(conditions["start_date"])
    end = date.fromisoformat(conditions["end_date"])
    days = f"{start:%m.%d}" if start == end else f"{start:%m.%d}~{end:%m.%d}"
    return f"{conditions['region']} {days}"


def _find(trips: list, trip_id: str) -> dict | None:
    return next((t for t in trips if t["trip_id"] == trip_id), None)


def save_trip(owner: str, conditions: dict) -> str:
    """[확인]을 누를 때 호출. 같은 목적지·날짜의 여행이 이미 있으면 새로 만들지 않고 그 여행을 갱신한다."""
    trips = _read(TRIPS_PATH, [])
    for trip in trips:
        same = trip["conditions"]
        if (trip["owner"] == owner and same["region"] == conditions["region"]
                and same["start_date"] == conditions["start_date"] and same["end_date"] == conditions["end_date"]):
            trip["conditions"] = conditions
            trip["updated_at"] = _now()
            _write(TRIPS_PATH, trips)
            return trip["trip_id"]

    trip_id = "t_" + secrets.token_hex(4)
    trips.append({
        "trip_id": trip_id,
        "owner": owner,
        "title": auto_title(conditions),
        "notes": "",
        "photo": None,
        "conditions": conditions,
        "favorites": {},
        "shared_with": [],
        "created_at": _now(),
        "updated_at": _now(),
    })
    _write(TRIPS_PATH, trips)
    return trip_id


def get_trip(trip_id: str) -> dict | None:
    return _find(_read(TRIPS_PATH, []), trip_id)


def can_view(trip: dict, user_id: str) -> bool:
    return trip["owner"] == user_id or user_id in trip["shared_with"]


def list_trips_for(user_id: str) -> list[dict]:
    """내가 만든 여행 + 나에게 공유된 여행 (최근에 바뀐 순서)."""
    trips = [t for t in _read(TRIPS_PATH, []) if can_view(t, user_id)]
    return sorted(trips, key=lambda t: t["updated_at"], reverse=True)


def update_trip_info(trip_id: str, user_id: str, title: str, notes: str) -> str | None:
    trips = _read(TRIPS_PATH, [])
    trip = _find(trips, trip_id)
    if trip is None or trip["owner"] != user_id:
        return "이 여행은 만든 사람만 고칠 수 있어요."
    title = title.strip()
    if not title:
        return "여행 이름을 입력해 주세요."
    trip["title"] = title[:40]
    trip["notes"] = notes.strip()[:1000]
    trip["updated_at"] = _now()
    _write(TRIPS_PATH, trips)
    return None


def set_trip_photo(trip_id: str, user_id: str, filename: str, data: bytes) -> str | None:
    ext = Path(filename).suffix.lower()
    if ext not in PHOTO_TYPES:
        return "사진은 png, jpg, webp 파일만 올릴 수 있어요."
    if len(data) > MAX_PHOTO_BYTES:
        return "사진이 너무 커요. 5MB 이하로 올려 주세요."

    trips = _read(TRIPS_PATH, [])
    trip = _find(trips, trip_id)
    if trip is None or trip["owner"] != user_id:
        return "이 여행은 만든 사람만 고칠 수 있어요."

    PHOTO_DIR.mkdir(parents=True, exist_ok=True)
    if trip["photo"]:
        (PHOTO_DIR / trip["photo"]).unlink(missing_ok=True)  # 예전 사진은 지워서 공간 절약
    photo_name = f"{trip_id}{ext}"
    (PHOTO_DIR / photo_name).write_bytes(data)
    trip["photo"] = photo_name
    trip["updated_at"] = _now()
    _write(TRIPS_PATH, trips)
    return None


def photo_path(trip: dict) -> Path | None:
    if not trip.get("photo"):
        return None
    path = PHOTO_DIR / trip["photo"]
    return path if path.exists() else None


# ---------------------------------------------------------------------
# 찜(하트) — 여행마다, 사람마다 따로 저장
# ---------------------------------------------------------------------
def toggle_favorite(trip_id: str, user_id: str, place_id: str) -> None:
    trips = _read(TRIPS_PATH, [])
    trip = _find(trips, trip_id)
    if trip is None or not can_view(trip, user_id):
        return
    mine = trip["favorites"].setdefault(user_id, [])
    if place_id in mine:
        mine.remove(place_id)
    else:
        mine.append(place_id)
    _write(TRIPS_PATH, trips)


# ---------------------------------------------------------------------
# 동행에게 공유
# ---------------------------------------------------------------------
def share_trip(trip_id: str, from_user: str, to_user: str) -> str | None:
    to_user = to_user.strip()
    if not to_user:
        return "공유할 사용자 ID를 입력해 주세요."
    if to_user == from_user:
        return "내 아이디에는 공유할 수 없어요."
    if not user_exists(to_user):
        return f"'{to_user}' 아이디를 찾을 수 없어요."

    trips = _read(TRIPS_PATH, [])
    trip = _find(trips, trip_id)
    if trip is None or trip["owner"] != from_user:
        return "이 여행은 만든 사람만 공유할 수 있어요."
    if to_user in trip["shared_with"]:
        return f"이미 {to_user}님과 공유한 여행이에요."

    trip["shared_with"].append(to_user)
    trip["updated_at"] = _now()
    _write(TRIPS_PATH, trips)
    return None
