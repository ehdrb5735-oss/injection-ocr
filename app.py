import streamlit as st
import google.generativeai as genai
from PIL import Image
import pandas as pd
import json

# 페이지 설정
st.set_page_config(
    page_title="작업일지 및 검사 OCR 자동화 시스템",
    page_icon="📋",
    layout="wide"
)

# 세션 상태 초기화 (데이터 유지용)
if "admin_mode" not in st.session_state:
    st.session_state.admin_mode = False
if "reference_image" not in st.session_state:
    st.session_state.reference_image = None
if "inspection_points" not in st.session_state:
    st.session_state.inspection_points = []
if "ocr_results" not in st.session_state:
    st.session_state.ocr_results = {}
if "api_key" not in st.session_state:
    st.session_state.api_key = ""

# --- 사이드바 설정 (API 키 및 모드 전환) ---
st.sidebar.header("⚙️ 시스템 설정")
api_key_input = st.sidebar.text_input("Gemini API Key", type="password", value=st.session_state.api_key)
if api_key_input:
    st.session_state.api_key = api_key_input
    genai.configure(api_key=api_key)

st.sidebar.divider()

# 1. 관리자 로그인 / 모드 전환 섹션
st.sidebar.subheader("🔒 시스템 모드")
admin_password = st.sidebar.text_input("관리자 비밀번호 입력", type="password")

# 간단한 관리자 인증 (비밀번호: admin123 또는 원하는 값으로 변경 가능)
if admin_password == "admin123":
    st.session_state.admin_mode = True
    st.sidebar.success("관리자 모드 활성화됨")
else:
    if admin_password != "":
        st.sidebar.error("비밀번호가 틀렸습니다.")
    st.session_state.admin_mode = False

# 메인 화면 타이틀
st.title("📋 지그/부품 검사 및 작업일지 OCR 시스템")

# --- [요구사항 1] 관리자 기능: 기준 사진 첨부 및 포인트 지정 ---
if st.session_state.admin_mode:
    st.info("💡 **[관리자 모드]** 기준 사진을 등록하고 검사할 포인트 영역을 설정합니다.")
    
    col_a, col_b = st.columns(2)
    with col_a:
        ref_file = st.file_uploader("기준 사진(템플릿) 업로드", type=["png", "jpg", "jpeg"], key="ref_uploader")
        if ref_file:
            st.session_state.reference_image = Image.open(ref_file)
            st.image(st.session_state.reference_image, caption="등록된 기준 사진", use_container_width=True)
            
    with col_b:
        st.subheader("📍 포인트별 위치 및 항목 지정")
        st.write("인식할 항목 이름과 대략적인 위치(예: 좌측 상단, 치수부 등)를 정의합니다.")
        
        point_name = st.text_input("포인트/항목 이름 (예: 홀 치수, 외관 불량 등)")
        if st.button("포인트 추가"):
            if point_name:
                st.session_state.inspection_points.append(point_name)
                st.success(f"포인트 '{point_name}' 추가됨")
            else:
                st.warning("항목 이름을 입력하세요.")
                
        if st.session_state.inspection_points:
            st.write("현재 등록된 검사 포인트 목록:")
            for idx, pt in enumerate(st.session_state.inspection_points):
                st.write(f"{idx+1}. {pt}")
            if st.button("포인트 초기화"):
                st.session_state.inspection_points = []
                st.rerun()

    st.divider()

# --- [요구사항 2, 3, 4] 일반 작업자 영역 (로그인 불필요) ---
st.subheader("🔍 작업자 검사 및 데이터 입력 화면")
st.write("로그인 없이 사진을 업로드하면 AI가 분석을 수행하며, 우측에서 값을 직접 수정할 수 있습니다.")

if not st.session_state.api_key:
    st.warning("⚠️ 사이드바에 Google Gemini API Key를 먼저 입력해주세요.")
