"""회원 · 찜(하트) · 공유 정보를 저장하는 파일 (해커톤 데모용).

- 저장 위치: 이 폴더 안의 user_data/ (JSON 파일). .gitignore에 넣어서 GitHub에는 올라가지 않는다.
  → 각자 컴퓨터에서 가입한 계정은 그 컴퓨터에만 있다.
- 비밀번호는 그대로 저장하지 않고, 되돌릴 수 없는 해시(hash) 값으로 바꿔서 저장한다.
- 오류가 있으면 문자열(화면에 보여줄 메시지)을, 성공하면 None을 돌려준다.
"""

import hashlib
import hmac
import json
import os
import re
import secrets
from datetime import datetime
from pathlib import Path

STORE_DIR = Path(__file__).parent / "user_data"
USERS_PATH = STORE_DIR / "users.json"
SHARES_PATH = STORE_DIR / "shares.json"

ID_PATTERN = re.compile(r"^[A-Za-z0-9_]{3,20}$")
MIN_PASSWORD_LEN = 4


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
    users[user_id] = {
        "salt": salt,
        "password_hash": _hash_password(password, salt),
        "favorites": [],
        "created_at": _now(),
    }
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
# 찜(하트) — 찜한 리스트 화면은 나중에 만들 예정, 지금은 저장만
# ---------------------------------------------------------------------
def get_favorites(user_id: str) -> set[str]:
    user = _read(USERS_PATH, {}).get(user_id, {})
    return set(user.get("favorites", []))


def toggle_favorite(user_id: str, place_id: str) -> None:
    users = _read(USERS_PATH, {})
    if user_id not in users:
        return
    favorites = users[user_id].setdefault("favorites", [])
    if place_id in favorites:
        favorites.remove(place_id)
    else:
        favorites.append(place_id)
    _write(USERS_PATH, users)


# ---------------------------------------------------------------------
# 동행에게 공유
# ---------------------------------------------------------------------
def share_trip(from_user: str, to_user: str, trip: dict, place_ids: list[str]) -> str | None:
    to_user = to_user.strip()
    if not to_user:
        return "공유할 사용자 ID를 입력해 주세요."
    if to_user == from_user:
        return "내 아이디에는 공유할 수 없어요."
    if not user_exists(to_user):
        return f"'{to_user}' 아이디를 찾을 수 없어요."
    if not place_ids:
        return "공유할 추천 장소가 없어요."

    shares = _read(SHARES_PATH, [])
    shares.append({
        "from": from_user,
        "to": to_user,
        "trip": trip,
        "place_ids": place_ids,
        "created_at": _now(),
    })
    _write(SHARES_PATH, shares)
    return None


def get_shares_for(user_id: str) -> list[dict]:
    """나에게 공유된 여행 (최신순)."""
    shares = [s for s in _read(SHARES_PATH, []) if s["to"] == user_id]
    return sorted(shares, key=lambda s: s["created_at"], reverse=True)
