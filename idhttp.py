from selenium import webdriver
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
import requests
import time
import re
import json

class YouTubeScraper:
    def __init__(self, search_keyword, server_url):
        chrome_options = Options()
        chrome_options.add_argument("--headless")  # Headless 모드 설정
        chrome_options.add_argument("--disable-gpu")
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--disable-dev-shm-usage")
        chrome_options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36")
        self.driver = webdriver.Chrome(options=chrome_options)
        self.wait = WebDriverWait(self.driver, 20)
        self.search_keyword = search_keyword
        self.server_url = server_url
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

    def send_to_server(self):
        headers = {"Content-Type": "application/json"}
        try:
            response = requests.post(self.server_url, json={"items": self.unique_videos}, headers=headers)
            if response.status_code == 200:
                print("데이터 전송 성공:", response.json())
            else:
                print("데이터 전송 실패:", response.status_code, response.text)
        except Exception as e:
            print("서버 전송 중 에러 발생:", e)

    def scrape(self):
        try:
            self.setup_driver()
            self.search()
            self.collect_videos()
            self.send_to_server()
        finally:
            self.driver.quit()

if __name__ == "__main__":
    server_url = "http://localhost:30001/api/videos"
    scraper = YouTubeScraper("음악", server_url)
    scraper.scrape()
