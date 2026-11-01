
import streamlit as st

st.title("해커톤 프로젝트 1조")

st.write("AI 서비스 개발환경 테스트")

name = st.text_input("이름을 입력하세요")

if st.button("확인"):
    if name:
        st.success(f"{name}님, 환영합니다!")
    else:
        st.warning("이름을 입력해주세요.")
