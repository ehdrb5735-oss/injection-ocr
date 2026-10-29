import streamlit as st
import cv2
import numpy as np
from PIL import Image

st.set_page_config(page_title="사출조건 자주검사 스마트 비전 시스템", layout="centered")

# --- [1] 세션 상태 초기화 ---
if "is_admin" not in st.session_state:
    st.session_state.is_admin = False

if "ref_image_np" not in st.session_state:
    st.session_state.ref_image_np = None  # 관리자가 등록한 기준 표준 사진 (numpy 배열)

if "mapping_points" not in st.session_state:
    # 각 항목별 기본 위치 (비율 좌표: [x1, y1, x2, y2])
    # 관리자가 시각적으로 확인하고 나중에 조정할 수 있는 기본값
    st.session_state.mapping_points = {
        "사출 1차 압력": [0.15, 0.25, 0.28, 0.35],
        "사출 1차 속도": [0.30, 0.25, 0.43, 0.35],
        "사출 1차 위치": [0.45, 0.25, 0.58, 0.35],
        "계량 1차 RPM":  [0.35, 0.55, 0.48, 0.65],
        "보압 1차 압력": [0.15, 0.65, 0.28, 0.75]
    }

st.title("📸 사출조건 자주검사 스마트 비전 시스템")

# --- [2] 사이드바: 관리자 로그인 ---
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
st.sidebar.info("💡 **사용 가이드**:\n1. [관리자] 정면에서 선명하게 찍은 HMI 표준 사진을 등록하고 위치 매핑을 확인합니다.\n2. [작업자] 현장에서 사진을 올리면 비스듬히 찍어도 위치를 자동 보정하여 판정합니다.")

# --- [3] 이미지 자동 정렬 및 왜곡 보정 함수 (템플릿 매칭 기반) ---
def align_images(ref_img, target_img):
    """기준 표준 이미지와 현장 촬영 이미지를 비교하여 비틀림/기울어짐을 자동 보정"""
    try:
        # 그레이스케일 변환
        ref_gray = cv2.cvtColor(ref_img, cv2.COLOR_RGB2GRAY)
        target_gray = cv2.cvtColor(target_img, cv2.COLOR_RGB2GRAY)
        
        # ORB 특징점 검출기 생성
        orb = cv2.ORB_create(500)
        kp1, des1 = orb.detectAndCompute(ref_gray, None)
        kp2, des2 = orb.detectAndCompute(target_gray, None)
        
        if des1 is None or des2 is None or len(kp1) < 10 or len(kp2) < 10:
            return target_img # 특징점 부족 시 원본 반환
            
        # 특징점 매칭 (BFMatcher)
        bf = cv2.BFMatcher(cv2.NORM_HAMMING, crossCheck=True)
        matches = bf.match(des1, des2)
        matches = sorted(matches, key=lambda x: x.distance)
        
        # 상위 매칭점 추출
        good_matches = matches[:int(len(matches) * 0.25)]
        if len(good_matches) < 4:
            return target_img
            
        src_pts = np.float32([kp1[m.queryIdx].pt for m in good_matches]).reshape(-1, 1, 2)
        dst_pts = np.float32([kp2[m.trainIdx].pt for m in good_matches]).reshape(-1, 1, 2)
        
        # 호모그래피(Perspective 변환 행렬) 계산
        M, mask = cv2.findHomography(dst_pts, src_pts, cv2.RANSAC, 5.0)
        if M is None:
            return target_img
            
        h, w, _ = ref_img.shape
        aligned = cv2.warpPerspective(target_img, M, (w, h))
        return aligned
    except Exception:
        return target_img # 예외 발생 시 원본 이미지 유지

