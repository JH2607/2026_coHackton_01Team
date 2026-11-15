
"""김밥(GIMBAP) Streamlit 서비스 실행 파일"""

from pathlib import Path
import runpy

ui_path = Path(__file__).with_name("ui.py")

runpy.run_path(str(ui_path), run_name="__main__")
