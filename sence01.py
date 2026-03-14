import streamlit as st
import pandas as pd
import time
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from webdriver_manager.chrome import ChromeDriverManager

st.set_page_config(page_title="営業リストメーカーPro", layout="wide")

# --- UI設定 ---
st.title("📂 法人リスト作成ツール (ナレッジスイート対応)")
st.info("※サーバーへの負荷を抑えるため、適度な待機時間を設けて実行してください。")

with st.sidebar:
    st.header("1. 地域選択")
    pref_options = {
        "愛知県": "23", "岐阜県": "21", "三重県": "24", "静岡県": "22",
        "東京都": "13", "大阪府": "27", "神奈川県": "14", "千葉県": "12"
    }
    selected_pref = st.selectbox("都道府県", list(pref_options.keys()))
    pref_code = pref_options[selected_pref]

    st.header("2. 業種選択")
    genre_options = {
        "製造・加工": "101", "建設・工事": "103", "運送・物流": "106",
        "不動産": "108", "卸売・問屋": "102", "情報通信・IT": "105",
        "飲食・宿泊": "111", "医療・福祉": "113"
    }
    selected_genre = st.selectbox("業種", list(genre_options.keys()))
    genre_code = genre_options[selected_genre]

    st.header("3. 取得設定")
    target_count = st.number_input("目標件数", 1, 1000, 50)
    wait_sec = st.slider("ページ切替待機（秒）", 1.0, 10.0, 3.0)

# --- スクレイピング関数 ---
def scrape_knowledge_suite(p_code, g_code, limit):
    options = webdriver.ChromeOptions()
    options.add_argument('--headless')
    options.add_argument('--no-sandbox')
    options.add_argument('--disable-dev-shm-usage')
    options.add_argument('--disable-gpu')
    options.add_argument('--lang=ja-JP')
    
    # ステルス設定（人間が操作しているように見せかける）
    options.add_experimental_option("excludeSwitches", ["enable-automation"])
    options.add_experimental_option('useAutomationExtension', False)
    ua = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"
    options.add_argument(f'user-agent={ua}')
    
    try:
        driver = webdriver.Chrome(options=options)
        # navigator.webdriver フラグを隠す
        driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
    except:
        service = Service(ChromeDriverManager().install())
        driver = webdriver.Chrome(service=service, options=options)
    
    results = []
    base_url = f"https://ttj.knowledge-suite.jp/search/pref/{p_code}/genre/{g_code}/"
    page = 1
    
    status_text = st.empty()
    pbar = st.progress(0.0)

    try:
        while len(results) < limit:
            url = f"{base_url}?page={page}"
            driver.get(url)
            time.sleep(wait_sec)
            
            # リストアイテムの取得
            items = driver.find_elements(By.CSS_SELECTOR, "div.m-search_result_list_item")
            
            if not items:
                break
                
            for item in items:
                try:
                    name = item.find_element(By.TAG_NAME, "h2").text.strip()
                    # 住所と電話番号のブロック
                    info_area = item.find_element(By.CLASS_NAME, "m-search_result_list_item_address").text
                    
                    phone = "不明"
                    address = "不明"
                    
                    lines = info_area.split('\n')
                    if lines:
                        address = lines[0] # 最初の行が住所
                        for line in lines:
                            if "TEL" in line:
                                phone = line.replace("TEL：", "").strip()

                    results.append({
                        "社名": name,
                        "電話番号": phone,
                        "住所": address,
                        "業種": selected_genre
                    })
                    
                    if len(results) >= limit: break
                except:
                    continue
            
            # 画面表示更新
            status_text.text(f"📊 {len(results)} 件取得済み (Page: {page})")
            pbar.progress(min(len(results) / limit, 1.0))
            
            page += 1
            # サイト負荷軽減のため1秒追加待機
            time.sleep(1)

    finally:
        driver.quit()
        
    return pd.DataFrame(results)

# --- ボタン処理 ---
if st.button("🚀 リスト作成を開始"):
    if not (pref_code and genre_code):
        st.error("地域と業種を選択してください。")
    else:
        with st.spinner("データを取得しています..."):
            df = scrape_knowledge_suite(pref_code, genre_code, target_count)
            
        if not df.empty:
            st.success(f"✅ {len(df)} 件のリストを作成しました！")
            st.dataframe(df)
            
            # Excel用文字化け対策版CSV
            csv_data = df.to_csv(index=False, encoding="utf-8-sig")
            st.download_button(
                label="📥 Excel対応CSVを保存",
                data=csv_data,
                file_name=f"list_{selected_pref}_{selected_genre}.csv",
                mime="text/csv"
            )
        else:
            st.warning("データが見つかりませんでした。待機時間を長めにして再度お試しください。")