else:
    # 2. 사진 첨부 및 데이터 읽기
    uploaded_worker_file = st.file_uploader("검사할 작업일지 또는 부품 사진 업로드", type=["png", "jpg", "jpeg"], key="worker_uploader")
    
    if uploaded_worker_file is not None:
        worker_image = Image.open(uploaded_worker_file)
        
        col1, col2 = st.columns(2)
        
        with col1:
            st.image(worker_image, caption="업로드된 검사 사진", use_container_width=True)
            run_ocr = st.button("🚀 데이터 자동 읽기 (OCR)", type="primary")
            
        with col2:
            st.subheader("✏️ 데이터 확인 및 수정 (우측)")
            st.write("AI가 추출한 값을 확인하고 잘못된 부분을 직접 수정하세요.")
            
            # OCR 실행 로직
            if run_ocr:
                with st.spinner("AI가 사진을 분석하고 있습니다..."):
                    try:
                        model = genai.GenerativeModel('gemini-2.5-flash')
                        
                        # 관리자가 지정한 포인트가 있다면 함께 반영하여 프롬프트 구성
                        points_guide = f"중점적으로 읽어야 할 포인트 목록: {st.session_state.inspection_points}" if st.session_state.inspection_points else ""
                        
                        prompt = f"""
                        제공된 이미지는 작업일지 또는 부품 검사 사진입니다. 
                        이미지 안의 텍스트, 수치, 체크 항목들을 분석하여 JSON 형식으로 추출해 주세요.
                        {points_guide}
                        반드시 아래의 키-값(Key-Value) 구조 형태의 JSON만 출력해 주세요. 다른 설명은 적지 마세요.
                        예시: {{"항목1": "값1", "항목2": "값2"}}
                        """
                        
                        response = model.generate_content([worker_image, prompt])
                        text_res = response.text.strip()
                        
                        # JSON 파싱 시도
                        if "```json" in text_res:
                            text_res = text_res.split("```json")[1].split("```")[0].strip()
                        elif "```" in text_res:
                            text_res = text_res.split("```")[1].split("```")[0].strip()
                            
                        parsed_data = json.loads(text_res)
                        st.session_state.ocr_results = parsed_data
                        st.success("✅ 데이터 읽기 완료!")
                    except Exception as e:
                        st.error(f"데이터 분석 중 오류 발생: {e}")
                        # 기본 빈 폼 제공
                        st.session_state.ocr_results = {"결과항목1": "입력필요", "결과항목2": "입력필요"}

            # [요구사항 3] 데이터 수정 입력 폼 생성
            edited_data = {}
            if st.session_state.ocr_results:
                with st.form("edit_form"):
                    st.write("--- **데이터 수정 필드** ---")
                    for key, val in st.session_state.ocr_results.items():
                        edited_data[key] = st.text_input(label=key, value=str(val))
                    
                    submit_form = st.form_submit_button("💾 수정사항 반영")
                    if submit_form:
                        st.session_state.ocr_results = edited_data
                        st.success("수정 사항이 임시 반영되었습니다.")
            else:
                st.info("좌측의 '데이터 자동 읽기' 버튼을 눌러주세요.")

        st.divider()
        
        # [요구사항 4] 스프레드시트 전송 버튼
        st.subheader("📤 스프레드시트 전송")
        st.write("최종 확인된 데이터를 구글 스프레드시트로 전송합니다.")
        
        if st.button("✈️ 구글 스프레드시트로 전송하기", type="primary"):
            if st.session_state.ocr_results:
                # 여기에 구글 스프레드시트 연동 코드 (gspread 또는 웹훅 API 등) 구현 가능
                # 현재는 시뮬레이션 및 데이터 다운로드 기능 제공
                df_to_send = pd.DataFrame([st.session_state.ocr_results])
                
                st.success("🎉 데이터가 구글 스프레드시트로 성공적으로 전송되었습니다! (시뮬레이션)")
                st.dataframe(df_to_send)
                
                # 추가로 엑셀 다운로드도 병행 제공
                csv = df_to_send.to_csv(index=False).encode('utf-8-sig')
                st.download_button(
                    label="📥 엑셀(CSV) 파일로도 백업 다운로드",
                    data=csv,
                    file_name="inspection_data.csv",
                    mime="text/csv",
                )
            else:
                st.warning("전송할 데이터가 없습니다.")
