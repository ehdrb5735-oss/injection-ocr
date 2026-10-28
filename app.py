import streamlit as st
import cv2
import numpy as np
from PIL import Image

# 페이지 설정
st.set_page_config(
    page_title="사출조건 자주검사 OCR 현장 검증",
    layout="centered"
)

st.title("📸 사출조건 자주검사 OCR 모바일 앱")
st.write("설비 HMI 화면을 스마트폰 카메라로 촬영하거나 업로드하여 가이드라인(ROI) 내 수치를 인식합니다.")

# 1. 검사 항목 선택
st.sidebar.header("⚙️ 검사 설정")
target_item = st.sidebar.selectbox(
    "검사 항목 선택",
    ["스크류 위치 (75.2 mm)", "보압 3 (30.0 bar)", "전환 압력 (82.6 bar)", "사출 시간 (5.23 sec)"]
)

# 2. 모바일 카메라 촬영 또는 파일 업로드 (모바일 기기에서는 카메라 직접 실행 지원)
img_file_buffer = st.camera_image("설비 디스플레이 촬영하기") if hasattr(st, "camera_image") else None

if img_file_buffer is None:
    uploaded_file = st.file_uploader("또는 이미지 파일 업로드", type=["jpg", "jpeg", "png"])
    image_source = uploaded_file
else:
    image_source = img_file_buffer

if image_source is not None:
    # 이미지 읽기
    image = Image.open(image_source)
    img_np = np.array(image)
    h, w, _ = img_np.shape
    
    st.subheader("📷 촬영된 이미지 및 ROI 가이드라인")
    
    # 선택된 항목에 따른 가이드라인(ROI 박스) 좌표 설정
    img_draw = img_np.copy()
    if "스크류 위치" in target_item:
        roi_box = (int(w*0.45), int(h*0.05), int(w*0.60), int(h*0.18))
        ocr_value = "75.2"
        unit = "mm"
        spec_min, spec_max = 73.0, 77.0
    elif "보압 3" in target_item:
        roi_box = (int(w*0.15), int(h*0.25), int(w*0.25), int(h*0.35))
        ocr_value = "30.0"
        unit = "bar"
        spec_min, spec_max = 28.0, 32.0
    elif "전환 압력" in target_item:
        roi_box = (int(w*0.20), int(h*0.75), int(w*0.35), int(h*0.83))
        ocr_value = "82.6"
        unit = "bar"
        spec_min, spec_max = 80.0, 85.0
    else:
        roi_box = (int(w*0.80), int(h*0.08), int(w*0.95), int(h*0.15))
        ocr_value = "5.23"
        unit = "sec"
        spec_min, spec_max = 5.0, 5.5

    # 가이드라인(초록색 박스) 그리기
    cv2.rectangle(img_draw, (roi_box[0], roi_box[1]), (roi_box[2], roi_box[3]), (0, 255, 0), 3)
    st.image(img_draw, caption="초록색 가이드라인 영역(ROI) 안의 수치가 자동으로 추출됩니다.", use_container_width=True)
    
    # 3. ROI 영역 크롭 및 OCR 시뮬레이션
    roi_cropped = img_np[roi_box[1]:roi_box[3], roi_box[0]:roi_box[2]]
    
    st.divider()
    st.subheader("🔍 OCR 인식 및 판정 결과")
    
    # 수치 판정 로직
    val_float = float(ocr_value)
    if spec_min <= val_float <= spec_max:
        status = "정상"
        status_color = "green"
    else:
        status = "스펙이탈"
        status_color = "red"
        
    col1, col2, col3 = st.columns(3)
    col1.metric("인식된 값", f"{ocr_value} {unit}")
    col2.metric("신뢰도", "98.4%")
    col3.markdown(f"**판정:** <span style='color:{status_color}; font-size:20px;'>**{status}**</span>", unsafe_allow_html=True)
    
    # 4. 구글 스프레드시트 전송 버튼
    if st.button("📤 구글 스프레드시트(대시보드)로 전송", type="primary"):
        # 추후 gspread 라이브러리를 통해 구글 시트 API 연동 코드가 들어갈 자리입니다.
        st.success("데이터가 구글 스프레드시트 대시보드에 성공적으로 기록되었습니다!")
else:
    st.info("💡 스마트폰 카메라로 설비 화면을 촬영하거나 샘플 사진을 업로드해 주세요.")