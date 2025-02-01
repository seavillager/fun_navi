import os
import logging
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.service import Service
from selenium.common.exceptions import TimeoutException, NoSuchElementException
from datetime import datetime
from dotenv import load_dotenv
import holidays
import getpass

last_date = None
last_facility_name  = None

# 環境変数の読み込み
load_dotenv(override=True)

# ログレベルの設定
def configure_logging():
    log_level = os.getenv("LOG_LEVEL", "INFO").upper()
    logging.basicConfig(
        level=getattr(logging, log_level, logging.INFO),
        format="%(asctime)s - %(levelname)s - %(message)s",
        handlers=[
            logging.FileHandler("fun_navi_log.log"),
            logging.StreamHandler()
        ]
    )
    return logging.getLogger(__name__)


# WebDriver の初期化
def initialize_driver():
    chrome_driver_path = os.getenv("CHROME_DRIVER_PATH")
    options = webdriver.ChromeOptions()
    return webdriver.Chrome(service=Service(chrome_driver_path), options=options)


# ログイン処理
def login(driver, logger):
    login_url = os.getenv("LOGIN_URL", "https://fun-navi.net/frpc010g.jsp")
    user_id = os.getenv("USER_ID")
    password = os.getenv("PASSWORD")

    if not user_id:
        user_id = input("fun naviのユーザーIDを入力してください: ")
    if not password:
        password = getpass.getpass("fun naviのパスワードを入力してください: ")

    try:
        driver.get(login_url)
        WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.ID, "a11y-01")))
        driver.find_element(By.ID, "a11y-01").send_keys(user_id)
        driver.find_element(By.ID, "a11y-02").send_keys(password)
        driver.find_element(By.XPATH, '//input[@type="submit" and @value="ログイン"]').click()
        WebDriverWait(driver, 10).until(EC.url_contains("FRPC010G_LoginAction.do"))
        logger.info("ログイン成功")
    except Exception as e:
        logger.error(f"ログインに失敗しました: {e}")
        raise


# 日付フォーマット関数
def parse_datetime_with_weekday(date_str):
    try:
        date_str_cleaned = date_str.split("(")[0].strip() + " " + date_str.split(" ")[1].strip()
        return datetime.strptime(date_str_cleaned, "%Y/%m/%d %H:%M")
    except ValueError as e:
        logging.error(f"日付のフォーマットエラー: {date_str} - {e}")
        return None


# 土日祝日判定
def is_weekend_or_holiday(date):
    year = date.year
    japan_holidays = holidays.Japan(years=year)
    return date.weekday() in [5, 6] or date in japan_holidays


# ページ遷移の共通関数
def navigate_to_page(driver, logger, xpath):
    try:
        WebDriverWait(driver, 10).until(
            EC.invisibility_of_element_located((By.ID, "loading"))
        )
        button = WebDriverWait(driver, 10).until(EC.element_to_be_clickable((By.XPATH, xpath)))

        button.click()
        logger.info("ページ遷移に成功しました。")
        
    except Exception as e:
        logger.error(f"ページ遷移に失敗しました: {e}")
        raise

# 空き状況チェックの共通関数
def search_availability(driver, logger, facility_name, date):
    """指定した施設名と日付で空き状況を検索"""
    global last_date  # グローバル変数を参照
    global last_facility_name  # グローバル変数を参照
    try:
        if isinstance(date, str):
            date = datetime.strptime(date, "%Y/%m/%d")

        WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.ID, "keyword")))

        # 前回と異なる施設名の場合のみ入力
        if facility_name != last_facility_name:
            driver.find_element(By.ID, "keyword").clear()
            driver.find_element(By.ID, "keyword").send_keys(facility_name)
            last_facility_name = facility_name

        # 前回と異なる日付の場合のみ入力
        if date != last_date:
            driver.find_element(By.ID, "useDateArea").clear()
            driver.find_element(By.ID, "useDateArea").send_keys(date.strftime("%Y/%m/%d"))
            last_date = date   

        driver.find_element(By.ID, "search").click()

        # ローディングが非表示になるまで待機
        WebDriverWait(driver, 10).until(
            EC.invisibility_of_element_located((By.ID, "loading"))
        )
        # 検索結果の確認
        WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.CLASS_NAME, "status-area47")))

        # 空き状況の確認
        available_buttons = driver.find_elements(By.CLASS_NAME, "time-rsv-available-btn")
        available = len(available_buttons) > 0

        if available_buttons:
            logger.info(f"施設: {facility_name}, 日付: {date.strftime('%Y/%m/%d')} は予約可能")
        else:
            logger.info(f"施設: {facility_name}, 日付: {date.strftime('%Y/%m/%d')} は空きなし")

        return available


    except Exception as e:
        logger.error(f"施設: {facility_name}, 日付: {date.strftime('%Y/%m/%d')} の検索中にエラーが発生: {str(e)}")
        return False

