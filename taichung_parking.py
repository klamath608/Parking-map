import requests
import base64
import pandas as pd
import folium
import time
import json
from datetime import datetime, timedelta, timezone
from folium.plugins import LocateControl
import os

# 載入 secrets，假設你有方式在本地用 JSON 讀取
#with open("secrets.json") as f:
#    secrets = json.load(f)


GITHUB_USER = os.environ["MY_GITHUB_USER"]
REPO_NAME = os.environ["MY_REPO_NAME"]
TOKEN = os.environ["GH_TOKEN"]

FILE_NAME = "taichung_parking_map.html"
GITHUB_API = f"https://api.github.com/repos/{GITHUB_USER}/{REPO_NAME}/contents/{FILE_NAME}"

def generate_map(filepath):
    try:
        tz = timezone(timedelta(hours=8))
        now = datetime.now(tz).strftime("%Y-%m-%d %H:%M:%S")

        url = "https://datacenter.taichung.gov.tw/swagger/OpenData/791a8a4b-ade6-48cf-b3ed-6c594e58a1f1"
        data = requests.get(url).json()
        df = pd.DataFrame(data)

        m = folium.Map(location=[24.14266, 120.6798], zoom_start=17)
        LocateControl(auto_start=False).add_to(m)

        colors = {"1": "red", "0": "green", "2": "gray"}
        for _, row in df.iterrows():
            folium.CircleMarker(
                location=[row['PS_Lat'], row['PS_Lng']],
                radius=6,
                color=colors.get(str(row['status']), 'blue'),
                fill=True,
                fill_opacity=0.7
            ).add_to(m)

        m.get_root().html.add_child(folium.Element(f'''
            <div style="position: fixed; bottom: 10px; left: 10px;
                        width: 250px; height: 30px; background-color: white;
                        z-index: 9999; padding: 5px; border: 1px solid #ccc;
                        font-size: 14px;">
                最後更新時間：{now}
            </div>
        '''))

        m.get_root().header.add_child(folium.Element('<meta http-equiv="refresh" content="60">'))
        m.save(filepath)
        return now
    except Exception as e:
        print("❌ 地圖產生失敗:", e)
        return None

def upload_to_github(filepath, commit_msg):
    headers = {
        "Authorization": f"token {TOKEN}",
        "Accept": "application/vnd.github.v3+json"
    }

    with open(filepath, "rb") as f:
        content = base64.b64encode(f.read()).decode("utf-8")

    sha = None
    res = requests.get(GITHUB_API, headers=headers)
    if res.status_code == 200:
        sha = res.json()["sha"]

    payload = {
        "message": commit_msg,
        "content": content,
        "branch": "main"
    }
    if sha:
        payload["sha"] = sha

    put_res = requests.put(GITHUB_API, headers=headers, json=payload)
    if put_res.status_code in [200, 201]:
        print("✅ 成功上傳 GitHub")
    else:
        print("❌ 上傳失敗:", put_res.json())

if __name__ == "__main__":
    start_time = time.time()
    duration_seconds = 5 * 60 * 60  # 5小時

    while True:
        now = generate_map(FILE_NAME)
        if now:
            upload_to_github(FILE_NAME, f"自動更新地圖：{now}")
        else:
            print("跳過上傳，因為地圖生成失敗")
        
        time.sleep(60)  # 等60秒再繼續下一輪

        elapsed = time.time() - start_time
        if elapsed > duration_seconds:
            print("執行時間超過5小時，程式結束。")
            break
