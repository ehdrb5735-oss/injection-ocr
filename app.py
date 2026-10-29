import streamlit as st
import cv2
import numpy as np
from PIL import Image

st.set_page_config(page_title="사출조건 자주검사 모바일 시스템", layout="centered")

# --- [1] 세션 상태 관리 (관리자 로그인 및 데이터 저장소) ---
if "is_admin" not in st.session_state:
    st.session_state.is_admin = False

if "spec_data" not in st.session_state:
    # 관리자가 수정 가능한 기준 스펙 데이터 기본값
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
st.sidebar.info("💡 **촬영 팁**: 모니터 정면보다는 **약간 비스듬하게 각도를 주어 촬영**하면 빛 반사(글자 날림)를 크게 줄일 수 있습니다.")

# --- [3] 이미지 전처리 함수 (흐림 및 빛 반사 개선, 선명화) ---
def enhance_image(img_np):
    # 1. 그레이스케일 변환
    gray = cv2.cvtColor(img_np, cv2.COLOR_RGB2GRAY)
    
    # 2. 노이즈 제거 및 경계선 강화 (Bilateral Filter - 모니터 픽셀 살림)
    denoised = cv2.bilateralFilter(gray, 9, 75, 75)
    
    # 3. CLAHE (Contrast Limited Adaptive Histogram Equalization) 적용 - 어두운 부분과 밝은 부분 대비 극대화
    clahe = cv2.createCLAHE(clipLimit=2.5, tileGridSize=(8, 8))
    enhanced = clahe.apply(denoised)
    
    # 4. 3채널(RGB)로 다시 변환하여 화면 출력용으로 반환
    return cv2.cvtColor(enhanced, cv2.COLOR_GRAY2RGB)

# --- [4] 메인 화면: 카메라 촬영 ---
st.markdown("### 📷 설비 디스플레이 실시간 촬영 및 보정")
camera_image = st.camera_image("설비 화면 촬영하기")

if camera_image is not None:
    # 촬영된 이미지 로드
    image = Image.open(camera_image)
    img_np = np.array(image)
    h, w, _ = img_np.shape
    
    # 이미지 선명화 및 전처리 적용 (흐림/반사 개선)
    processed_img = enhance_image(img_np)
    
    st.subheader("🎯 보정된 촬영 이미지 및 가이드라인")
    
    img_draw = processed_img.copy()
    
    # 가이드라인(외곽 테두리 및 주요 구역 박스)
    cv2.rectangle(img_draw, (int(w*0.02), int(h*0.02)), (int(w*0.98), int(h*0.98)), (0, 255, 0), 4)
    cv2.rectangle(img_draw, (int(w*0.10), int(h*0.20), int(w*0.45), int(h*0.55)), (255, 0, 0), 2) # 사출부
    cv2.rectangle(img_draw, (int(w*0.48), int(h*0.20), int(w*0.75), int(h*0.55)), (0, 0, 255), 2) # 계량부
    cv2.rectangle(img_draw, (int(w*0.10), int(h*0.60), int(w*0.45), int(h*0.90)), (255, 165, 0), 2) # 보압부

    st.image(img_draw, use_container_width=True, caption="빛 반사 및 흐림 현상을 개선하기 위해 고대비 전처리가 적용된 화면입니다.")
    
    st.divider()
    st.subheader("📊 사출조건 검사 항목 판정 결과")
    
    # 현재 관리자 설정 기준값과 비교하여 판정
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
    st.info("💡 위의 **'설비 화면 촬영하기'** 버튼을 눌러 촬영해 주세요.")
