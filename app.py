import streamlit as st
import easyocr
import pandas as pd
from datetime import datetime
import numpy as np
import cv2

# 1. 페이지 설정 및 제목 (모바일 최적화)
st.set_page_config(page_title="소 양수분석기", layout="wide")
st.title("🐂 소 양수현황 분석기 (모바일/다중 업로드)")

# 2. OCR 엔진 준비
@st.cache_resource
def load_reader():
    # 빈 공간을 하나 만듭니다
    status_placeholder = st.empty()
    status_placeholder.write("🔍 분석 엔진(OCR)을 준비 중입니다. 잠시만 기다려 주세요...")
    
    reader = easyocr.Reader(['ko', 'en'], gpu=False)
    
    # 준비가 끝나면 기존 문구를 지우고 완료 메시지를 띄웁니다
    status_placeholder.success("✅ 엔진 준비 완료! 이제 사진을 올리셔도 됩니다.")
    return reader

# 함수 호출
reader = load_reader()

# 3. 파일 업로드 섹션 (accept_multiple_files=True 설정)
uploaded_files = st.file_uploader(
    "사진들을 여러 장 선택하거나 찍으세요", 
    type=['jpg', 'jpeg', 'png'], 
    accept_multiple_files=True
)

if uploaded_files:
    # 업로드된 파일 개수 표시
    st.info(f"현재 {len(uploaded_files)}장의 사진이 선택되었습니다.")
    
    if st.button("실시간 통합 분석 시작"):
        all_data = []
        
        # 각 파일별로 반복 분석
        for uploaded_file in uploaded_files:
            with st.spinner(f'{uploaded_file.name} 분석 중...'):
                # 이미지 변환
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

                # 데이터 추출 및 만 개월수 계산
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
                                    '출생일': b_date.strftime('%Y-%m-%d'),
                                    '양수일': t_date.strftime('%Y-%m-%d'),
                                    '개월수': round(diff_months, 1)
                                })
                        except:
                            continue

        # 최종 결과 출력
        if all_data:
            df = pd.DataFrame(all_data)
            st.success(f"모든 분석 완료! 총 {len(all_data)}건의 대상 개체를 찾았습니다.")
            st.dataframe(df, use_container_width=True)
            
            # 엑셀(CSV) 다운로드 버튼
            csv = df.to_csv(index=False).encode('utf-8-sig')
            st.download_button("📥 통합 결과 다운로드 (엑셀)", csv, "total_result.csv", "text/csv")
        else:
            st.warning("분석 결과 10개월 이상인 개체가 없습니다.")



