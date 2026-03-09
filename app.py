import streamlit as st
import easyocr
import pandas as pd
from datetime import datetime
import numpy as np
import cv2

# 페이지 설정
st.set_page_config(page_title="소 분석기", layout="wide")
st.title("🐂 소 양수현황 분석기 (최종 안정화 버전)")

# 엔진 로딩을 아주 조심스럽게 합니다
@st.cache_resource
def load_reader():
    # 모델을 미리 다운로드하지 않고 호출될 때만 사용하도록 설정
    return easyocr.Reader(['ko', 'en'], gpu=False)

# 버튼을 누르기 전까지는 엔진을 깨우지 않습니다 (서버 부담 방지)
if 'reader' not in st.session_state:
    st.session_state.reader = None

uploaded_files = st.file_uploader("사진을 선택하세요 (여러 장 가능)", type=['jpg', 'jpeg', 'png'], accept_multiple_files=True)

if uploaded_files:
    st.info(f"현재 {len(uploaded_files)}장의 사진이 대기 중입니다.")
    
    if st.button("🚀 분석 시작 (클릭 시 엔진 가동)"):
        # 여기서 엔진을 처음으로 부릅니다
        if st.session_state.reader is None:
            with st.spinner("서버 엔진을 깨우는 중입니다... (처음 한 번만 1~2분 소요)"):
                st.session_state.reader = load_reader()
        
        all_data = []
        progress_bar = st.progress(0)
        
        for i, uploaded_file in enumerate(uploaded_files):
            with st.spinner(f"[{i+1}/{len(uploaded_files)}] {uploaded_file.name} 분석 중..."):
                file_bytes = np.frombuffer(uploaded_file.read(), np.uint8)
                img = cv2.imdecode(file_bytes, cv2.IMREAD_COLOR)
                result = st.session_state.reader.readtext(img)
                
                # 데이터 정리 로직 (기존과 동일)
                lines = {}
                for (bbox, text, prob) in result:
                    y_center = (bbox[0][1] + bbox[2][1]) / 2
                    found_line = False
                    for line_y in lines.keys():
                        if abs(line_y - y_center) < 20: 
                            lines[line_y].append((bbox[0][0], text))
                            found_line = True
                            break
                    if not found_line:
                        lines[y_center] = [(bbox[0][0], text)]

                for y in sorted(lines.keys()):
                    row = sorted(lines[y], key=lambda x: x[0])
                    if len(row) >= 8:
                        try:
                            num = row[2][1].replace(" ", "")
                            b_raw = row[5][1].replace(" ", "").replace(",", ".")
                            t_raw = row[7][1].replace(" ", "").replace(",", ".")
                            b_date = datetime.strptime("20" + b_raw, '%Y.%m.%d')
                            t_date = datetime.strptime("20" + t_raw, '%Y.%m.%d')
                            diff_months = (t_date - b_date).days / 30.44
                            
                            if diff_months >= 10:
                                all_data.append({
                                    '파일명': uploaded_file.name,
                                    '개체번호': num,
                                    '개월수': round(diff_months, 1),
                                    '출생일': b_date.strftime('%Y-%m-%d'),
                                    '양수일': t_date.strftime('%Y-%m-%d')
                                })
                        except: continue
            progress_bar.progress((i + 1) / len(uploaded_files))

        if all_data:
            df = pd.DataFrame(all_data)
            st.success("✅ 모든 분석이 완료되었습니다!")
            st.dataframe(df, use_container_width=True)
            csv = df.to_csv(index=False).encode('utf-8-sig')
            st.download_button("📥 엑셀 결과 다운로드", csv, "cow_result.csv", "text/csv")
        else:
            st.warning("분석 결과 대상 개체가 없습니다.")

