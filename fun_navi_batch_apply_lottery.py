from fun_navi_common import (
    configure_logging, initialize_driver, login, apply_for_facility_lottery, is_weekend_or_holiday
)
import os
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.service import Service
from dotenv import load_dotenv
import holidays
from datetime import datetime, timedelta
from dateutil.relativedelta import relativedelta  # dateutilライブラリを使用
import csv


logger = configure_logging()
driver = initialize_driver()

# 環境変数を読み込み
FACILITY_NAMES = os.getenv("PRR_FACILITY_NAMES", "").split(",")
HOLIDAYS_ONLY = os.getenv("PRR_HOLIDAYS_ONLY", "false").lower() == "true"

# 空き状況を記録
# availability_results = {}

# 予約履歴を記録
reservation_results = []

def get_dates_range(start_date, end_date):
    """
    開始日と終了日で指定された範囲の日付リストを生成。
    除外日と追加日を考慮する。
    """
    # .env から除外日と追加日を取得
    excluded_dates = os.getenv("PRR_EXCLUDED_DATES", "").split(",")
    additional_dates = os.getenv("PRR_ADDITIONAL_DATES", "").split(",")
    
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
    # 施設名が空の場合にエラーを発生
    if not FACILITY_NAMES or all(name.strip() == "" for name in FACILITY_NAMES):
        raise ValueError("FACILITY_NAMESが空です。環境変数に少なくとも1つの施設名を指定してください。")

    # ログイン
    login(driver, logger)

    # 現在の日付と時刻を取得
    now = datetime.now()
    two_months_later = now + relativedelta(months=2)

    # ２ヶ月後の年と月を取得
    year_two_months_later = two_months_later.year
    month_two_months_later = two_months_later.month


    print(f"現在の年月: {now.year}年{now.month}月")
    print(f"2か月後の年月: {year_two_months_later}年{month_two_months_later}月")

    # 指定した月の最初の日と最後の日
    start_date = datetime(year_two_months_later, month_two_months_later, 1)
    if month_two_months_later == 12:
        end_date = datetime(year_two_months_later + 1, 1, 1) - timedelta(days=1)
    else:
        end_date = datetime(year_two_months_later, month_two_months_later + 1, 1) - timedelta(days=1)

    dates = get_dates_range(start_date, end_date)
    last_facility_name = None
    last_date = None

    current_date = start_date
    for date in dates:
        current_date = datetime.strptime(date, "%Y/%m/%d")
        print(f"予約日: {current_date} の予約を試みます")
        for facility_name in FACILITY_NAMES:
            print(f"施設: {facility_name} の予約を試みます")
            facility_name = facility_name.strip()

            reservation_data = apply_for_facility_lottery(driver, logger, facility_name, date)
            # 予約結果を記録
            reservation_results.append(reservation_data)

finally:
    # ブラウザを閉じる
    driver.quit()

    # CSVに結果を出力
    with open("reservation_results.csv", mode="w", encoding="utf-8", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=["facility_name", "date", "reservation_number", "status"])
        writer.writeheader()
        writer.writerows(reservation_results)

    print("予約結果をreservation_results.csvに出力しました。")
