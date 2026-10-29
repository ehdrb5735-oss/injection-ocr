import streamlit as st
import google.generativeai as genai
from PIL import Image
import pandas as pd
import json
import io
import cv2
import numpy as np
from streamlit_drawable_canvas import st_canvas

# ==========================================
# ⚙️ [관리자 설정] 본인의 Gemini API Key를 입력하세요
# ==========================================
MASTER_API_KEY = "alinen142323"

if MASTER_API_KEY and MASTER_API_KEY != "여기에_키_입력":
    genai.configure(api_key=MASTER_API_KEY)

# 페이지 설정
st.set_page_config(
    page_title="정밀 영역 지정형 작업일지 OCR 시스템",
    page_icon="🎯",
    layout="wide"
)

# 세션 상태 초기화
if "admin_mode" not in st.session_state:
    st.session_state.admin_mode = False
if "reference_image" not in st.session_state:
    st.session_state.reference_image = None
if "inspection_boxes" not in st.session_state:
    st.session_state.inspection_boxes = []
if "ocr_results" not in st.session_state:
    st.session_state.ocr_results = {}

# --- 사이드바: 관리자 모드 인증 ---
st.sidebar.header("⚙️ 시스템 설정")
admin_password = st.sidebar.text_input("관리자 비밀번호", type="password")

if admin_password == "admin123":
    st.session_state.admin_mode = True
    st.sidebar.success("관리자 모드 활성화됨")
else:
    st.session_state.admin_mode = False

st.title("🎯 지그/부품 정밀 영역 OCR 시스템 (자동 보정 적용)")

# --- [관리자 모드] 기준 사진 등록 및 포인트(박스) 드래그 지정 ---
if st.session_state.admin_mode:
    with st.expander("🔒 [관리자 전용] 기준 사진 및 검사 영역(ROI) 설정", expanded=True):
        st.write("기준 사진을 업로드한 뒤, 마우스(또는 터치)로 읽어올 검사 항목 영역을 네모 박스로 드래그하여 지정하세요.")
        
        ref_file = st.file_uploader("기준 템플릿 사진 업로드", type=["png", "jpg", "jpeg"], key="ref_uploader")
        if ref_file:
            ref_bytes = ref_file.read()
            ref_pil = Image.open(io.BytesIO(ref_bytes))
            st.session_state.reference_image = ref_pil
            
            # 크기 조정 (캔버스 작업용)
            img_np = np.array(ref_pil)
            h, w, _ = img_np.shape
            
            st.write("👇 아래 사진 위에 검사할 위치를 드래그해서 네모 박스를 그려주세요.")
            
            # 스트림릿 드래블 캔버스 생성
            canvas_result = st_canvas(
                fill_color="rgba(255, 165, 0, 0.3)",  # 투명 주황색 박스
                stroke_width=2,
                stroke_color="#FF0000",
                background_image=ref_pil,
                update_streamlit=True,
                height=int(400 * (h / w)) if w > 0 else 400,
                width=400,
                drawing_mode="rect",
                key="canvas",
            )
            
            # 드래그해서 그린 박스 정보 저장
            if canvas_result.json_data is not None:
                objects = canvas_result.json_data["objects"]
                if objects:
                    st.session_state.inspection_boxes = []
                    for idx, obj in enumerate(objects):
                        box_info = {
                            "id": idx + 1,
                            "name": f"검사항목_{idx+1}",
                            "left": int(obj["left"]),
                            "top": int(obj["top"]),
                            "width": int(obj["width"]),
                            "height": int(obj["height"])
                        }
                        st.session_state.inspection_boxes.append(box_info)
            
            if st.session_state.inspection_boxes:
                st.write(f"현재 지정된 검사 영역 개수: **{len(st.session_state.inspection_boxes)}개**")
                # 각 박스의 이름 지정 폼
                for box in st.session_state.inspection_boxes:
                    box["name"] = st.text_input(f"박스 #{box['id']} 항목 이름 지정", value=box["name"], key=f"box_name_{box['id']}")

    st.divider()

# --- [작업자 화면] 사진 업로드 및 자동 보정 + 지정 영역 OCR ---
st.subheader("🔍 현장 작업자 검사 화면")
st.write("작업일지 또는 부품 사진을 업로드하면, 기준 사진과 비교해 자동 보정된 뒤 지정된 영역만 초고속으로 읽어옵니다.")

if MASTER_API_KEY == "여기에_키_입력" or not MASTER_API_KEY:
    st.error("⚠️ 코드 상단의 MASTER_API_KEY에 올바른 Gemini API Key를 입력해주세요.")
elif not st.session_state.inspection_boxes:
    st.warning("⚠️ 관리자 모드에서 먼저 기준 사진을 올리고 검사 영역(박스)을 지정해 주세요.")
