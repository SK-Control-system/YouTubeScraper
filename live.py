import os
import pytchat
import pafy
import pandas as pd
from transformers import AutoTokenizer, AutoModelForSequenceClassification, pipeline

video_id = '1_KM02tUaI8'  # [LIVE] YTN 뉴스 채널
file_path = './runninmen_youtube.csv'

# KcBERT 모델과 토크나이저 설정
model_name = "beomi/kcbert-base"
tokenizer = AutoTokenizer.from_pretrained(model_name)
model = AutoModelForSequenceClassification.from_pretrained(model_name)

# 감정 분석 파이프라인 설정
sentiment_analyzer = pipeline("sentiment-analysis", model=model, tokenizer=tokenizer)

# 실시간 댓글 가져오기
empty_frame = pd.DataFrame(columns=['댓글 작성자', '댓글 내용', '댓글 작성 시간', '감정', '신뢰도'])
chat = pytchat.create(video_id=video_id)

# 댓글 저장 리스트 및 카운터 초기화
comments_data = []
counter = 0  # 현재까지 수집된 댓글 개수

while chat.is_alive():
    try:
        data = chat.get()
        items = data.items
        for c in items:
            # 댓글 내용과 작성자 정보 출력
            print(f"{c.datetime} [{c.author.name}]- {c.message}")
            data.tick()
            
            # 댓글 감정 분석 수행
            sentiment = sentiment_analyzer(c.message)
            sentiment_label = sentiment[0]['label']
            sentiment_score = sentiment[0]['score']
            
            # 콘솔에 감정 분석 결과와 현재 카운터 출력
            counter += 1
            print(f"감정 분석 결과: {sentiment_label} (신뢰도: {sentiment_score}) [{counter}/100]\n")
            
            # 데이터프레임에 저장할 데이터 추가
            data_row = {
                '댓글 작성자': c.author.name,
                '댓글 내용': c.message,
                '댓글 작성 시간': c.datetime,
                '감정': sentiment_label,
                '신뢰도': sentiment_score
            }
            comments_data.append(data_row)
            
            # 100개 모일 때마다 CSV 파일에 저장
            if counter % 100 == 0:
                df = pd.DataFrame(comments_data)
                df.to_csv(file_path, mode='a', header=False, index=False, encoding='utf-8-sig')
                comments_data = []  # 저장 후 리스트 초기화
                print(f"{counter}개의 댓글이 저장되었습니다. (CSV 파일에 기록 완료)\n")
        
    except KeyboardInterrupt:
        # 강제로 중단했을 때 남은 데이터를 저장
        if comments_data:
            df = pd.DataFrame(comments_data)
            df.to_csv(file_path, mode='a', header=False, index=False, encoding='utf-8-sig')
            print(f"종료 전 마지막으로 {len(comments_data)}개의 댓글이 저장되었습니다.\n")
        chat.terminate()
        break

# 저장된 데이터를 확인
df = pd.read_csv(file_path, names=['댓글 작성자', '댓글 내용', '댓글 작성 시간', '감정', '신뢰도'])
print(df.head(30))