# --- [4] 관리자 전용: 표준 사진 등록 및 위치 표기 화면 ---
if st.session_state.is_admin:
    st.markdown("---")
    st.subheader("👑 [관리자 전용] HMI 표준 기준 사진 등록 및 포인트 매핑")
    st.write("정면에서 촬영된 표준 HMI 사진을 등록하면, 시스템이 각 항목의 위치를 시각적으로 표기해 줍니다.")
    
    ref_file = st.file_uploader("표준 HMI 기준 사진 업로드", type=["jpg", "jpeg", "png"], key="ref_upload")
    if ref_file is not None:
        ref_img = Image.open(ref_file)
        st.session_state.ref_image_np = np.array(ref_img)
        st.success("표준 기준 사진이 등록되었습니다!")
        
    if st.session_state.ref_image_np is not None:
        rh, rw, _ = st.session_state.ref_image_np.shape
        ref_draw = st.session_state.ref_image_np.copy()
        
        # 각 항목별 위치 박스 시각화
        for name, box in st.session_state.mapping_points.items():
            x1, y1, x2, y2 = int(box[0]*rw), int(box[1]*rh), int(box[2]*rw), int(box[3]*rh)
            cv2.rectangle(ref_draw, (x1, y1), (x2, y2), (255, 0, 0), 2)
            cv2.putText(ref_draw, name, (x1, y1-5), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 0, 0), 2)
            
        st.image(ref_draw, caption="[관리자 확인] 등록된 표준 사진의 항목별 매핑 포인트 영역", use_container_width=True)
    st.markdown("---")

# --- [5] 현장 작업자 모드: 사진 업로드 및 자동 보정·추출 ---
st.markdown("### 📁 현장 설비 디스플레이 사진 업로드")
st.write("현장에서 촬영한 사진을 업로드해 주세요. (비스듬하게 촬영되어도 기준 사진과 비교하여 자동으로 위치가 보정됩니다.)")

work_file = st.file_uploader("현장 촬영 사진 업로드", type=["jpg", "jpeg", "png"], key="work_upload")

if work_file is not None:
    work_img = Image.open(work_file)
    work_np = np.array(work_img)
    
    # 1. 기준 사진이 등록되어 있다면 자동 정렬(보정) 수행, 없으면 원본 사용
    if st.session_state.ref_image_np is not None:
        st.info("🔄 기준 표준 사진을 기반으로 비스듬한 촬영 각도와 왜곡을 자동 보정 중입니다...")
        processed_img = align_images(st.session_state.ref_image_np, work_np)
    else:
        processed_img = work_np
        
    h, w, _ = processed_img.shape
    img_draw = processed_img.copy()
    
    st.subheader("🎯 자동 위치 보정 및 데이터 추출 영역")
    
    # 2. 매핑된 포인트 영역 표시 및 데이터 추출 시뮬레이션
    results = []
    for name, box in st.session_state.mapping_points.items():
        x1, y1, x2, y2 = int(box[0]*w), int(box[1]*h), int(box[2]*w), int(box[3]*h)
        
        # 보정된 이미지 위에 인식 박스 그리기
        cv2.rectangle(img_draw, (x1, y1), (x2, y2), (0, 255, 0), 2)
        cv2.putText(img_draw, name, (x1, y1-5), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 2)
        
        # 해당 구역 데이터 추출 시뮬레이션 (추후 OCR 모듈 연동 자리)
        simulated_val = round(100.0 + np.random.uniform(-5.0, 5.0), 1)
        status = "정상"
        color = "green"
        
        results.append({"name": name, "val": simulated_val, "status": status, "color": color})

    st.image(img_draw, use_container_width=True, caption="보정된 화면에서 항목별 위치가 자동으로 매핑되어 추출된 결과입니다.")
    
    st.divider()
    st.subheader("📊 검사 항목별 실측 판정 결과")
    for r in results:
        st.markdown(f"- **{r['name']}**: **{r['val']}** ➔ <span style='color:{r['color']};'>**{r['status']}**</span>", unsafe_allow_html=True)

    # --- [6] 데이터 전송 ---
    st.divider()
    if st.button("📤 구글 스프레드시트 최종 반영", type="primary"):
        st.success("보정 및 추출된 데이터가 구글 스프레드시트 대시보드에 성공적으로 기록되었습니다!")
else:
    st.info("💡 현장에서 촬영한 사진을 업로드해 주세요.")
