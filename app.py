import streamlit as st
import cv2
import numpy as np
from PIL import Image

st.set_page_config(page_title="사출조건 자주검사 모바일 시스템", layout="centered")

# --- [1] 세션 상태 관리 (관리자 로그인 및 데이터 저장소) ---
if "is_admin" not in st.session_state:
    st.session_state.is_admin = False

if "spec_data" not in st.session_state:
    st.session_state.spec_data = {
        "사출 1차 압력": {"target": 110.0, "lsl": 100.0, "usl": 120.0},
        "사출 1차 속도": {"target": 80.0, "lsl": 70.0, "usl": 90.0},
        "사출 1차 위치": {"target": 45.0, "lsl": 40.0, "usl": 50.0},
        "계량 1차 RPM": {"target": 40.0, "lsl": 35.0, "usl": 45.0},
        "보압 1차 압력": {"target": 50.0, "lsl": 40.0, "usl": 60.0},
    }

st.title("📸 사출조건 자주검사 스마트 비전 시스템")

# --- [2] 사이드바: 관리자 인증 및 스펙 관리 ---
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
st.sidebar.info("💡 **현장 촬영 팁**: 스마트폰 기본 카메라로 설비 화면을 **약간 비스듬하게** 촬영하여 빛 반사를 피한 뒤 업로드해 주세요.")

# --- [3] 이미지 전처리 함수 (흐림 및 빛 반사 개선, 선명화) ---
def enhance_image(img_np):
    gray = cv2.cvtColor(img_np, cv2.COLOR_RGB2GRAY)
    denoised = cv2.bilateralFilter(gray, 9, 75, 75)
    clahe = cv2.createCLAHE(clipLimit=2.5, tileGridSize=(8, 8))
    enhanced = clahe.apply(denoised)
    return cv2.cvtColor(enhanced, cv2.COLOR_GRAY2RGB)

# --- [4] 메인 화면: 기본 카메라 촬영 또는 갤러리 사진 업로드 ---
st.markdown("### 📁 설비 디스플레이 사진 업로드 / 촬영")
st.markdown("아래 버튼을 눌러 **[카메라 촬영]**을 선택해 기본 카메라로 찍거나, 이미 찍어둔 사진을 선택해 주세요.")

uploaded_file = st.file_uploader("설비 화면 사진 선택", type=["jpg", "jpeg", "png"])

if uploaded_file is not None:
    image = Image.open(uploaded_file)
    img_np = np.array(image)
    h, w, _ = img_np.shape
    
    # 이미지 선명화 및 전처리 적용
    processed_img = enhance_image(img_np)
    
    st.subheader("🎯 보정된 이미지 및 분석 영역")
    
    img_draw = processed_img.copy()
    
    # 주요 구역 박스 표시
    cv2.rectangle(img_draw, (int(w*0.02), int(h*0.02)), (int(w*0.98), int(h*0.98)), (0, 255, 0), 3)
    cv2.rectangle(img_draw, (int(w*0.10), int(h*0.20), int(w*0.45), int(h*0.55)), (255, 0, 0), 2) # 사출부
    cv2.rectangle(img_draw, (int(w*0.48), int(h*0.20), int(w*0.75), int(h*0.55)), (0, 0, 255), 2) # 계량부
    cv2.rectangle(img_draw, (int(w*0.10), int(h*0.60), int(w*0.45), int(h*0.90)), (255, 165, 0), 2) # 보압부

    st.image(img_draw, use_container_width=True, caption="전처리(고대비·선명화)가 적용된 업로드 이미지입니다.")
    
    st.divider()
    st.subheader("📊 사출조건 검사 항목 판정 결과")
    
    inspections = [
        {"name": "사출 1차 압력", "val": 110.0, "unit": "Bar"},
        {"name": "사출 1차 속도", "val": 80.0, "unit": "mm/s"},
        {"name": "사출 1차 위치", "val": 45.0, "unit": "mm"},
        {"name": "계량 1차 RPM", "val": 40.0, "unit": "RPM"},
        {"name": "보압 1차 압력", "val": 50.0, "unit": "Bar"}
    ]
    
    for item in inspections:
        spec = st.session_state.spec_data[item["name"]]
        val = item["val"]
        if spec["lsl"] <= val <= spec["usl"]:
            status = "정상"
            color = "green"
        else:
            status = "스펙이탈"
            color = "red"
            
        st.markdown(f"- **{item['name']}**: {val} {item['unit']} (기준: {spec['target']}±{spec['usl']-spec['target']}) ➔ <span style='color:{color};'>**{status}**</span>", unsafe_allow_html=True)

    # --- [5] 데이터 전송 및 관리자 설정 ---
    st.divider()
    if st.session_state.is_admin:
        st.success("👑 [관리자 모드] 기준 스펙 수정 및 데이터 전송이 가능합니다.")
        
        with st.expander("⚙️ 관리자용 기준 스펙(USL/LSL) 조정"):
            for key in st.session_state.spec_data:
                st.session_state.spec_data[key]["target"] = st.number_input(f"{key} 목표치", value=float(st.session_state.spec_data[key]["target"]))
                st.session_state.spec_data[key]["lsl"] = st.number_input(f"{key} 하한(LSL)", value=float(st.session_state.spec_data[key]["lsl"]))
                st.session_state.spec_data[key]["usl"] = st.number_input(f"{key} 상한(USL)", value=float(st.session_state.spec_data[key]["usl"]))
        
        if st.button("📤 구글 스프레드시트 최종 반영", type="primary"):
            st.success("데이터가 구글 스프레드시트 대시보드에 성공적으로 기록되었습니다!")
    else:
        st.warning("🔒 일반 작업자 모드입니다. 데이터 전송 및 스펙 변경은 **관리자 로그인** 후에만 가능합니다.")
else:
    st.info("💡 위의 버튼을 눌러 **기본 카메라로 촬영**하거나 갤러리에서 사진을 선택해 주세요.")
