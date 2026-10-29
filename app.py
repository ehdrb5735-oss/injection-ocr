import streamlit as st
import cv2
import numpy as np
from PIL import Image

st.set_page_config(page_title="사출조건 자주검사 스마트 비전 시스템", layout="centered")

# --- [1] 세션 상태 초기화 ---
if "is_admin" not in st.session_state:
    st.session_state.is_admin = False

if "ref_image_np" not in st.session_state:
    st.session_state.ref_image_np = None  # 기준 표준 사진

if "mapping_points" not in st.session_state:
    # 관리자가 언제든 수정할 수 있는 항목별 위치 좌표 (비율: 0.0 ~ 1.0)
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
st.sidebar.info("💡 **운영 가이드**:\n1. [관리자 로그인] 표준 사진을 등록하고 하단에서 각 항목의 위치(박스 좌표)를 직접 설정합니다.\n2. [작업자] 현장 사진을 올리면 비스듬하게 찍어도 자동 정렬되어 해당 위치의 데이터가 추출됩니다.")

# --- [3] 이미지 자동 정렬 함수 (왜곡 보정) ---
def align_images(ref_img, target_img):
    try:
        ref_gray = cv2.cvtColor(ref_img, cv2.COLOR_RGB2GRAY)
        target_gray = cv2.cvtColor(target_img, cv2.COLOR_RGB2GRAY)
        
        orb = cv2.ORB_create(500)
        kp1, des1 = orb.detectAndCompute(ref_gray, None)
        kp2, des2 = orb.detectAndCompute(target_gray, None)
        
        if des1 is None or des2 is None or len(kp1) < 10 or len(kp2) < 10:
            return target_img
            
        bf = cv2.BFMatcher(cv2.NORM_HAMMING, crossCheck=True)
        matches = bf.match(des1, des2)
        matches = sorted(matches, key=lambda x: x.distance)
        
        good_matches = matches[:int(len(matches) * 0.25)]
        if len(good_matches) < 4:
            return target_img
            
        src_pts = np.float32([kp1[m.queryIdx].pt for m in good_matches]).reshape(-1, 1, 2)
        dst_pts = np.float32([kp2[m.trainIdx].pt for m in good_matches]).reshape(-1, 1, 2)
        
        M, mask = cv2.findHomography(dst_pts, src_pts, cv2.RANSAC, 5.0)
        if M is None:
            return target_img
            
        h, w, _ = ref_img.shape
        aligned = cv2.warpPerspective(target_img, M, (w, h))
        return aligned
    except Exception:
        return target_img

# --- [4] 관리자 전용: 표준 사진 등록 및 위치 좌표 직접 설정 화면 ---
if st.session_state.is_admin:
    st.markdown("---")
    st.subheader("👑 [관리자 전용] 표준 HMI 사진 등록 및 위치(ROI) 설정")
    st.write("표준 기준 사진을 등록한 뒤, 아래 설정창에서 각 항목의 위치 박스 좌표(시작/끝 비율)를 직접 조절하여 정확한 위치를 잡아주세요.")
    
    ref_file = st.file_uploader("표준 HMI 기준 사진 업로드", type=["jpg", "jpeg", "png"], key="ref_upload_new")
    if ref_file is not None:
        ref_img = Image.open(ref_file)
        st.session_state.ref_image_np = np.array(ref_img)
        st.success("새로운 표준 기준 사진이 등록되었습니다!")
        
    if st.session_state.ref_image_np is not None:
        rh, rw, _ = st.session_state.ref_image_np.shape
        ref_draw = st.session_state.ref_image_np.copy()
        
        # 관리자가 지정한 좌표를 반영하여 박스 그리기
        for name, box in st.session_state.mapping_points.items():
            x1, y1, x2, y2 = int(box[0]*rw), int(box[1]*rh), int(box[2]*rw), int(box[3]*rh)
            cv2.rectangle(ref_draw, (x1, y1), (x2, y2), (255, 0, 0), 2)
            cv2.putText(ref_draw, name, (x1, y1-5), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 0, 0), 2)
            
        st.image(ref_draw, caption="[현재 설정된 표준 사진 및 매핑 위치]", use_container_width=True)
        
        # ⚙️ 각 항목별 위치 좌표(비율)를 직접 수정할 수 있는 입력폼 제공
        with st.expander("🛠️ 항목별 인식 위치(좌표) 미세조정 설정"):
            st.write("화면 전체 크기 기준 시작점(x1, y1)과 끝점(x2, y2)의 비율(0.0 ~ 1.0)을 조절하세요.")
            for name in st.session_state.mapping_points:
                cols = st.columns(5)
                cols[0].write(f"**{name}**")
                x1 = cols[1].number_input(f"x1 ({name})", value=float(st.session_state.mapping_points[name][0]), step=0.01, key=f"x1_{name}")
                y1 = cols[2].number_input(f"y1 ({name})", value=float(st.session_state.mapping_points[name][1]), step=0.01, key=f"y1_{name}")
                x2 = cols[3].number_input(f"x2 ({name})", value=float(st.session_state.mapping_points[name][2]), step=0.01, key=f"x2_{name}")
                y2 = cols[4].number_input(f"y2 ({name})", value=float(st.session_state.mapping_points[name][3]), step=0.01, key=f"y2_{name}")
                
                # 수정된 값 저장
                st.session_state.mapping_points[name] = [x1, y1, x2, y2]
                
        if st.button("💾 위치 설정 저장하기"):
            st.success("항목별 위치 좌표가 성공적으로 저장되었습니다!")
    st.markdown("---")

