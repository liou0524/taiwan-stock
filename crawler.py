import requests
import json
from datetime import datetime
import re

def get_taifex_data():
    # 台灣期交所三大法人期貨留倉查詢 API (當日)
    url = "https://www.taifex.com.tw/cht/3/callsAndPutsDate"
    # 使用今日日期
    today_str = datetime.now().strftime("%Y/%m/%d")
    payload = {
        'queryDate': today_str,
        'marketCode': '0',
        'commodityId': 'TX' # 臺股期貨(大台)
    }
    
    try:
        response = requests.post("https://www.taifex.com.tw/cht/3/futThreeBigProductInsti", data=payload)
        html = response.text
        
        # 使用簡單的正規表達式抓取網頁表格中的數字（免去安裝複雜解析庫）
        # 依序尋找：外資、投信、自營商的 多方、空方、多空淨額部位
        patterns = {
            'dealers': r'自營商.*?(\d+,?\d*).*?(\d+,?\d*).*?(-?\d+,?\d*).*?(-?\d+,?\d*).*?(-?\d+,?\d*).*?(-?\d+,?\d*)',
            'sitc': r'投信.*?(\d+,?\d*).*?(\d+,?\d*).*?(-?\d+,?\d*).*?(-?\d+,?\d*).*?(-?\d+,?\d*).*?(-?\d+,?\d*)',
            'foreign': r'外資.*?(\d+,?\d*).*?(\d+,?\d*).*?(-?\d+,?\d*).*?(-?\d+,?\d*).*?(-?\d+,?\d*).*?(-?\d+,?\d*)'
        }
        
        result = {'date': today_str}
        clean_html = re.sub(r'\s+', '', html) # 移除所有空白換行方便比對
        
        for name, pattern in patterns.items():
            match = re.search(pattern, clean_html)
            if match:
                # 留倉的多方(第7欄)、空方(第9欄)、淨額(第11欄)
                # 在網頁表格中對應的是後面的未平倉量數據
                # 簡化解析：直接取未平倉多、空、淨
                # 註：期交所網頁結構為：交易量(多、空、淨)、未平倉量(多、空、淨)
                # 因此抓取最後三組數字
                match_data = re.findall(r'-?\d+,?\d+', match.group(0))
                long_val = int(match_data[-3].replace(',', ''))
                short_val = int(match_data[-2].replace(',', ''))
                net_val = int(match_data[-1].replace(',', ''))
                
                result[name] = {'long': long_val, 'short': short_val, 'net': net_val}
            else:
                return None # 如果今天沒開盤或沒資料就跳出
                
        return result
    except Exception as e:
        print(f"Error: {e}")
        return None

def update_web():
    new_data = get_taifex_data()
    if not new_data:
        print("今日未開盤或無法取得資料。")
        return
        
    # 讀取原本的 index.html
    with open("index.html", "r", encoding="utf-8") as f:
        html_content = f.read()
        
    # 找出舊的數據並解析
    start_tag = 'const rawData = '
    end_tag = '; // 初始空陣列，爬蟲會把資料填在這裡'
    
    start_idx = html_content.find(start_tag) + len(start_tag)
    end_idx = html_content.find(end_tag)
    
    old_data_str = html_content[start_idx:end_idx]
    try:
        data_list = json.loads(old_data_str)
    except:
        data_list = []
        
    # 檢查重複，同一天不重複塞資料
    if not any(d['date'] == new_data['date'] for d in data_list):
        data_list.append(new_data)
        # 只保留最近 10 筆歷史紀錄，避免檔案無限變大
        if len(data_list) > 10:
            data_list.pop(0)
            
    # 把新數據寫回 index.html
    new_data_str = json.dumps(data_list, ensure_ascii=False)
    new_html = html_content[:start_idx] + new_data_str + html_content[end_idx:]
    
    with open("index.html", "w", encoding="utf-8") as f:
        f.write(new_html)
    print("網頁數據更新成功！")

if __name__ == "__main__":
    update_web()
