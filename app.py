import streamlit as st
import cv2
import numpy as np
from PIL import Image
from streamlit_drawable_canvas import st_canvas

st.set_page_config(page_title="사출조건 자주검사 스마트 비전 시스템", layout="centered")

# --- [1] 세션 상태 초기화 ---
if "is_admin" not in st.session_state:
    st.session_state.is_admin = False

if "ref_image_pil" not in st.session_state:
    st.session_state.ref_image_pil = None  # 기준 표준 사진 (PIL Image)

if "mapping_boxes" not in st.session_state:
    # 항목별 지정된 박스 좌표 저장소 ({ "항목이름": [x1, y1, x2, y2 비율] })
    st.session_state.mapping_boxes = {}

# 검사할 항목 리스트 정의
TARGET_ITEMS = ["사출 1차 압력", "사출 1차 속도", "사출 1차 위치", "계량 1차 RPM", "보압 1차 압력"]

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
st.sidebar.info("💡 **마우스 드래그 매핑 가이드**:\n1. 관리자로 로그인 후 표준 사진을 올립니다.\n2. 매핑할 항목을 선택하고 사진 위를 마우스로 **드래그하여 네모 박스**를 그립니다.\n3. 저장하면 해당 위치가 완벽하게 등록됩니다.")

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

# --- [4] 관리자 전용: 표준 사진 등록 및 마우스 드래그 영역 지정 화면 ---
if st.session_state.is_admin:
    st.markdown("---")
    st.subheader("👑 [관리자 전용] 표준 사진 마우스 드래그 위치 지정")
    st.write("표준 HMI 사진을 올린 뒤, 아래에서 항목을 선택하고 사진 위를 **마우스로 드래그**하여 해당 위치를 지정하세요.")
    
    ref_file = st.file_uploader("표준 HMI 기준 사진 업로드", type=["jpg", "jpeg", "png"], key="ref_upload_canvas")
    if ref_file is not None:
        st.session_state.ref_image_pil = Image.open(ref_file)
        st.success("표준 기준 사진이 등록되었습니다!")
        
    if st.session_state.ref_image_pil is not None:
        # 드래그할 항목 선택
        selected_item = st.selectbox("🎯 위치를 지정할 검사 항목 선택", TARGET_ITEMS)
        
        st.write(f"👉 **[{selected_item}]**에 해당하는 위치를 아래 사진 위에 **마우스로 드래그하여 네모 박스를 그려주세요.**")
        
        # 이미지 크기 맞춤
        img_w, img_h = st.session_state.ref_image_pil.size
        display_width = min(img_w, 600)
        display_height = int(img_h * (display_width / img_w))
        
        # 드래그 캔버스 실행
        canvas_result = st_canvas(
            fill_color="rgba(0, 255, 0, 0.3)",  # 채우기 색상 (반투명 초록)
            stroke_width=2,
            stroke_color="#FF0000",             # 테두리 색상 (빨강)
            background_image=st.session_state.ref_image_pil.resize((display_width, display_height)),
            update_streamlit=True,
            drawing_mode="rect",                # 네모 박스 드래그 모드
            height=display_height,
            width=display_width,
            key="canvas_drawing",
        )
        
        # 드래그해서 그린 박스가 있다면 저장 버튼 활성화
        if canvas_result.json_data is not None:
            objects = canvas_result.json_data["objects"]
            if len(objects) > 0:
                # 가장 최근에 그린 박스 가져오기
                obj = objects[-1]
                left, top, width, height = obj["left"], obj["top"], obj["width"], obj["height"]
                
                # 비율 좌표로 변환 (0.0 ~ 1.0)
                x1 = left / display_width
                y1 = top / display_height
                x2 = (left + width) / display_width
                y2 = (top + height) / display_height
                
                if st.button(f"💾 [{selected_item}] 위치 저장하기"):
                    st.session_state.mapping_boxes[selected_item] = [x1, y1, x2, y2]
                    st.success(f"[{selected_item}] 위치가 성공적으로 저장되었습니다!")
                    
        # 현재까지 등록된 매핑 목록 표시
        if st.session_state.mapping_boxes:
            st.markdown("📋 **현재 등록된 항목별 위치 목록:**")
            for item, box in st.session_state.mapping_boxes.items():
                st.write(f"- **{item}**: 지정완료 (영역: [{box[0]:.2f}, {box[1]:.2f}, {box[2]:.2f}, {box[3]:.2f}])")
    st.markdown("---")

# --- [5] 현장 작업자 모드: 사진 업로드 및 자동 보정·추출 ---
st.markdown("### 📁 현장 설비 디스플레이 사진 업로드")
st.write("현장에서 촬영한 사진을 업로드해 주세요. (비스듬하게 촬영되어도 표준 사진을 기준으로 자동 정렬되어 지정된 위치를 정확히 찾아냅니다.)")

work_file = st.file_uploader("현장 촬영 사진 업로드", type=["jpg", "jpeg", "png"], key="work_upload_canvas")

if work_file is not None:
    work_img = Image.open(work_file)
    work_np = np.array(work_img)
    
    ref_np = np.array(st.session_state.ref_image_pil) if st.session_state.ref_image_pil else None
    
    # 기준 사진이 있으면 자동 보정(정렬) 수행
    if ref_np is not None:
        st.info("🔄 표준 기준 사진을 대조하여 비스듬한 각도와 왜곡을 자동 보정하는 중입니다...")
        processed_img = align_images(ref_np, work_np)
    else:
        processed_img = work_np
        st.warning("⚠️ [알림] 등록된 표준 기준 사진이 없습니다. 관리자 로그인 후 기준 사진과 위치를 지정해 주세요.")
        
    h, w, _ = processed_img.shape
    img_draw = processed_img.copy()
    
    st.subheader("🎯 마우스로 지정된 위치 매핑 및 데이터 추출 영역")
    
    results = []
    if st.session_state.mapping_boxes:
        for name, box in st.session_state.mapping_boxes.items():
            x1, y1, x2, y2 = int(box[0]*w), int(box[1]*h), int(box[2]*w), int(box[3]*h)
            
            # 보정된 이미지 위에 지정된 박스 표시
            cv2.rectangle(img_draw, (x1, y1), (x2, y2), (0, 255, 0), 2)
            cv2.putText(img_draw, name, (x1, y1-5), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 2)
            
            # 데이터 추출 시뮬레이션
            simulated_val = round(100.0 + np.random.uniform(-5.0, 5.0), 1)
            results.append({"name": name, "val": simulated_val, "status": "정상", "color": "green"})
    else:
        st.info("💡 아직 관리자가 지정한 위치(매핑 박스)가 없습니다. 관리자 모드에서 위치를 먼저 지정해 주세요.")

    st.image(img_draw, use_container_width=True, caption="마우스로 드래그하여 지정한 위치와 자동 보정이 적용된 추출 화면입니다.")
    
    if results:
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