# 抽選申し込みの共通関数
def apply_for_facility_lottery(driver, logger, facility_name, date):
    """指定した施設名と日付で空き状況を検索"""
    global last_date  # グローバル変数を参照
    global last_facility_name  # グローバル変数を参照
    """申し込み用の電話番号を取得"""
    PHONE_NUMBER = os.getenv("PHONE_NUMBER")
    reservation_data = {"facility_name": facility_name, "date": date, "reservation_number": "", "status": "Success"}

    try:
        if isinstance(date, str):
            date = datetime.strptime(date, "%Y/%m/%d")

        WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.ID, "keyword")))

        # 前回と異なる施設名の場合のみ入力
        if facility_name != last_facility_name:
            driver.find_element(By.ID, "keyword").clear()
            driver.find_element(By.ID, "keyword").send_keys(facility_name)
            last_facility_name = facility_name

        # 前回と異なる日付の場合のみ入力
        if date != last_date:
            driver.find_element(By.ID, "useDateArea").clear()
            driver.find_element(By.ID, "useDateArea").send_keys(date.strftime("%Y/%m/%d"))
            last_date = date   

        # 絞り込みボタンをクリック
        # ローディングが消えるまで待機
        WebDriverWait(driver, 15).until(
            EC.invisibility_of_element_located((By.ID, "loading"))
        )
        # 絞り込みボタンをクリック
        WebDriverWait(driver, 10).until(
            EC.element_to_be_clickable((By.ID, "search"))
        ).click()

        # ローディングが非表示になるまで待機
        WebDriverWait(driver, 10).until(
            EC.invisibility_of_element_located((By.ID, "loading"))
        )

        try:
            # 検索結果の確認
            WebDriverWait(driver, 3).until(EC.presence_of_element_located((By.CLASS_NAME, "time-drawing-available-btn")))
            button = driver.find_element(By.CLASS_NAME, "time-drawing-available-btn")
            button.click()
            logger.info(f"ボタンをクリックしました: {date}")

            # 注意事項の同意チェック
            WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.ID, "a11y-06")))
            checkbox = driver.find_element(By.ID, "a11y-06")
            if not checkbox.is_selected():
                checkbox.click()
                print("注意事項への同意チェックボックスをチェックしました。")

            # 緊急連絡先を入力
            input_field = driver.find_element(By.ID, "a11y-01")
            input_field.clear()
            input_field.send_keys(PHONE_NUMBER)
            print(f"電話番号 '{PHONE_NUMBER}' を入力しました。")

            # 次へボタンをクリック（確認画面）
            driver.find_element(By.ID, "nextPageBtn").click()
            print("次へ（確認画面）のボタンをクリックしました。")

            # 確認画面で次へボタンをクリック
            WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.XPATH, "//input[@value='次へ（完了画面）']"))).click()
            print("次へ（完了画面）のボタンをクリックしました。")

            # 完了画面から予約番号を取得
            WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.CLASS_NAME, "first-child.last-child")))
            reservation_number = driver.find_element(By.CLASS_NAME, "first-child.last-child").text.split("：")[1].strip()
            reservation_data["reservation_number"] = reservation_number
            print(f"予約番号を取得しました: {reservation_number}")

            # 受付完了後に「施設一覧に戻る」をクリック
            WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.XPATH, "//input[@value='施設一覧に戻る']"))).click()
            print("施設一覧に戻るボタンをクリックしました。")

            return reservation_data

        except TimeoutException:
            # タイムアウトの場合は、申し込み済み（抽選待ち）の状態か確認
            try:
                # 「抽選待ち」の表示を持つ要素を確認
                applied_status = driver.find_element(By.XPATH, "//span[@class='rsv-status-text' and text()='抽選待ち']")
                logger.info(f"施設: {facility_name}, 日付: {date.strftime('%Y/%m/%d')} は既に抽選申し込み済みです。ステータス: {applied_status.text}")
                # ここで申し込み済みの結果を記録する処理を追加する
                reservation_data["status"] = "Already applied"
                return reservation_data
            except NoSuchElementException:
                logger.info(f"施設: {facility_name}, 日付: {date.strftime('%Y/%m/%d')} は予約状況が不明です。")
                reservation_data["status"] = f"Failed: {str(e)}"
                return reservation_data

    except Exception as e:
        logger.error(f"施設: {facility_name}, 日付: {date.strftime('%Y/%m/%d')} の検索中にエラーが発生: {str(e)}")
        reservation_data["status"] = f"Failed: {str(e)}"
        return reservation_data

