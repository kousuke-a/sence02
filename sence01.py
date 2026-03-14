import streamlit as st
import pandas as pd
import time
import requests
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from webdriver_manager.chrome import ChromeDriverManager

st.set_page_config(page_title="ナレッジスイート・エクスプローラー", layout="wide")

# --- 設定エリア ---
st.title("📂 ナレッジスイート 法人電話帳抽出ツール")
st.markdown("地域と業種を指定して、安定した法人リストを作成します。")

with st.sidebar:
    st.header("1. 地域選択")
    # 主要な地域を抜粋（必要に応じて追加可能）
    pref_options = {
        "愛知県": "23", "岐阜県": "21", "三重県": "24", "静岡県": "22",
        "東京都": "13", "大阪府": "27", "神奈川県": "14", "千葉県": "12"
    }
    selected_pref = st.selectbox("都道府県を選んでください", list(pref_options.keys()))
    pref_code = pref_options[selected_pref]

    st.header("2. 業種選択")
    # ナレッジスイートの主要カテゴリ
    genre_options = {
        "建設・工事": "103", "製造・加工": "101", "運送・物流": "106",
        "不動産": "108", "卸売・問屋": "102", "情報通信・IT": "105",
        "飲食・宿泊": "111", "医療・福祉": "113"
    }
    selected_genre = st.selectbox("業種を選んでください", list(genre_options.keys()))
    genre_code = genre_options[selected_genre]

    st.header("3. 取得設定")
    target_count = st.number_input("目標件数", 1, 1000, 100)
    wait_time = st.slider("待機時間（秒）", 1.0, 5.0, 2.0)

# --- スクレイピング機能 ---
def scrape_knowledge_suite(p_code, g_code, limit):
    options = webdriver.ChromeOptions()
    options.add_argument('--headless')
    options.add_argument('--no-sandbox')
    options.add_argument('--disable-dev-shm-usage')
    options.add_argument('--lang=ja-JP')
    
    try:
        driver = webdriver.Chrome(options=options)
    except:
        driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)
    
    results = []
    # 検索URLの組み立て
    base_url = f"https://ttj.knowledge-suite.jp/search/pref/{p_code}/genre/{g_code}/"
    page = 1
    
    status_area = st.empty()
    pbar = st.progress(0.0)

    try:
        while len(results) < limit:
            url = f"{base_url}?page={page}"
            driver.get(url)
            time.sleep(wait_time)
            
            # 各企業のブロックを取得
            items = driver.find_elements(By.CSS_SELECTOR, "div.m-search_result_list_item")
            
            if not items:
                st.info("これ以上のデータが見つかりませんでした。")
                break
                
            for item in items:
                try:
                    name = item.find_element(By.TAG_NAME, "h2").text.strip()
                    # 住所と電話番号が含まれるテキストブロックを取得
                    info_text = item.find_element(By.CLASS_NAME, "m-search_result_list_item_address").text
                    
                    # 電話番号の抽出（簡易的な抜き出し）
                    phone = "不明"
                    lines = info_text.split('\n')
                    for line in lines:
                        if "TEL" in line:
                            phone = line.replace("TEL：", "").strip()
                    
                    address = lines[0] if lines else "不明"

                    results.append({
                        "社名": name,
                        "電話番号": phone,
                        "住所": address,
                        "業種": selected_genre
                    })
                    
                    if len(results) >= limit: break
                except:
                    continue
            
            # 進捗更新
            current_len = len(results)
            status_area.text(f"現在 {current_len} 件取得中... (Page: {page})")
            pbar.progress(min(current_len / limit, 1.0))
            
            page += 1
            if page > 50: # 安全のため50ページまでに制限
                break
                
    finally:
        driver.quit()
        
    return pd.DataFrame(results)

# --- 実行セクション ---
if st.button("リスト作成を開始"):
    with st.spinner("ナレッジスイートから抽出中..."):
        df = scrape_knowledge_suite(pref_code, genre_code, target_count)
        
    if not df.empty:
        st.success(f"✅ {len(df)} 件のリストが完成しました！")
        st.dataframe(df)
        
        # 文字化け対策版CSV（Excel対応）
        csv = df.to_csv(index=False, encoding="utf-8-sig")
        st.download_button(
            label="📥 Excel対応CSVを保存",
            data=csv,
            file_name=f"knowledge_suite_{selected_pref}_{selected_genre}.csv",
            mime="text/csv"
        )
    else:
        st.error("データが取得できませんでした。条件を変えて試してください。")