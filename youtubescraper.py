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
        chrome_options.binary_location = os.getenv("CHROMIUM_PATH", "/usr/bin/chromium")  # 개선: 환경 변수로 경로 설정
        service = Service(os.getenv("CHROMEDRIVER_PATH", "/usr/bin/chromedriver"))  # 개선: 환경 변수로 경로 설정

        retries = 3  # 드라이버 초기화 재시도 횟수
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

    def scrape(self):
        try:
            self.setup_driver()
            self.search()
            self.collect_videos()
        finally:
            self.driver.quit()

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

    def collect_videos(self):
        logging.info(f"Collecting video data for keyword '{self.search_keyword}'...")
        retries = 3
        max_videos = 5

        while len(self.unique_videos) < max_videos and retries > 0:
            try:
                video_elements = self.driver.find_elements(By.XPATH, '//ytd-video-renderer')
                logging.info(f"Found {len(video_elements)} video elements for '{self.search_keyword}'.")
                
                for video in video_elements:
                    title_element = video.find_element(By.XPATH, ".//a[@id='video-title']")
                    channel_image_element = video.find_element(By.XPATH, ".//a[@id='channel-thumbnail']//img")

                    title = title_element.get_attribute("title")
                    url = title_element.get_attribute("href")
                    channel_image = channel_image_element.get_attribute("src")

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

                    if len(self.unique_videos) >= max_videos:
                        break

                if len(self.unique_videos) < max_videos:
                    self.scroll_down()
            except Exception as e:
                retries -= 1
                logging.error(f"Error collecting videos. Retries left: {retries}. Error: {e}")

    def scroll_down(self):
        try:
            logging.info("Scrolling down to load more videos...")
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
        logging.info(f"Preparing to send data to Kafka for category '{self.search_keyword}'...")
        result = {
            "category": self.search_keyword,
            "items": self.unique_videos,
        }
        if not result["items"]:
            logging.warning(f"No data collected for '{self.search_keyword}'. Skipping Kafka send.")
            return

        max_retries = 5
        retry_count = 0

        while retry_count < max_retries:
            try:
                future = self.producer.send(topic, value=result)
                metadata = future.get(timeout=10)
                logging.info(f"Data for '{self.search_keyword}' successfully sent to Kafka topic '{metadata.topic}' at partition {metadata.partition}, offset {metadata.offset}.")
                self.producer.flush()
                return
            except Exception as e:
                retry_count += 1
                logging.error(f"Attempt {retry_count}/{max_retries} failed to send data to Kafka: {e}")
                time.sleep(2)

        logging.critical(f"Failed to send data to Kafka for '{self.search_keyword}' after {max_retries} attempts.")

def scrape_category(category):
    scraper = YouTubeScraper(category)
    scraper.scrape()
    scraper.send_result_to_kafka()

def run_scraper():
    categories = ["정치", "경제", "스포츠", "음악", "IT"]
    with ThreadPoolExecutor(max_workers=5) as executor:
        executor.map(scrape_category, categories)

# 2분마다 실행
schedule.every(2).minutes.do(run_scraper)

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
