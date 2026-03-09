import streamlit as st
import easyocr
import pandas as pd
from datetime import datetime
import numpy as np
import cv2

# 1. 페이지 설정 및 제목 (모바일 최적화)
st.set_page_config(page_title="소 양수분석기", layout="wide")
st.title("🐂 소 양수현황 분석기 (모바일)")

# 2. OCR 엔진 준비 (서버 성능 고려)
@st.cache_resource
def load_reader():
    # 서버 환경(CPU)에 맞춰 GPU 사용은 끕니다.
    return easyocr.Reader(['ko', 'en'], gpu=False)

reader = load_reader()

# 3. 파일 업로드 섹션 (카메라 연동 가능)
uploaded_file = st.file_uploader("사진을 찍거나 파일을 선택하세요", type=['jpg', 'jpeg', 'png'])

if uploaded_file is not None:
    # 화면에 찍은 사진 미리보기
    st.image(uploaded_file, caption='업로드 완료', use_container_width=True)
    
    if st.button("실시간 분석 시작"):
        all_data = []
        with st.spinner('글자를 읽고 계산하는 중입니다...'):
            # 이미지 변환 로직
            file_bytes = np.frombuffer(uploaded_file.read(), np.uint8)
            img = cv2.imdecode(file_bytes, cv2.IMREAD_COLOR)
            result = reader.readtext(img)
            
            # 줄 단위 데이터 처리 로직
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

            # 데이터 정렬 및 만 개월수 계산
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
                                '개체번호': num,
                                '출생일': b_date.strftime('%Y-%m-%d'),
                                '양수일': t_date.strftime('%Y-%m-%d'),
                                '개월수': round(diff_months, 1)
                            })
                    except:
                        continue

        # 결과 출력
        if all_data:
            df = pd.DataFrame(all_data)
            st.success(f"총 {len(all_data)}건을 찾았습니다!")
            st.dataframe(df, use_container_width=True)
            
            # 엑셀(CSV) 다운로드 버튼
            csv = df.to_csv(index=False).encode('utf-8-sig')
            st.download_button("📥 결과 다운로드 (엑셀저장)", csv, "result.csv", "text/csv")
        else:
            st.warning("10개월 이상인 개체를 찾지 못했습니다. 사진을 다시 확인해주세요.")
