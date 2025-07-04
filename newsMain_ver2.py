import streamlit as st
import datetime
from selenium import webdriver
from tempfile import mkdtemp
from loguru import logger

from bs4 import BeautifulSoup
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import pandas as pd
from datetime import datetime as datime
import time

def main():
    genre = st.radio(
        "아래의 옵션을 선택하세요.",
        ["부고", "인사"],
        index=0,
    )
    uploaded_file = st.file_uploader("엑셀 파일을 업로드하세요", type=["xlsx", "xls"])
    media_list =[]
    if uploaded_file is not None:
        # 업로드된 파일을 데이터프레임으로 읽기
        df = pd.read_excel(uploaded_file)
        # 데이터프레임을 배열로 변환
        media_list  = df.values.flatten()

    left, middle = st.columns([3, 1], vertical_alignment="bottom")
    test = ""
    # 오늘 날짜 가져오기
    today = datetime.date.today()
    doneYn = "N"
    # 7일 전 날짜 가져오기
    seven_days_ago = today - datetime.timedelta(days=7)
    with left:
        stDate = st.date_input("시작일자", value=seven_days_ago)
        endDate = st.date_input("종료일자", value=today)
    with middle:
        if st.button("Crawl news"):
            if media_list is None or len(media_list) == 0:
                st.warning("엑셀 파일을 업로드하여 유효한 언론사를 제공해주세요.")
            else:
                with st.spinner('Wait for it...'):
                    print(stDate)
                    print(endDate)
                    print(media_list)
                    print("--------------------------------")
                    start_time = time.perf_counter()
                    progress_text = "Operation in progress. Please wait."
                    news_articles = getNewsData2(stDate, endDate, genre,  media_list)
                    end_time = time.perf_counter()
                    time_cost = end_time - start_time
                    logger.info(f' 소요 시간: {time_cost}')
                    df = pd.DataFrame(news_articles)
                    doneYn = "Y"

    if 'Y'  in doneYn:
        st.success('Done!')
        csv = convert_df(df)
        current_time = datime.now().strftime("%Y%m%d%H%M")
        file_name = f"{current_time}_{genre}_data"
        st.download_button(
            "Press Download",
            csv,
            file_name + ".csv",
            key="download_csv")



@st.cache_data
def convert_df(df):
   return df.to_csv(index=False).encode('utf-8-sig')


def getNewsData2(stDate, endDate, genre, media_list):
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
    }
    news_list = []
    seen = set()

    start_date = stDate.strftime("%Y.%m.%d")
    end_date = endDate.strftime("%Y.%m.%d")

    # Selenium WebDriver 초기화


    options = webdriver.ChromeOptions()
    options.add_argument('--no-sandbox')
    options.add_argument("--disable-gpu")
    options.add_argument("--window-size=1280x1696")
    options.add_argument(
        "user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36")
    options.add_argument("single-process")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--disable-dev-tools")
    options.add_argument("--no-zygote")
    options.add_argument(f"--user-data-dir={mkdtemp()}")
    options.add_argument(f"--data-path={mkdtemp()}")
    options.add_argument(f"--disk-cache-dir={mkdtemp()}")
    options.add_experimental_option('excludeSwitches', ['enable-logging'])
    options.add_experimental_option("excludeSwitches", ["enable-automation"])
    options.add_experimental_option("useAutomationExtension", False)
    options.add_experimental_option("detach", False)
    options.add_argument('headless=new')

    driver = webdriver.Chrome(options=options)
    wait = WebDriverWait(driver, 10)
    for index, media in enumerate(media_list):
        if genre == '인사':
            query = f'"[인사] {media}"'
        else:
            query = f'[부고] {media}'

        driver.get(
            f"https://search.naver.com/search.naver?where=news&query={query}&sm=tab_opt&sort=0&photo=0&field=0&pd=3&ds={start_date}&de={end_date}&docid=&related=0&mynews=0&office_type=0&office_section_code=0&news_office_checked=is_sug_officeid=0&office_category=0&service_area=0")

        # 페이지 끝까지 스크롤 다운
        SCROLL_PAUSE_TIME = 2
        last_height = driver.execute_script("return document.body.scrollHeight")

        while True:
            # Scroll down to bottom
            driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")

            # Wait to load page
            time.sleep(SCROLL_PAUSE_TIME)

            # Calculate new scroll height and compare with last scroll height
            new_height = driver.execute_script("return document.body.scrollHeight")
            if new_height == last_height:
                break
            last_height = new_height

     
        # BeautifulSoup을 사용하여 HTML 파싱
        soup = BeautifulSoup(driver.page_source, "html.parser")

        try:
            all_divs = wait.until(
                EC.presence_of_all_elements_located((By.CSS_SELECTOR, 'ul.list_news div'))
            )

            filtered_divs = [
                div for div in all_divs
                if "sds-comps-vertical-layout" in div.get_attribute("class") and
                "sds-comps-full-layout" in div.get_attribute("class") and
                "BHQHyn3Flk5rFBSacJkG" in div.get_attribute("class")
            ]

            logger.info(f"뉴스 내부의 필터링된 태그 div 개수: {len(filtered_divs)}")

            for div in filtered_divs:
                title, content, press = None, None, None

                try:
                    # 제목 추출
                    try:
                        title_elem = div.find_element(By.CSS_SELECTOR, 'a.o8ZxSqp8BlHYDNRhXpaz > span')
                        title = title_elem.text.strip()
                    except Exception as err:
                        logger.error(f"Error: 제목을 찾을 수 없습니다. {str(err)}", exc_info=True)

                    # 본문 content 추출
                    try:
                        content_elem = div.find_element(By.CSS_SELECTOR, '.sds-comps-text-type-body1')
                        content = content_elem.text.strip()
                    except Exception as err:
                        logger.error(f"Error: 본문 내용을 찾을 수 없습니다. {str(err)}", exc_info=True)

                    # 언론사 추출
                    try:
                        news_press_element = div.find_element(By.CSS_SELECTOR, 'a.I1ImuwGyum46_fkF0p9U > span')
                        press = news_press_element.text.strip()
                    except Exception as err:
                        logger.error(f"Error: 언론사 정보를 찾을 수 없습니다. {str(err)}", exc_info=True)

                    # 언론사 이름이 title에 포함되어 있는지 확인
                    def check_title(title, media):
                        return media in title

                    # 결과 확인
                    if check_title(title, media):
                        identifier = (title, content) 
                        if identifier not in seen:
                            news_list.append({
                                "title": title,
                                "content": content,
                                "press": press if press else "정보 없음"
                            })
                            seen.add(identifier)
                     
                except Exception as e:
                    logger.warning(f"뉴스 div 파싱 중 오류 발생: {e}", exc_info=True)

        except Exception as e:
            logger.error(f"뉴스 리스트 전체 파싱 실패: {e}", exc_info=True)

    driver.quit()
    return news_list

if __name__ == '__main__':
    main()