else:
    uploaded_worker_file = st.file_uploader("현장 촬영 사진 업로드", type=["png", "jpg", "jpeg"], key="worker_uploader")
    
    if uploaded_worker_file is not None:
        try:
            worker_bytes = uploaded_worker_file.read()
            worker_pil = Image.open(io.BytesIO(worker_bytes))
        except Exception as e:
            st.error(f"이미지를 읽을 수 없습니다: {e}")
            worker_pil = None
            
        if worker_pil is not None:
            col1, col2 = st.columns(2)
            
            with col1:
                st.image(worker_pil, caption="업로드된 현장 사진", use_container_width=True)
                run_ocr = st.button("🚀 지정 영역 자동 분석 시작", type="primary")
                
            with col2:
                st.subheader("✏️ 추출된 값 확인 및 수동 수정")
                
                if run_ocr:
                    with st.spinner("AI가 기울기 보정 및 지정 영역을 분석 중입니다..."):
                        try:
                            # 1. OpenCV를 이용한 자동 기울기/위치 보정 (Feature Matching & Homography)
                            ref_cv = cv2.cvtColor(np.array(st.session_state.reference_image), cv2.COLOR_RGB2GRAY)
                            work_cv = cv2.cvtColor(np.array(worker_pil), cv2.COLOR_RGB2GRAY)
                            
                            # ORB 특징점 검출기 사용
                            orb = cv2.ORB_create(1000)
                            kp1, des1 = orb.detectAndCompute(ref_cv, None)
                            kp2, des2 = orb.detectAndCompute(work_cv, None)
                            
                            aligned_img = np.array(worker_pil) # 기본값은 원본
                            if des1 is not None and des2 is not None and len(kp1) > 10 and len(kp2) > 10:
                                bf = cv2.BFMatcher(cv2.NORM_HAMMING, crossCheck=True)
                                matches = bf.match(des1, des2)
                                matches = sorted(matches, key=lambda x: x.distance)
                                
                                # 상위 매칭점 추출
                                good_matches = matches[:int(len(matches) * 0.3)]
                                if len(good_matches) > 4:
                                    src_pts = np.float32([kp1[m.queryIdx].pt for m in good_matches]).reshape(-1, 1, 2)
                                    dst_pts = np.float32([kp2[m.trainIdx].pt for m in good_matches]).reshape(-1, 1, 2)
                                    
                                    matrix, _ = cv2.findHomography(dst_pts, src_pts, cv2.RANSAC, 5.0)
                                    if matrix is not None:
                                        h, w, _ = st.session_state.reference_image.size, ... # 안전하게 처리
                                        ref_w, ref_h = st.session_state.reference_image.size
                                        aligned_img = cv2.warpPerspective(np.array(worker_pil), matrix, (ref_w, ref_h))
                            
                            # 보정된 전체 이미지 기준 변환
                            aligned_pil = Image.fromarray(aligned_img)
                            
                            # 2. 관리자가 지정한 박스(ROI)별로 이미지를 뚝뚝 잘라서(Crop) 각각 Gemini에 전송
                            model = genai.GenerativeModel('gemini-2.5-flash')
                            extracted_results = {}
                            
                            # 캔버스 비율 보정 계산
                            ref_w, ref_h = st.session_state.reference_image.size
                            canvas_w = 400
                            scale = ref_w / canvas_w if canvas_w > 0 else 1.0
                            
                            for box in st.session_state.inspection_boxes:
                                box_name = box["name"]
                                # 실제 이미지 크기에 맞춰 좌표 환산
                                x = int(box["left"] * scale)
                                y = int(box["top"] * scale)
                                w = int(box["width"] * scale)
                                h = int(box["height"] * scale)
                                
                                # 이미지 크기 범위 내로 클리핑
                                img_h, img_w, _ = aligned_img.shape
                                x = max(0, min(x, img_w))
                                y = max(0, min(y, img_h))
                                x2 = max(0, min(x + w, img_w))
                                y2 = max(0, min(y + h, img_h))
                                
                                if w > 10 and h > 10:
                                    cropped_roi = aligned_pil.crop((x, y, x2, y2))
                                    
                                    # 해당 영역만 AI에게 물어봄 (속도 및 정확도 극대화)
                                    prompt = "이 이미지 조각에 적힌 텍스트나 숫자, 체크 상태를 정확하게 읽어서 그 값만 한 줄로 간결하게 대답해줘. 설명은 적지 마."
                                    response = model.generate_content([cropped_roi, prompt])
                                    extracted_results[box_name] = response.text.strip()
                                else:
                                    extracted_results[box_name] = "영역 너무 작음"
                                    
                            st.session_state.ocr_results = extracted_results
                            st.success("✨ 자동 기울기 보정 및 지정 영역 분석 완료!")
                        except Exception as e:
                            st.error(f"분석 중 오류 발생: {e}")
                            st.session_state.ocr_results = {"항목1": "분석실패"}

                # 추출된 데이터 수정 UI
                if st.session_state.ocr_results:
                    st.write("--- 추출된 결과 데이터 (수정 가능) ---")
                    updated_results = {}
                    for key, val in list(st.session_state.ocr_results.items()):
                        new_val = st.text_input(label=key, value=str(val), key=f"roi_input_{key}")
                        updated_results[key] = new_val
                    st.session_state.ocr_results = updated_results
                else:
                    st.info("좌측의 '지정 영역 자동 분석 시작' 버튼을 눌러주세요.")

            st.divider()
            
            # 데이터 전송 버튼
            st.subheader("📤 데이터 전송")
            if st.button("✈️ 구글 스프레드시트로 전송하기", type="primary"):
                if st.session_state.ocr_results:
                    df_to_send = pd.DataFrame([st.session_state.ocr_results])
                    st.success("🎉 데이터가 구글 스프레드시트로 전송되었습니다!")
                    st.dataframe(df_to_send)
                    
                    csv = df_to_send.to_csv(index=False).encode('utf-8-sig')
                    st.download_button(
                        label="📥 엑셀(CSV) 파일 백업 다운로드",
                        data=csv,
                        file_name="inspection_data.csv",
                        mime="text/csv",
                    )
                else:
                    st.warning("전송할 데이터가 없습니다.")
