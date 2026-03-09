import streamlit as st
import easyocr
import pandas as pd
from datetime import datetime
import numpy as np
import cv2

st.set_page_config(page_title="소 양수현황 분석기", layout="wide")
st.title("🐂 소 양수현황 분석기 (만 10개월 이상 추출)")

# 1. OCR 엔진 준비
@st.cache_resource
def load_reader():
    return easyocr.Reader(['ko', 'en'])

reader = load_reader()

# 2. 파일 업로드 섹션
uploaded_files = st.file_uploader("양수신고 현황 사진들을 선택하세요", type=['jpg', 'jpeg', 'png'], accept_multiple_files=True)

if uploaded_files:
    all_data = []
    
    if st.button("분석 시작"):
        for uploaded_file in uploaded_files:
            with st.spinner(f'{uploaded_file.name} 읽는 중...'):
                # 이미지 읽기
                file_bytes = np.frombuffer(uploaded_file.read(), np.uint8)
                img = cv2.imdecode(file_bytes, cv2.IMREAD_COLOR)
                result = reader.readtext(img)
                
                # 줄 단위 데이터 처리 (기존 로직 적용)
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
                                    '파일명': uploaded_file.name, '개체번호': num,
                                    '출생일': b_date.strftime('%Y-%m-%d'),
                                    '양수일': t_date.strftime('%Y-%m-%d'),
                                    '개월수': round(diff_months, 1)
                                })
                        except: continue

        if all_data:
            df = pd.DataFrame(all_data)
            st.success(f"총 {len(all_data)}건의 대상 개체를 찾았습니다!")
            st.dataframe(df) # 화면에 표 보여주기
            
            # 엑셀 다운로드 버튼
            csv = df.to_csv(index=False).encode('utf-8-sig')
            st.download_button("📥 엑셀 결과 다운로드", csv, "analysis_result.csv", "text/csv")
        else:
            st.warning("조건에 맞는 개체를 찾지 못했습니다.")