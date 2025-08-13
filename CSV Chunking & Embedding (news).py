import os
import pandas as pd
import google.generativeai as genai
from supabase import create_client, Client
import time
import numpy as np
# Colab 환경에서는 '보안 비밀' 기능을 사용합니다.
from google.colab import userdata

# --- 프록시 설정 비활성화 ---
# Colab 환경에서는 보통 필요 없지만, 만일을 위해 포함합니다.
os.environ['http_proxy'] = ''
os.environ['https_proxy'] = ''
os.environ['HTTP_PROXY'] = ''
os.environ['HTTPS_PROXY'] = ''
# -----------------------------------------

# --- 설정 (Colab '보안 비밀'에서 값을 가져옵니다) ---

# Supabase 클라이언트 초기화
url: str = userdata.get("SUPABASE_URL")
key: str = userdata.get("SUPABASE_KEY")
supabase: Client = create_client(url, key)

# Google Generative AI 설정
genai.configure(api_key=userdata.get("GOOGLE_API_KEY"))

# 처리할 파일 및 테이블 정보
CSV_FILE_PATH = '/content/gunsan_news.csv'
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

def process_and_insert_data():
    """CSV 파일을 읽고 데이터를 처리하여 Supabase에 삽입합니다."""
    try:
        df = pd.read_csv(CSV_FILE_PATH)
        df.replace(np.nan, '', regex=True, inplace=True)
        print(f"'{CSV_FILE_PATH}' 파일에서 총 {len(df)}개의 뉴스 기사를 읽었습니다.")

        for index, row in df.iterrows():
            title = str(row.get('title', ''))
            summary = str(row.get('summary', ''))
            spot = str(row.get('spot', ''))
            
            if not title and not summary:
                print(f"\n({index + 1}/{len(df)}) 건너뛰기: 제목과 요약이 모두 비어있습니다.")
                continue

            content_to_embed = f"뉴스 제목: {title}\n내용 요약: {summary}"
            if spot:
                content_to_embed += f"\n관련 장소: {spot}"
            
            print(f"\n({index + 1}/{len(df)}) 처리 중인 뉴스: {title}")
            
            embedding = generate_embedding(content_to_embed)
            
            if embedding:
                data_to_insert = {
                    'source_table': 'gunsan_news',
                    'source_id': str(row['id']),
                    'content': content_to_embed,
                    'embedding': embedding,
                }
                
                response = supabase.table(SUPABASE_TABLE_NAME).upsert(
                    data_to_insert, 
                    on_conflict='source_id'
                ).execute()
                
                if hasattr(response, 'error') and response.error:
                    print(f"  - DB 삽입 오류: {response.error}")

    except FileNotFoundError:
        print(f"오류: '{CSV_FILE_PATH}' 파일을 찾을 수 없습니다. Colab에 파일을 업로드했는지 확인하세요.")
    except Exception as e:
        print(f"처리 중 예상치 못한 오류 발생: {e}")
        
    print(f"\n모든 작업이 완료되었습니다.")

if __name__ == "__main__":
    process_and_insert_data()
