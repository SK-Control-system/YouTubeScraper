FROM python:3.9

# 비상호작용 모드 설정
ENV DEBIAN_FRONTEND=noninteractive

# 작업 디렉토리 설정
WORKDIR /app

# 필요한 패키지 설치
RUN apt-get update && apt-get install -y --no-install-recommends \
    wget \
    unzip \
    curl \
    gnupg \
    # Chromium과 ChromiumDriver 설치
    chromium \
    chromium-driver \
    # 추가로 필요한 라이브러리 설치
    libnss3 \
    libgconf-2-4 \
    libx11-xcb1 \
    libxcomposite1 \
    libxcursor1 \
    libxdamage1 \
    libxi6 \
    libxtst6 \
    libpangocairo-1.0-0 \
    libxrandr2 \
    libasound2 \
    libatk1.0-0 \
    libcups2 \
    libdbus-1-3 \
    libexpat1 \
    libfontconfig1 \
    libfreetype6 \
    libxinerama1 \
    libpangoft2-1.0-0 \
    xdg-utils \
    fonts-liberation \
    libatk-bridge2.0-0 \
    libatspi2.0-0 \
    libgtk-3-0 \
    libvulkan1 \
    libxkbcommon0

# Python 패키지 설치
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 애플리케이션 코드 복사
COPY youtubescraper.py .

# 실행 권한 부여 (필요한 경우)
RUN chmod +x /app/youtubescraper.py

# 컨테이너 실행 명령 설정
CMD ["python3", "youtubescraper.py"]