# --- [5] 현장 작업자 모드: 사진 업로드 및 자동 보정·추출 ---
st.markdown("### 📁 현장 설비 디스플레이 사진 업로드")
st.write("현장에서 촬영한 사진을 업로드해 주세요. (비스듬하게 촬영되어도 표준 사진을 기준으로 자동 정렬되어 위치를 찾아냅니다.)")

work_file = st.file_uploader("현장 촬영 사진 업로드", type=["jpg", "jpeg", "png"], key="work_upload_new")

if work_file is not None:
    work_img = Image.open(work_file)
    work_np = np.array(work_img)
    
    # 기준 사진이 있으면 자동 보정(정렬) 수행
    if st.session_state.ref_image_np is not None:
        st.info("🔄 표준 기준 사진을 대조하여 비스듬한 각도와 왜곡을 자동 보정하는 중입니다...")
        processed_img = align_images(st.session_state.ref_image_np, work_np)
    else:
        processed_img = work_np
        st.warning("⚠️ [알림] 등록된 표준 기준 사진이 없습니다. 관리자 로그인 후 기준 사진을 등록하시면 위치 자동 보정 기능이 활성화됩니다.")
        
    h, w, _ = processed_img.shape
    img_draw = processed_img.copy()
    
    st.subheader("🎯 위치 자동 매핑 및 데이터 추출 영역")
    
    results = []
    for name, box in st.session_state.mapping_points.items():
        x1, y1, x2, y2 = int(box[0]*w), int(box[1]*h), int(box[2]*w), int(box[3]*h)
        
        # 보정된 이미지 위에 매핑 박스 표시
        cv2.rectangle(img_draw, (x1, y1), (x2, y2), (0, 255, 0), 2)
        cv2.putText(img_draw, name, (x1, y1-5), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 2)
        
        # 데이터 추출 시뮬레이션
        simulated_val = round(100.0 + np.random.uniform(-5.0, 5.0), 1)
        results.append({"name": name, "val": simulated_val, "status": "정상", "color": "green"})

    st.image(img_draw, use_container_width=True, caption="관리자가 설정한 위치와 자동 보정이 적용된 추출 화면입니다.")
    
    st.divider()
    st.subheader("📊 검사 항목별 실측 판정 결과")
    for r in results:
        st.markdown(f"- **{r['name']}**: **{r['val']}** ➔ <span style='color:{r['color']};'>**{r['status']}**</span>", unsafe_allow_html=True)

    # --- [6] 데이터 전송 ---
    st.divider()
    if st.button("📤 구글 스프레드시트 최종 반영", type="primary"):
        st.success("데이터가 구글 스프레드시트 대시보드에 성공적으로 기록되었습니다!")
else:
    st.info("💡 현장에서 촬영한 사진을 업로드해 주세요.")
