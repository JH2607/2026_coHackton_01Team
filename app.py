"""김밥 서비스 실행 파일:  streamlit run app.py

'import ui'만 쓰면 첫 화면만 나오고, 버튼을 누르거나 다른 사람이 접속하면 화면이 비어 버림
(파이썬은 같은 모듈을 한 번만 실행하기 때문). 그래서 실행할 때마다 ui.main()을 부른다.
"""
import ui

ui.main()
