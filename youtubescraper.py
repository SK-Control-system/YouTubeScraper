import schedule
import time
from selenium import webdriver
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from kafka import KafkaProducer
import logging
import re
import json
import os
from concurrent.futures import ThreadPoolExecutor

# 로깅 설정
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")

class YouTubeScraper:
    def __init__(self, search_keyword):
        chrome_options = Options()
        chrome_options.add_argument("--headless")  # Headless 모드 설정
        chrome_options.add_argument("--disable-gpu")
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--disable-dev-shm-usage")
        chrome_options.add_argument(
            "user-agent=Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
        )
        chrome_options.binary_location = os.getenv("CHROMIUM_PATH", "/usr/bin/chromium")
        service = Service(os.getenv("CHROMEDRIVER_PATH", "/usr/bin/chromedriver"))

        retries = 3
        while retries > 0:
            try:
                self.driver = webdriver.Chrome(service=service, options=chrome_options)
                break
            except Exception as e:
                retries -= 1
                logging.error(f"Retrying driver setup ({3 - retries}/3). Error: {e}")
                time.sleep(5)

        if retries == 0:
            logging.critical("Failed to initialize driver after 3 attempts. Exiting...")
            raise RuntimeError("Driver initialization failed.")

        self.wait = WebDriverWait(self.driver, 20)
        self.search_keyword = search_keyword
        self.unique_videos = []
        self.seen_ids = set()

        # KafkaProducer 설정
        kafka_broker = os.getenv("KAFKA_BROKER", "kafka-svc:9093")
        self.producer = KafkaProducer(
            bootstrap_servers=kafka_broker,
            value_serializer=lambda v: json.dumps(v, ensure_ascii=False).encode("utf-8"),
        )

    def setup_driver(self):
        try:
            logging.info(f"Setting up the driver and navigating to YouTube for keyword '{self.search_keyword}'...")
            self.driver.get("https://www.youtube.com/")
            self.wait.until(EC.presence_of_element_located((By.TAG_NAME, "body")))
        except Exception as e:
            logging.error(f"Error setting up the driver: {e}")
            raise

    def search(self):
        try:
            logging.info(f"Searching for videos with keyword: {self.search_keyword}")
            search_box = self.driver.find_element(By.NAME, "search_query")
            search_box.send_keys(self.search_keyword)
            search_box.send_keys(Keys.RETURN)
            time.sleep(2.5)
        except Exception as e:
            logging.error(f"Error during search for keyword '{self.search_keyword}': {e}")
            raise

    def apply_filter(self, xpath):
        try:
            logging.info(f"Applying filter with XPath: {xpath}")
            filter_button = self.wait.until(
                EC.element_to_be_clickable(
                    (By.CSS_SELECTOR, "#filter-button > ytd-button-renderer > yt-button-shape > button")
                )
            )
            filter_button.click()
            time.sleep(2.5)
            option = self.wait.until(EC.element_to_be_clickable((By.XPATH, xpath)))
            self.driver.execute_script("arguments[0].click();", option)
            time.sleep(2.5)
        except Exception as e:
            logging.error(f"Error applying filter with XPath '{xpath}': {e}")
            raise

    def collect_videos(self):
        logging.info("Collecting video data...")
        retries = 3
        max_videos = 5

        while retries > 0:
            try:
                video_elements = self.driver.find_elements(By.XPATH, '//ytd-video-renderer')
                logging.info(f"Found {len(video_elements)} video elements.")

                for video in video_elements:
                    if len(self.unique_videos) >= max_videos:
                        break  # 최대 비디오 수를 초과하면 종료

                    try:
                        title_element = video.find_element(By.XPATH, ".//a[@id='video-title']")
                        channel_image_element = WebDriverWait(video, 10).until(
                            EC.presence_of_element_located((By.XPATH, ".//a[@id='channel-thumbnail']//img"))
                        )

                        title = title_element.get_attribute("title")
                        url = title_element.get_attribute("href")
                        channel_image = channel_image_element.get_attribute("src") if channel_image_element.get_attribute("src") else "https://example.com/default-image.png"

                        if url and url not in self.seen_ids:
                            self.seen_ids.add(url)

                            video_id_match = re.search(r"v=([^&]+)", url)
                            if video_id_match:
                                video_id = video_id_match.group(1)
                                self.unique_videos.append({
                                    "videoId": video_id,
                                    "videoTitle": title,
                                    "channelImage": channel_image
                                })
                    except Exception as e:
                        logging.warning(f"Error processing video: {e}")

                # 수정된 부분: 데이터가 부족하더라도 스크롤 종료 후 데이터 전송
                if not video_elements or len(self.unique_videos) >= max_videos:
                    break

                # 데이터가 부족하면 스크롤
                self.scroll_down()
            except Exception as e:
                retries -= 1
                logging.error(f"Error collecting videos. Retries left: {retries}. Error: {e}")
                if retries == 0:
                    break

    def scroll_down(self):
        try:
            self.driver.execute_script("window.scrollTo(0, document.documentElement.scrollHeight);")
            self.wait.until(
                EC.presence_of_element_located(
                    (By.XPATH, '//ytd-video-renderer')
                )
            )
        except Exception as e:
            logging.error(f"Error scrolling down: {e}")
            raise

    def send_result_to_kafka(self, topic="categoryLiveList"):
        logging.info("Preparing to send data to Kafka...")
        result = {
            "category": self.search_keyword,
            "items": self.unique_videos if self.unique_videos else [{"message": "데이터가 없습니다"}],
        }

        max_retries = 5
        retry_count = 0

        while retry_count < max_retries:
            try:
                future = self.producer.send(topic, value=result)
                metadata = future.get(timeout=10)
                logging.info(f"Data successfully sent to Kafka topic '{metadata.topic}' at partition {metadata.partition}, offset {metadata.offset}.")
                self.producer.flush()
                return
            except Exception as e:
                retry_count += 1
                logging.error(f"Attempt {retry_count}/{max_retries} failed to send data to Kafka: {e}")
                time.sleep(2)

        logging.critical(f"Failed to send data to Kafka after {max_retries} attempts.")

    def scrape(self):
        try:
            self.setup_driver()
            self.search()
            # 필터 추가
            self.apply_filter(
                "/html/body/ytd-app/ytd-popup-container/tp-yt-paper-dialog/ytd-search-filter-options-dialog-renderer/div[2]/ytd-search-filter-group-renderer[2]/ytd-search-filter-renderer[1]/a/div/yt-formatted-string"
            )
            self.apply_filter(
                "/html/body/ytd-app/ytd-popup-container/tp-yt-paper-dialog/ytd-search-filter-options-dialog-renderer/div[2]/ytd-search-filter-group-renderer[4]/ytd-search-filter-renderer[1]/a/div/yt-formatted-string"
            )
            self.apply_filter(
                "/html/body/ytd-app/ytd-popup-container/tp-yt-paper-dialog/ytd-search-filter-options-dialog-renderer/div[2]/ytd-search-filter-group-renderer[5]/ytd-search-filter-renderer[3]/a/div/yt-formatted-string"
            )
            self.collect_videos()
        finally:
            self.driver.quit()


def scrape_category(category):
    scraper = YouTubeScraper(category)
    scraper.scrape()
    scraper.send_result_to_kafka()


def run_scraper():
    categories = ["정치", "리그오브레전드", "메이플스토리", "배틀그라운드", "음악"]
    with ThreadPoolExecutor(max_workers=5) as executor:
        executor.map(scrape_category, categories)


# 5분마다 실행
schedule.every(5).minutes.do(run_scraper)

if __name__ == "__main__":
    try:
        logging.info("Scheduler is running. Press Ctrl+C to stop.")

        # 즉시 실행
        run_scraper()

        while True:
            schedule.run_pending()
            time.sleep(1)
    except KeyboardInterrupt:
        logging.warning("Scheduler interrupted by user. Exiting gracefully.")
    except Exception as e:
        logging.critical(f"Unexpected error: {e}", exc_info=True)
    finally:
        logging.info("Scheduler has stopped.")
