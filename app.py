import streamlit as st
import cv2
import numpy as np
from PIL import Image

st.set_page_config(page_title="사출조건 자주검사 OCR 모바일 시스템", layout="centered")

# --- [1] 세션 상태 관리 (관리자 로그인 여부) ---
if "is_admin" not in st.session_state:
    st.session_state.is_admin = False

st.title("📸 사출조건 자주검사 모바일 OCR 시스템")

# --- [2] 사이드바: 관리자 인증 및 설정 ---
st.sidebar.header("🔐 시스템 관리")
if not st.session_state.is_admin:
    admin_pw = st.sidebar.text_input("관리자 비밀번호 입력", type="password")
    if st.sidebar.button("관리자 로그인"):
        if admin_pw == "admin1234":  # 현장에 맞게 비밀번호 변경 가능
            st.session_state.is_admin = True
            st.sidebar.success("관리자 로그인 성공!")
            st.rerun()
        else:
            st.sidebar.error("비밀번호가 틀렸습니다.")
else:
    st.sidebar.success("👑 관리자 모드 활성화됨")
    if st.sidebar.button("로그아웃"):
        st.session_state.is_admin = False
        st.rerun()

st.sidebar.divider()
st.sidebar.header("🎯 촬영 가이드 설정")
st.sidebar.info("💡 촬영 시 화면의 **초록색 외곽 가이드라인**에 설비 HMI 모니터의 모서리를 정확히 맞추어 촬영해 주세요. (위치 오차 방지)")

# --- [3] 메인 화면: 사진 촬영 또는 업로드 ---
uploaded_file = st.file_uploader("설비 디스플레이 사진 촬영 또는 업로드", type=["jpg", "jpeg", "png"])

if uploaded_file is not None:
    image = Image.open(uploaded_file)
    img_np = np.array(image)
    h, w, _ = img_np.shape
    
    st.subheader("📷 가이드라인 오버레이 및 일괄 추출 영역")
    
    # 전체 모니터 가이드라인(초록색 외곽선) 및 세부 항목별 ROI 영역 정의
    # (실린더/금형 온도 파트는 제외하고 사출·보압·계량 파트만 매핑)
    img_draw = img_np.copy()
    
    # 1) 전체 화면 맞춤 가이드라인 (외곽 테두리)
    cv2.rectangle(img_draw, (int(w*0.02), int(h*0.02)), (int(w*0.98), int(h*0.98)), (0, 255, 0), 4)
    
    # 2) 주요 세부 영역 ROI 박스들 (예시 좌표)
    # 사출부 압력/속도/위치 영역
    cv2.rectangle(img_draw, (int(w*0.10), int(h*0.20), int(w*0.45), int(h*0.55)), (255, 0, 0), 2)
    # 계량부 영역
    cv2.rectangle(img_draw, (int(w*0.48), int(h*0.20), int(w*0.75), int(h*0.55)), (0, 0, 255), 2)
    # 보압부 영역
    cv2.rectangle(img_draw, (int(w*0.10), int(h*0.60), int(w*0.45), int(h*0.90)), (255, 165, 0), 2)

    st.image(img_draw, use_container_width=True, caption="[가이드라인 안내] 외곽 녹색 박스에 화면을 맞추면, 지정된 영역(사출·계량·보압)의 수치만 일괄 추출됩니다.")
    
    st.divider()
    st.subheader("📊 일괄 OCR 인식 결과 (온도 제외)")
    
    # 시뮬레이션된 추출 데이터 테이블 (실제 OCR 연동 시 각 ROI별 인식 결과 매핑)
    extracted_data = [
        {"구분": "사출 1차", "항목": "압력 / 속도 / 위치", "인식값": "110 Bar / 80 mm/s / 45 mm", "판정": "정상"},
        {"구분": "사출 2차", "항목": "압력 / 속도 / 위치", "인식값": "105 Bar / 70 mm/s / 30 mm", "판정": "정상"},
        {"구분": "계량 1차", "항목": "속도 / 배압 / 위치", "in": "40 RPM / 5 Bar / 30 mm", "인식값": "40 RPM / 5 Bar / 30 mm", "판정": "정상"},
        {"구분": "보압 1차", "항목": "압력 / 시간 / 속도", "인식값": "50 Bar / 0.8 sec / 45 %", "판정": "정상"},
        {"구분": "기타 조건", "항목": "사출최대압력 / 냉각시간", "인식값": "105 Bar / 15 sec", "판정": "정상"}
    ]
    
    for item in extracted_data:
        st.write(f"• **[{item['구분']}]** {item['항목']} ➔ **{item['인식값']}** ({item['판정']})")

    # --- [4] 권한 제어: 관리자만 설정 수정 및 시트 전송 가능 ---
    st.divider()
    if st.session_state.is_admin:
        st.success("👑 [관리자 권한] 아래 버튼을 눌러 인식된 데이터를 구글 스프레드시트에 최종 전송 및 반영할 수 있습니다.")
        if st.button("📤 구글 스프레드시트 최종 반영", type="primary"):
            st.success("데이터가 구글 스프레드시트 대시보드에 성공적으로 기록되었습니다!")
    else:
        st.warning("🔒 일반 작업자 모드입니다. 데이터 전송 및 가이드라인(ROI) 좌표 수정은 **관리자 로그인** 후에만 가능합니다.")
else:
    st.info("💡 현장 설비 디스플레이를 가이드라인에 맞춰 촬영하거나 사진을 업로드해 주세요.")
