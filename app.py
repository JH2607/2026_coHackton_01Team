
import streamlit as st

"""김밥 서비스 실행 파일"""
import ui

name = st.text_input("이름을 입력하세요")

if st.button("확인"):
    if name:
        st.success(f"{name}님, 환영합니다!")
    else:
        st.warning("이름을 입력해주세요.")
