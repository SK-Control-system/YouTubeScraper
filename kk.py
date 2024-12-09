from selenium import webdriver
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import time

# Chrome WebDriver 설정
driver = webdriver.Chrome()

# YouTube 열기 및 검색 실행
driver.get("https://www.youtube.com/")
time.sleep(2)

# 검색어 입력 및 검색 실행
search_keyword = "게임"
search_box = driver.find_element(By.NAME, "search_query")
search_box.send_keys(search_keyword)
search_box.send_keys(Keys.RETURN)
time.sleep(2)

# 필터 옵션 선택 기능 정의
wait = WebDriverWait(driver, 10)

def apply_filter(xpath):
    # 필터 버튼 클릭
    filter_button = wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, "#filter-button > ytd-button-renderer > yt-button-shape > button")))
    filter_button.click()
    time.sleep(1)
    # 필터 옵션 클릭 (XPath 사용)
    option = wait.until(EC.element_to_be_clickable((By.XPATH, xpath)))
    driver.execute_script("arguments[0].click();", option)
    time.sleep(1)

try:
    # 각 필터 적용: 업로드 날짜, 라이브, 조회수 순서
    apply_filter("/html/body/ytd-app/ytd-popup-container/tp-yt-paper-dialog/ytd-search-filter-options-dialog-renderer/div[2]/ytd-search-filter-group-renderer[1]/ytd-search-filter-renderer[2]/a/div/yt-formatted-string")
    apply_filter("/html/body/ytd-app/ytd-popup-container/tp-yt-paper-dialog/ytd-search-filter-options-dialog-renderer/div[2]/ytd-search-filter-group-renderer[4]/ytd-search-filter-renderer[1]/a/div/yt-formatted-string")
    apply_filter("/html/body/ytd-app/ytd-popup-container/tp-yt-paper-dialog/ytd-search-filter-options-dialog-renderer/div[2]/ytd-search-filter-group-renderer[5]/ytd-search-filter-renderer[3]/a/div/yt-formatted-string")

    # 동영상 로드 및 조건부 스크롤로 고유 동영상 확보
    unique_videos = []
    seen_urls = set()
    scroll_attempts = 0
    max_scrolls = 3  # 최적화를 위해 스크롤 횟수 제한

    while len(unique_videos) < 5 and scroll_attempts < max_scrolls:
        video_elements = driver.find_elements(By.XPATH, '//*[@id="video-title"]')
        
        for video in video_elements:
            title = video.get_attribute("title")
            url = video.get_attribute("href")
            if url and url not in seen_urls:
                seen_urls.add(url)
                unique_videos.append((title, url))
            if len(unique_videos) >= 5:
                break
        
        # 스크롤 시도 증가
        if len(unique_videos) < 5:
            scroll_attempts += 1
            driver.execute_script("window.scrollTo(0, document.documentElement.scrollHeight);")
            time.sleep(2)  # 페이지 로딩 대기

    # 상위 5개 고유 동영상 출력
    for idx, (title, url) in enumerate(unique_videos, start=1):
        print(f"{idx}. 제목: {title}")
        print(f"   URL: {url}")
        print("-")

finally:
    # 드라이버 종료
    driver.quit()
