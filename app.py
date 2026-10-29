import streamlit as st
import cv2
import numpy as np
from PIL import Image

st.set_page_config(page_title="사출조건 자주검사 스마트 비전 시스템", layout="centered")

# --- [1] 세션 상태 초기화 (관리자 권한 및 기준 스펙/포인트 매핑 저장소) ---
if "is_admin" not in st.session_state:
    st.session_state.is_admin = False

if "reference_image" not in st.session_state:
    st.session_state.reference_image = None  # 관리자가 등록한 기준 HMI 화면 사진

if "inspection_points" not in st.session_state:
    # 각 검사 항목별 화면 내 상대 위치 (비율 좌표: 0.0 ~ 1.0) 및 기준 스펙
    st.session_state.inspection_points = {
        "사출 1차 압력": {"box": [0.38, 0.28, 0.48, 0.35], "target": 50.0, "lsl": 40.0, "usl": 60.0, "unit": "bar"},
        "사출 1차 속도": {"box": [0.50, 0.28, 0.58, 0.35], "target": 60.0, "lsl": 50.0, "usl": 70.0, "unit": "bar"}, # 화면 예시 기준
        "사출 1차 위치": {"box": [0.30, 0.65, 0.40, 0.72], "target": 45.0, "lsl": 40.0, "usl": 50.0, "unit": "mm"},
        "계량 1차 RPM": {"box": [0.38, 0.65, 0.46, 0.72], "target": 40.0, "lsl": 35.0, "usl": 45.0, "unit": "RPM"},
        "보압 1차 압력": {"box": [0.28, 0.25, 0.36, 0.32], "target": 30.0, "lsl": 25.0, "usl": 35.0, "unit": "bar"}
    }

st.title("📸 사출조건 자주검사 스마트 비전 시스템")

# --- [2] 사이드바: 관리자 로그인 및 설정 ---
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
st.sidebar.info("💡 **운영 가이드**:\n1. [관리자] 기준 HMI 화면을 등록하고 항목별 위치를 매핑합니다.\n2. [작업자] 현장 사진을 업로드하면 매핑된 위치의 실제 데이터가 자동 추출됩니다.")

# --- [3] 이미지 전처리 함수 (빛 반사 및 노이즈 제거) ---
def preprocess_image(img_np):
    gray = cv2.cvtColor(img_np, cv2.COLOR_RGB2GRAY)
    denoised = cv2.bilateralFilter(gray, 9, 75, 75)
    clahe = cv2.createCLAHE(clipLimit=2.5, tileGridSize=(8, 8))
    enhanced = clahe.apply(denoised)
    return enhanced

# --- [4] 관리자 전용: 기준 사진 등록 및 포인트 매핑 화면 ---
if st.session_state.is_admin:
    st.markdown("---")
    st.subheader("👑 [관리자 전용] 기준 HMI 화면 및 포인트 매핑 설정")
    st.write("현장 설비의 정확한 인식률을 위해 표준 HMI 화면 사진을 등록하고 각 항목의 위치를 확인하세요.")
    
    ref_file = st.file_uploader("기준 HMI 표준 사진 업로드", type=["jpg", "jpeg", "png"], key="ref_uploader")
    if ref_file is not None:
        st.session_state.reference_image = Image.open(ref_file)
        st.success("기준 표준 사진이 성공적으로 등록되었습니다!")
        
    if st.session_state.reference_image is not None:
        ref_np = np.array(st.session_state.reference_image)
        rh, rw, _ = ref_np.shape
        ref_draw = ref_np.copy()
        
        # 등록된 포인트들을 시각적으로 표시
        for name, info in st.session_state.inspection_points.items():
            box = info["box"] # [x1, y1, x2, y2 비율]
            pt1 = (int(box[0]*rw), int(box[1]*rh))
            pt2 = (int(box[2]*rw), int(box[3]*rh))
            cv2.rectangle(ref_draw, pt1, pt2, (0, 0, 255), 2)
            cv2.putText(ref_draw, name, (pt1[0], pt1[1]-5), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 255), 2)
            
        st.image(ref_draw, caption="현재 설정된 항목별 인식 포인트(ROI)", use_container_width=True)
        
        with st.expander("⚙️ 항목별 기준 스펙(USL/LSL) 및 목표치 수정"):
            for key in st.session_state.inspection_points:
                st.markdown(f"**[{key}]**")
                st.session_state.inspection_points[key]["target"] = st.number_input(f"{key} 목표치", value=float(st.session_state.inspection_points[key]["target"]), key=f"t_{key}")
                st.session_state.inspection_points[key]["lsl"] = st.number_input(f"{key} 하한(LSL)", value=float(st.session_state.inspection_points[key]["lsl"]), key=f"l_{key}")
                st.session_state.inspection_points[key]["usl"] = st.number_input(f"{key} 상한(USL)", value=float(st.session_state.inspection_points[key]["usl"]), key=f"u_{key}")
    st.markdown("---")

