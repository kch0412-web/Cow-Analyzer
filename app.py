import streamlit as st
import easyocr
import pandas as pd
from datetime import datetime
import numpy as np
import cv2

# 페이지 설정
st.set_page_config(page_title="소 분석기", layout="wide")
st.title("🐂 소 양수현황 분석기 (초경량 버전)")

# 모델을 캐싱하여 서버 메모리 점유를 최소화합니다
@st.cache_resource
def get_reader():
    return easyocr.Reader(['ko', 'en'], gpu=False)

# 사진 업로드 (여러 장 가능)
uploaded_files = st.file_uploader("사진을 선택하세요", type=['jpg', 'jpeg', 'png'], accept_multiple_files=True)

if uploaded_files:
    st.info(f"현재 {len(uploaded_files)}장의 사진이 대기 중입니다.")
    
    if st.button("🚀 실시간 분석 시작"):
        all_data = []
        # 버튼을 누른 순간에만 엔진을 가동합니다
        reader = get_reader()
        
        for uploaded_file in uploaded_files:
            with st.spinner(f"{uploaded_file.name} 처리 중..."):
                file_bytes = np.frombuffer(uploaded_file.read(), np.uint8)
                img = cv2.imdecode(file_bytes, cv2.IMREAD_COLOR)
                result = reader.readtext(img)
                
                # 데이터 정리 로직
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

        if all_data:
            df = pd.DataFrame(all_data)
            st.success("분석 완료!")
            st.dataframe(df, use_container_width=True)
            csv = df.to_csv(index=False).encode('utf-8-sig')
            st.download_button("📥 엑셀 결과 저장", csv, "result.csv", "text/csv")
