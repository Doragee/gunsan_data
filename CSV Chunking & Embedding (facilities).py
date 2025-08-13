import os
import pandas as pd
import google.generativeai as genai
from supabase import create_client, Client
import time
import numpy as np
# Colab 환경에서는 '보안 비밀' 기능을 사용합니다.
from google.colab import userdata

# --- 프록시 설정 비활성화 ---
# 시스템에 설정된 프록시를 무시하고 직접 연결하도록 설정합니다.
os.environ['http_proxy'] = ''
os.environ['https_proxy'] = ''
os.environ['HTTP_PROXY'] = ''
os.environ['HTTPS_PROXY'] = ''
# -----------------------------------------

# --- 설정 (Colab '보안 비밀'에서 값을 가져옵니다) ---

# Supabase 클라이언트 초기화
# Colab의 '보안 비밀'에 아래 변수들이 설정되어 있어야 합니다:
# SUPABASE_URL, SUPABASE_KEY
url: str = userdata.get("SUPABASE_URL")
key: str = userdata.get("SUPABASE_KEY")
supabase: Client = create_client(url, key)

# Google Generative AI 설정
# Colab의 '보안 비밀'에 GOOGLE_API_KEY가 설정되어 있어야 합니다.
genai.configure(api_key=userdata.get("GOOGLE_API_KEY"))

# 처리할 파일 및 테이블 정보
CSV_FILE_PATH = '/content/publicFacilities.csv'
SUPABASE_TABLE_NAME = 'chatbot_embeddings' 
EMBEDDING_MODEL = 'models/embedding-001'

# --- 스크립트 본문 ---

def generate_embedding(text: str):
    """주어진 텍스트에 대한 임베딩을 생성합니다."""
    try:
        result = genai.embed_content(
            model=EMBEDDING_MODEL,
            content=text,
            task_type="RETRIEVAL_DOCUMENT"
        )
        return result['embedding']
    except Exception as e:
        print(f"  - 임베딩 생성 중 오류 발생: {e}")
        time.sleep(5)
        return None

def create_chunks(row):
    """하나의 행(row)을 받아 의미 단위의 청크(chunk) 리스트를 생성합니다."""
    chunks = []
    facility_name = row.get('facility_name', '해당 시설')

    # 청크 1: 기본 정보 및 위치
    address = str(row.get('road_name_address', '주소 정보 없음'))
    facility_type = str(row.get('facility_type', ''))
    chunks.append({
        "chunk_type": "location_info",
        "content": f"{facility_name}의 종류는 {facility_type}이며, 주소는 {address}입니다."
    })

    # 청크 2: 운영 시간
    weekday_hours = f"{row.get('weekday_opening_hour', '')}~{row.get('weekday_closing_hour', '')}"
    weekend_hours = f"{row.get('weekend_opening_hour', '')}~{row.get('weekend_closing_hour', '')}"
    closed_days = str(row.get('closed_days', '정보 없음'))
    chunks.append({
        "chunk_type": "operating_hours",
        "content": f"{facility_name}의 운영 시간 정보입니다. 주중 운영 시간은 {weekday_hours}, 주말 운영 시간은 {weekend_hours}이며, 휴무일은 {closed_days}입니다."
    })

    # 청크 3: 이용 방법 및 요금
    fee_info = "유료" if row.get('paid_service') == 'Y' else "무료"
    capacity = row.get('capacity', '정보 없음')
    amenities = str(row.get('amenities', '정보 없음'))
    application_method = str(row.get('application_method', '정보 없음'))
    chunks.append({
        "chunk_type": "usage_info",
        "content": f"{facility_name}의 이용 정보입니다. 이 시설은 {fee_info}이며, 수용 가능 인원은 {capacity}명입니다. 주요 편의시설은 {amenities}이며, 신청 방법은 {application_method}입니다."
    })

    # 청크 4: 연락처 정보
    department = str(row.get('department_in_charge', '담당 부서 정보 없음'))
    contact = str(row.get('contact_number', '연락처 정보 없음'))
    chunks.append({
        "chunk_type": "contact_info",
        "content": f"{facility_name}의 연락처 정보입니다. 담당 부서는 {department}이며, 연락처는 {contact}입니다."
    })
    
    return chunks


def process_and_insert_data():
    """CSV 파일을 읽고 청킹하여 데이터를 처리한 후 Supabase에 삽입합니다."""
    try:
        df = pd.read_csv(CSV_FILE_PATH)
        df.replace(np.nan, '', regex=True, inplace=True)
        print(f"'{CSV_FILE_PATH}' 파일에서 총 {len(df)}개의 시설 정보를 읽었습니다.")

        total_chunks = 0
        for index, row in df.iterrows():
            print(f"\n({index + 1}/{len(df)}) 처리 중인 시설: {row['facility_name']}")
            
            chunks = create_chunks(row)
            
            for chunk in chunks:
                content_to_embed = chunk['content']
                embedding = generate_embedding(content_to_embed)
                
                if embedding:
                    data_to_insert = {
                        'source_table': 'publicFacilities',
                        'source_id': f"{row['id']}-{chunk['chunk_type']}",
                        'content': content_to_embed,
                        'embedding': embedding,
                    }
                    response = supabase.table(SUPABASE_TABLE_NAME).upsert(
                        data_to_insert, 
                        on_conflict='source_id'
                    ).execute()
                    
                    total_chunks += 1
                    if hasattr(response, 'error') and response.error:
                        print(f"  - DB 삽입 오류: {response.error}")

    except FileNotFoundError:
        print(f"오류: '{CSV_FILE_PATH}' 파일을 찾을 수 없습니다. Colab에 파일을 업로드했는지, 파일 경로가 올바른지 확인하세요.")
    except Exception as e:
        print(f"처리 중 예상치 못한 오류 발생: {e}")
        
    print(f"\n모든 작업이 완료되었습니다. 총 {total_chunks}개의 청크가 처리되었습니다.")


if __name__ == "__main__":
    process_and_insert_data()
