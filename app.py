"""김밥(GIMBAP) Streamlit 서비스 실행 파일"""

import importlib
import runpy
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ui_path = HERE / "ui.py"

# Streamlit Cloud는 GitHub에 새 코드가 올라오면 ui.py는 다시 실행하지만,
# ui.py가 import한 파일(ui_style, user_store 등)은 예전 버전을 메모리에 그대로 둘 때가 있다.
# (→ "module has no attribute ..." AttributeError) 파일이 바뀐 경우에만 의존 순서대로 다시 읽는다.
_LOCAL_MODULES = [
    "ui_style", "user_store", "data_service", "db_tools", "kakao_service",
    "kakao_verifier", "route_service", "ai_service", "ai_chat_agent",
    "map_view", "chat_view",
]
_mtimes = sys.__dict__.setdefault("_gimbap_module_mtimes", {})


def _mtime(name: str) -> float:
    try:
        return (HERE / f"{name}.py").stat().st_mtime
    except OSError:
        return 0.0


# 기록이 없을 때(이 app.py가 처음 실행될 때)도 이미 올라간 모듈은 한 번 다시 읽는다.
_changed = any(
    name in sys.modules and _mtimes.get(name) != _mtime(name)
    for name in _LOCAL_MODULES
)
for name in _LOCAL_MODULES:
    if _changed and name in sys.modules:
        try:
            importlib.reload(sys.modules[name])
        except Exception:
            pass
    _mtimes[name] = _mtime(name)

runpy.run_path(str(ui_path), run_name="__main__")
