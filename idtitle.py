from selenium import webdriver
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
import time
import re
import json

class YouTubeScraper:
    def __init__(self, search_keyword):
        chrome_options = Options()
        chrome_options.add_argument("--headless")  # Headless 모드 설정
        chrome_options.add_argument("--disable-gpu")
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--disable-dev-shm-usage")
        chrome_options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36")
        self.driver = webdriver.Chrome(options=chrome_options)
        self.wait = WebDriverWait(self.driver, 20)
        self.search_keyword = search_keyword
        self.unique_videos = []
        self.seen_ids = set()

    def setup_driver(self):
        self.driver.get("https://www.youtube.com/")
        self.wait.until(EC.presence_of_element_located((By.TAG_NAME, "body")))
        time.sleep(10)  # JavaScript 실행 대기 시간

    def search(self):
        search_box = self.driver.find_element(By.NAME, "search_query")
        search_box.send_keys(self.search_keyword)
        search_box.send_keys(Keys.RETURN)
        time.sleep(2.5)

    def apply_filter(self, xpath):
        filter_button = self.wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, "#filter-button > ytd-button-renderer > yt-button-shape > button")))
        filter_button.click()
        time.sleep(5)
        option = self.wait.until(EC.element_to_be_clickable((By.XPATH, xpath)))
        self.driver.execute_script("arguments[0].click();", option)
        time.sleep(5)

    def collect_videos(self):
        while len(self.unique_videos) < 10:
            video_elements = self.driver.find_elements(By.XPATH, '//*[@id="video-title"]')
            for video in video_elements:
                title = video.get_attribute("title")
                url = video.get_attribute("href")
                if url:
                    video_id_match = re.search(r"v=([^&]+)", url)
                    if video_id_match:
                        video_id = video_id_match.group(1)
                        if video_id not in self.seen_ids:
                            self.seen_ids.add(video_id)
                            self.unique_videos.append({"videoId": video_id, "videoTitle": title})
                if len(self.unique_videos) >= 10:
                    break
            if len(self.unique_videos) < 10:
                self.driver.execute_script("window.scrollTo(0, document.documentElement.scrollHeight);")
                time.sleep(2.5)

    def scrape(self):
        try:
            self.setup_driver()
            self.search()
            self.apply_filter("/html/body/ytd-app/ytd-popup-container/tp-yt-paper-dialog/ytd-search-filter-options-dialog-renderer/div[2]/ytd-search-filter-group-renderer[2]/ytd-search-filter-renderer[1]/a/div/yt-formatted-string")  # 동영상 필터 적용
            self.apply_filter("/html/body/ytd-app/ytd-popup-container/tp-yt-paper-dialog/ytd-search-filter-options-dialog-renderer/div[2]/ytd-search-filter-group-renderer[4]/ytd-search-filter-renderer[1]/a/div/yt-formatted-string")  # 정렬 기준: 조회수
            self.apply_filter("/html/body/ytd-app/ytd-popup-container/tp-yt-paper-dialog/ytd-search-filter-options-dialog-renderer/div[2]/ytd-search-filter-group-renderer[5]/ytd-search-filter-renderer[3]/a/div/yt-formatted-string")  # 라이브 중인 영상
            self.collect_videos()
        finally:
            self.driver.quit()

    def get_result(self):
        return {
            "category": "music",
            "items": self.unique_videos
        }

if __name__ == "__main__":
    scraper = YouTubeScraper("음악")
    scraper.scrape()
    result = scraper.get_result()
    print(json.dumps(result, indent=2, ensure_ascii=False))