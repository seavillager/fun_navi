from fun_navi_common import (
    configure_logging, initialize_driver, login, search_availability, is_weekend_or_holiday
)
from datetime import datetime, timedelta
from dateutil.relativedelta import relativedelta
import os
import csv
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.service import Service

logger = configure_logging()
driver = initialize_driver()

# 環境変数を読み込み
FACILITY_NAMES = os.getenv("FACILITY_NAMES", "").split(",")
SEARCH_START_DATE = os.getenv("SEARCH_START_DATE")
SEARCH_END_DATE = os.getenv("SEARCH_END_DATE")
HOLIDAYS_ONLY = os.getenv("HOLIDAYS_ONLY", "false").lower() == "true"

# 空き状況を記録
availability_results = {}


def get_dates_range(start_date, end_date):
    """
    開始日と終了日で指定された範囲の日付リストを生成。
    除外日と追加日を考慮する。
    """
    # .env から除外日と追加日を取得
    excluded_dates = os.getenv("EXCLUDED_DATES", "").split(",")
    additional_dates = os.getenv("ADDITIONAL_DATES", "").split(",")
    
    # 除外日と追加日を datetime オブジェクトに変換
    excluded_dates = {datetime.strptime(date.strip(), "%Y/%m/%d") for date in excluded_dates if date.strip()}
    additional_dates = {datetime.strptime(date.strip(), "%Y/%m/%d") for date in additional_dates if date.strip()}

    current_date = start_date
    dates = []

    # 指定された期間の日付をリストに追加
    while current_date <= end_date:
        if HOLIDAYS_ONLY and not is_weekend_or_holiday(current_date):
            current_date += timedelta(days=1)
            continue

        if current_date not in excluded_dates:
            dates.append(current_date.strftime("%Y/%m/%d"))

        current_date += timedelta(days=1)

    # 追加日をリストに追加し、重複を排除しつつ昇順にソート
    all_dates = {datetime.strptime(date, "%Y/%m/%d") for date in dates}
    final_dates = sorted(all_dates.union(additional_dates) - excluded_dates)

    return [date.strftime("%Y/%m/%d") for date in final_dates]


try:
    # ログイン
    login(driver, logger)

    # 日付範囲を取得
    start_date = datetime.strptime(SEARCH_START_DATE, "%Y/%m/%d")
    end_date = datetime.strptime(SEARCH_END_DATE, "%Y/%m/%d")
    dates = get_dates_range(start_date, end_date)
    last_facility_name = None
    last_date = None

    current_date = start_date
    for date in dates:
        current_date = datetime.strptime(date, "%Y/%m/%d")
        for facility_name in FACILITY_NAMES:
            facility_name = facility_name.strip()
            if facility_name not in availability_results:
                availability_results[facility_name] = {}

            logger.debug(f"施設: {facility_name}, 日付: {current_date.strftime('%Y/%m/%d')} を検索中...")
            availability = search_availability(driver, logger, facility_name, current_date )

            availability_results[facility_name][current_date.strftime("%Y/%m/%d")] = "○" if availability else "×"

finally:
    driver.quit()

# CSVに出力
with open("availability_results.csv", "w", encoding="utf-8", newline="") as file:
    logger.debug("availability_results:", availability_results)

    # 全ての日付を取得（重複を除く）
    all_dates = sorted({date for dates in availability_results.values() for date in dates})

    # CSVの書き込み
    with open("availability_matrix.csv", "w", encoding="utf-8", newline="") as file:
        writer = csv.writer(file)
        
        # ヘッダーを書き込む
        writer.writerow(["施設名"] + all_dates)
        
        # 各施設の行を書き込む
        for facility_name, dates_availability in availability_results.items():
            row = [facility_name] + [dates_availability.get(date, "×") for date in all_dates]
            writer.writerow(row)    

    logger.info("空き状況をavailability_matrix.csvに出力しました")


