import streamlit as st
import cv2
import numpy as np
from PIL import Image

st.set_page_config(page_title="사출조건 자주검사 모바일 시스템", layout="centered")

# --- [1] 세션 상태 관리 (관리자 로그인 여부) ---
if "is_admin" not in st.session_state:
    st.session_state.is_admin = False

st.title("📸 사출조건 자주검사 카메라 촬영 앱")

# --- [2] 사이드바: 관리자 인증 및 안내 ---
st.sidebar.header("🔐 시스템 관리")
if not st.session_state.is_admin:
    admin_pw = st.sidebar.text_input("관리자 비밀번호 입력", type="password")
    if st.sidebar.button("관리자 로그인"):
        if admin_pw == "admin1234":
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
st.sidebar.info("💡 **촬영 가이드**: 아래 카메라 버튼을 눌러 설비 HMI 화면을 촬영하세요. 화면의 초록색 테두리에 모니터를 맞추면 오차가 줄어듭니다.")

# --- [3] 메인 화면: 무조건 카메라 촬영만 지원 (파일 업로드 제거) ---
st.markdown("### 📷 설비 디스플레이 실시간 촬영")
st.write("스마트폰 카메라로 설비 화면을 촬영해 주세요.")

# Streamlit 내장 카메라 캡처 기능 (모바일 기기에서 바로 카메라 구동)
camera_image = st.camera_image("설비 화면 촬영하기")

if camera_image is not None:
    # 촬영된 이미지 읽기
    image = Image.open(camera_image)
    img_np = np.array(image)
    h, w, _ = img_np.shape
    
    st.subheader("🎯 촬영된 이미지 및 가이드라인(ROI) 적용")
    
    img_draw = img_np.copy()
    
    # 1) 전체 화면 맞춤 가이드라인 (외곽 녹색 테두리)
    cv2.rectangle(img_draw, (int(w*0.02), int(h*0.02)), (int(w*0.98), int(h*0.98)), (0, 255, 0), 4)
    
    # 2) 주요 세부 영역 ROI 박스들 (사출·계량·보압 파트, 온도 제외)
    cv2.rectangle(img_draw, (int(w*0.10), int(h*0.20), int(w*0.45), int(h*0.55)), (255, 0, 0), 2) # 사출부
    cv2.rectangle(img_draw, (int(w*0.48), int(h*0.20), int(w*0.75), int(h*0.55)), (0, 0, 255), 2) # 계량부
    cv2.rectangle(img_draw, (int(w*0.10), int(h*0.60), int(w*0.45), int(h*0.90)), (255, 165, 0), 2) # 보압부

    st.image(img_draw, use_container_width=True, caption="초록색 외곽 가이드라인 영역에 맞춰 촬영된 결과입니다.")
    
    st.divider()
    st.subheader("📊 일괄 OCR 인식 결과 (온도 제외)")
    
    # 추출 데이터 시뮬레이션
    extracted_data = [
        {"구분": "사출 1차", "항목": "압력 / 속도 / 위치", "인식값": "110 Bar / 80 mm/s / 45 mm", "판정": "정상"},
        {"구분": "사출 2차", "항목": "압력 / 속도 / 위치", "인식값": "105 Bar / 70 mm/s / 30 mm", "판정": "정상"},
        {"구분": "계량 1차", "항목": "속도 / 배압 / 위치", "인식값": "40 RPM / 5 Bar / 30 mm", "판정": "정상"},
        {"구분": "보압 1차", "항목": "압력 / 시간 / 속도", "인식값": "50 Bar / 0.8 sec / 45 %", "판정": "정상"},
        {"구분": "기타 조건", "항목": "사출최대압력 / 냉각시간", "인식값": "105 Bar / 15 sec", "판정": "정상"}
    ]
    
    for item in extracted_data:
        st.write(f"• **[{item['구분']}]** {item['항목']} ➔ **{item['인식값']}** ({item['판정']})")

    # --- [4] 관리자 권한 제어 ---
    st.divider()
    if st.session_state.is_admin:
        st.success("👑 [관리자 권한] 아래 버튼을 눌러 인식된 데이터를 구글 스프레드시트에 최종 전송할 수 있습니다.")
        if st.button("📤 구글 스프레드시트 최종 반영", type="primary"):
            st.success("데이터가 구글 스프레드시트 대시보드에 성공적으로 기록되었습니다!")
    else:
        st.warning("🔒 일반 작업자 모드입니다. 데이터 전송은 **관리자 로그인** 후에만 가능합니다.")
else:
    st.info("💡 위의 **'설비 화면 촬영하기'** 버튼을 눌러 카메라를 켜고 설비 디스플레이를 촬영해 주세요.")