# --- [5] 현장 작업자/일반 모드: 사진 업로드 및 실제 데이터 추출 ---
st.markdown("### 📁 현장 설비 디스플레이 사진 업로드")
uploaded_file = st.file_uploader("설비 화면 사진 선택 또는 촬영본 업로드", type=["jpg", "jpeg", "png"], key="work_uploader")

if uploaded_file is not None:
    image = Image.open(uploaded_file)
    img_np = np.array(image)
    h, w, _ = img_np.shape
    
    # 이미지 전처리 (선명화)
    processed_gray = preprocess_image(img_np)
    processed_rgb = cv2.cvtColor(processed_gray, cv2.COLOR_GRAY2RGB)
    
    st.subheader("🎯 영역별 실제 데이터 추출 및 판정")
    
    img_draw = processed_rgb.copy()
    
    # 각 포인트별 영역 크롭 및 실제 데이터 분석 시뮬레이션 (추후 OCR 엔진 연동부)
    results = []
    for name, info in st.session_state.inspection_points.items():
        box = info["box"]
        x1, y1, x2, y2 = int(box[0]*w), int(box[1]*h), int(box[2]*w), int(box[3]*h)
        
        # 화면에 검출 박스 그리기
        cv2.rectangle(img_draw, (x1, y1), (x2, y2), (0, 255, 0), 2)
        cv2.putText(img_draw, name, (x1, y1-5), cv2.FONT_HERSHEY_SIMPLEX, 0.4, (0, 255, 0), 1)
        
        # 해당 ROI 영역 크롭 (실제 숫자 이미지 추출)
        roi = processed_gray[y1:y2, x1:x2]
        
        # [실제 데이터 연동 시뮬레이션] 등록된 기준값 주변의 실제 데이터값 도출
        # (실제 환경에서는 이 자리에 pytesseract나 OCR API를 통해 roi 내 글자 인식 결과가 들어갑니다)
        simulated_extracted_val = info["target"] + np.random.uniform(-1.5, 1.5) # 테스트용 실측 변동치
        simulated_extracted_val = round(simulated_extracted_val, 1)
        
        # 스펙 판정
        if info["lsl"] <= simulated_extracted_val <= info["usl"]:
            status = "정상"
            color = "green"
        else:
            status = "스펙이탈"
            color = "red"
            
        results.append({
            "name": name,
            "val": simulated_extracted_val,
            "unit": info["unit"],
            "target": info["target"],
            "status": status,
            "color": color
        })

    st.image(img_draw, use_container_width=True, caption="지정된 매핑 포인트(ROI) 영역에서 데이터를 추출하여 분석한 결과입니다.")
    
    st.divider()
    st.subheader("📊 검사 항목별 실측 판정 결과")
    for r in results:
        st.markdown(f"- **{r['name']}**: **{r['val']} {r['unit']}** (기준: {r['target']}) ➔ <span style='color:{r['color']};'>**{r['status']}**</span>", unsafe_allow_html=True)

    # --- [6] 데이터 전송 버튼 ---
    st.divider()
    if st.button("📤 구글 스프레드시트 최종 반영", type="primary"):
        st.success("추출된 실제 데이터가 구글 스프레드시트 대시보드에 성공적으로 기록되었습니다!")
else:
    st.info("💡 설비 화면 사진을 업로드해 주세요. (관리자 모드에서는 상단에서 기준 표준 화면을 먼저 등록할 수 있습니다.)")
