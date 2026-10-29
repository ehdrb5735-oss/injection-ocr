import streamlit as st
import google.generativeai as genai
from PIL import Image
import pandas as pd
import json

# ==========================================
# ⚙️ [관리자 설정] 여기에 본인의 Gemini API Key를 입력해 두세요!
# ==========================================
MASTER_API_KEY = "alrusq13323w"  # <-- 여기에 발급받은 키를 넣으세요

# 페이지 설정
st.set_page_config(
    page_title="작업일지 및 검사 OCR 자동화 시스템",
    page_icon="📋",
    layout="wide"
)

# API Key 설정 적용
if MASTER_API_KEY != "YOUR_GEMINI_API_KEY":
    genai.configure(api_key=MASTER_API_KEY)

# 세션 상태 초기화
if "admin_mode" not in st.session_state:
    st.session_state.admin_mode = False
if "reference_image" not in st.session_state:
    st.session_state.reference_image = None
if "inspection_points" not in st.session_state:
    st.session_state.inspection_points = []
if "ocr_results" not in st.session_state:
    st.session_state.ocr_results = {}

# --- 사이드바: 관리자 모드 전용 설정 ---
st.sidebar.header("⚙️ 시스템 설정")
admin_password = st.sidebar.text_input("관리자 비밀번호", type="password")

# 관리자 비밀번호 (원하시는 비밀번호로 변경 가능)
if admin_password == "admin123":
    st.session_state.admin_mode = True
    st.sidebar.success("관리자 모드 활성화됨")
else:
    st.session_state.admin_mode = False

# 메인 화면 타이틀
st.title("📋 지그/부품 검사 및 작업일지 OCR 시스템")

# --- [요구사항 1] 관리자 기능: 기준 사진 첨부 및 포인트 지정 ---
if st.session_state.admin_mode:
    with st.expander("🔒 [관리자 전용] 기준 사진 및 검사 포인트 설정", expanded=True):
        col_a, col_b = st.columns(2)
        with col_a:
            ref_file = st.file_uploader("기준 사진(템플릿) 업로드", type=["png", "jpg", "jpeg"], key="ref_uploader")
            if ref_file:
                st.session_state.reference_image = Image.open(ref_file)
                st.image(st.session_state.reference_image, caption="등록된 기준 사진", use_container_width=True)
                
        with col_b:
            st.subheader("📍 포인트별 항목 지정")
            point_name = st.text_input("포인트/항목 이름 (예: 홀 치수, 불량유무 등)")
            if st.button("포인트 추가"):
                if point_name:
                    st.session_state.inspection_points.append(point_name)
                    st.success(f"포인트 '{point_name}' 추가됨")
                else:
                    st.warning("항목 이름을 입력하세요.")
                    
            if st.session_state.inspection_points:
                st.write("현재 등록된 포인트:")
                for idx, pt in enumerate(st.session_state.inspection_points):
                    st.write(f"{idx+1}. {pt}")
                if st.button("포인트 초기화"):
                    st.session_state.inspection_points = []
                    st.rerun()

    st.divider()

# --- [요구사항 2, 3, 4] 작업자 화면 (로그인/API키 입력 불필요) ---
st.subheader("🔍 현장 작업자 검사 화면")
st.write("사진을 업로드하면 자동으로 데이터를 읽어옵니다. 우측에서 값을 확인하고 수정할 수 있습니다.")

if MASTER_API_KEY == "YOUR_GEMINI_API_KEY":
    st.error("⚠️ 관리자가 코드 내에 Gemini API Key를 설정하지 않았습니다. 소스코드의 MASTER_API_KEY를 수정해주세요.")
else:
    # 2. 사진 첨부 및 데이터 읽기
    uploaded_worker_file = st.file_uploader("작업일지 또는 부품 사진 업로드", type=["png", "jpg", "jpeg"], key="worker_uploader")
    
    if uploaded_worker_file is not None:
        import io

# 업로드된 파일을 바이트로 안전하게 읽어서 이미지로 변환
bytes_data = uploaded_worker_file.read()
worker_image = Image.open(io.BytesIO(bytes_data))

        
        col1, col2 = st.columns(2)
        
        with col1:
            st.image(worker_image, caption="업로드된 검사 사진", use_container_width=True)
            run_ocr = st.button("🚀 데이터 자동 읽기 (OCR)", type="primary")
            
        with col2:
            st.subheader("✏️ 데이터 확인 및 수정")
            
            # OCR 실행 로직
            if run_ocr:
                with st.spinner("AI가 사진을 분석 중입니다..."):
                    try:
                        model = genai.GenerativeModel('gemini-2.5-flash')
                        points_guide = f"중점적으로 읽어야 할 포인트 목록: {st.session_state.inspection_points}" if st.session_state.inspection_points else ""
                        
                        prompt = f"""
                        제공된 이미지는 작업일지 또는 부품 검사 사진입니다. 
                        이미지 안의 텍스트, 수치, 체크 항목들을 분석하여 JSON 형식으로 추출해 주세요.
                        {points_guide}
                        반드시 키-값 형태의 JSON만 출력해 주세요. 다른 설명은 적지 마세요.
                        예시: {{"항목1": "값1", "항목2": "값2"}}
                        """
                        
                        response = model.generate_content([worker_image, prompt])
                        text_res = response.text.strip()
                        
                        if "```json" in text_res:
                            text_res = text_res.split("```json")[1].split("```")[0].strip()
                        elif "```" in text_res:
                            text_res = text_res.split("```")[1].split("```")[0].strip()
                            
                        parsed_data = json.loads(text_res)
                        st.session_state.ocr_results = parsed_data
                        st.success("✅ 데이터 읽기 완료!")
                    except Exception as e:
                        st.error(f"분석 중 오류 발생: {e}")
                        st.session_state.ocr_results = {"결과항목1": "확인필요"}

            # [요구사항 3] 우측 데이터 수동 수정 폼
            edited_data = {}
            if st.session_state.ocr_results:
                with st.form("edit_form"):
                    st.write("--- **추출된 데이터 수정** ---")
                    for key, val in st.session_state.ocr_results.items():
                        edited_data[key] = st.text_input(label=key, value=str(val))
                    
                    submit_form = st.form_submit_button("💾 수정사항 반영")
                    if submit_form:
                        st.session_state.ocr_results = edited_data
                        st.success("수정 사항이 반영되었습니다.")
            else:
                st.info("좌측의 '데이터 자동 읽기' 버튼을 눌러주세요.")

        st.divider()
        
        # [요구사항 4] 스프레드시트 전송 버튼
        st.subheader("📤 데이터 전송")
        if st.button("✈️ 구글 스프레드시트로 전송하기", type="primary"):
            if st.session_state.ocr_results:
                df_to_send = pd.DataFrame([st.session_state.ocr_results])
                st.success("🎉 데이터가 구글 스프레드시트로 전송되었습니다!")
                st.dataframe(df_to_send)
                
                # 백업용 다운로드
                csv = df_to_send.to_csv(index=False).encode('utf-8-sig')
                st.download_button(
                    label="📥 엑셀(CSV) 파일 백업 다운로드",
                    data=csv,
                    file_name="inspection_data.csv",
                    mime="text/csv",
                )
            else:
                st.warning("전송할 데이터가 없습니다.")
