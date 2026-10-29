import streamlit as st
import google.generativeai as genai
from PIL import Image
import pandas as pd
import io

# 페이지 기본 설정 (가장 처음에 위치해야 함)
st.set_page_config(
    page_title="작업일지 OCR 자동화",
    page_icon="📄",
    layout="wide"
)

# 타이틀
st.title("📄 작업일지 OCR 및 엑셀 변환 시스템")
st.write("수기 작업일지 사진을 업로드하면 AI가 텍스트를 추출하여 데이터로 변환합니다.")

# 사이드바 설정 (API 키 입력 등)
st.sidebar.header("설정")
api_key = st.sidebar.text_input("Gemini API Key", type="password")

if not api_key:
    st.warning("⚠️ 사이드바에 Google Gemini API Key를 입력해주세요.")
else:
    genai.configure(api_key=api_key)
    
    # 파일 업로더
    uploaded_file = st.file_uploader("작업일지 이미지를 선택하세요 (PNG, JPG)", type=["png", "jpg", "jpeg"])
    
    if uploaded_file is not None:
        image = Image.open(uploaded_file)
        st.image(image, caption="업로드된 작업일지", use_container_width=True)
        
        if st.button("🚀 OCR 분석 실행", type="primary"):
            with st.spinner("AI가 작업일지를 분석 중입니다..."):
                try:
                    # 모델 설정 (Gemini Flash 등 활용)
                    model = genai.GenerativeModel('gemini-2.5-flash')
                    
                    prompt = "이 작업일지 이미지의 내용을 분석해서 주요 항목과 텍스트를 마크다운 표 형태로 정리해줘."
                    response = model.generate_content([image, prompt])
                    
                    st.success("✅ 분석 완료!")
                    st.markdown(response.text)
                    
                except Exception as e:
                    st.error(f"분석 중 오류가 발생했습니다: {e}")
