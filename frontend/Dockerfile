# ============================================================
#  frontend 폴더 Dockerfile
# ============================================================
#  ※ Streamlit Cloud 배포 시에는 이 Dockerfile 이 필요 없습니다.
#    (Streamlit Cloud 는 requirements.txt 만 읽어 자동 배포)
#  이 파일은 로컬 테스트 / docker-compose 실행용으로 제공됩니다.

FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 8501

CMD ["streamlit", "run", "streamlit_app.py", "--server.address=0.0.0.0", "--server.port=8501"]
