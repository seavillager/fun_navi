from fun_navi_common import (
    configure_logging, initialize_driver, login, navigate_to_page, parse_datetime_with_weekday
)
import csv
import os
from datetime import datetime
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC



logger = configure_logging()
driver = initialize_driver()

# 環境変数を読み込み
FACILITY_NAMES = os.getenv("FACILITY_NAMES", "").split(",")

# 予約履歴を記録
reservation_results = []

# 現在の日付と時刻を取得
now = datetime.now()

def fetch_reservations():
    """予約履歴を取得して記録する"""
    existing_reservations = []
    try:
        while True:
            reservation_rows = driver.find_elements(By.XPATH, '//table[@class="striped01"]/tbody/tr')
            if not reservation_rows:
                logger.info("予約履歴が見つかりませんでした。")
                break

            for row in reservation_rows:
                columns = row.find_elements(By.TAG_NAME, "td")
                if len(columns) >= 5:
                    facility_name = columns[2].text.strip()
                    start_time = columns[0].text.strip()
                    end_time = columns[1].text.strip()
                    reservation_number = columns[3].text.strip()
                    status = columns[4].text.strip()

                    start_datetime = parse_datetime_with_weekday(start_time)
                    if not start_datetime:
                        continue

                    if start_datetime > now:
                        existing_reservations.append({
                            "facility_name": facility_name,
                            "start_time": start_time,
                            "end_time": end_time,
                            "reservation_number": reservation_number,
                            "status": status
                        })

            try:
                next_page_button = driver.find_element(By.XPATH, '//a[contains(@href, "do_NextPage")]')
                next_page_button.click()
                logger.info("次のページへ遷移します...")
                WebDriverWait(driver, 10).until(
                    EC.presence_of_element_located((By.CLASS_NAME, "section.view-list.first-child.last-child"))
                )
            except Exception:
                logger.info("全ての予約履歴を読み込みました。")
                break

    except Exception as e:
        logger.error(f"予約履歴の取得中にエラーが発生しました: {e}")

    return existing_reservations


try:
    # ログイン
    login(driver, logger)

    # 予約履歴ページに移動
    navigate_to_page(driver, logger, '//a[contains(@href, "do_ReserveInfoListGeneral")]') 

    reservation_results = fetch_reservations()


finally:
    driver.quit()

    # CSVに出力
    with open("reservation_results.csv", "w", encoding="utf-8", newline="") as file:
        writer = csv.DictWriter(
            file,
            fieldnames=["start_time", "end_time", "facility_name", "reservation_number", "status"],
        )
        writer.writeheader()
        writer.writerows(reservation_results)

    logger.info("予約履歴をCSVに出力しました。")
