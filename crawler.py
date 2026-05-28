import requests
import json
from datetime import datetime
import re

def get_taifex_data():
    url = "https://www.taifex.com.tw/cht/3/futThreeBigProductInsti"
    today_str = datetime.now().strftime("%Y/%m/%d")
    payload = {
        'queryDate': today_str,
        'marketCode': '0',
        'commodityId': 'TX'  # 臺股期貨
    }
    
    try:
        response = requests.post(url, data=payload)
        html = response.text
        
        # 清理網頁原始碼中的空白與換行，方便比對
        clean_html = re.sub(r'\s+', '', html)
        
        # 檢查今天是不是沒開盤（如果網頁顯示查無資料）
        if "查無資料" in html or "請輸入欲查詢之日期" in html:
            print("期交所今日查無資料，可能未開盤。")
            return None

        # 定義三大法人的對應關鍵字
        legal_entities = {
            'dealers': '自營商',
            'sitc': '投信',
            'foreign': '外資'
        }
        
        result = {'date': today_str}
        
        for key, name in legal_entities.items():
            # 這段正規表達式會精確抓取該法人該列（tr）裡面的所有數字欄位
            # 期交所表格結構：前6個數字是「交易量」的多空淨，後3個數字是「未平倉量」的多、空、淨
            row_pattern = f'<tr><td>{name}</td>.*?</tr>'
            row_match = re.search(row_pattern, clean_html)
            
            if row_match:
                # 撈出該行所有的數字（包含負號與逗號）
                numbers = re.findall(r'-?\d+,?\d+', row_match.group(0))
                if len(numbers) >= 9:
                    # 取最後 3 個數字，分別是未平倉的多方、空方、淨額
                    long_val = int(numbers[-3].replace(',', ''))
                    short_val = int(numbers[-2].replace(',', ''))
                    net_val = int(numbers[-1].replace(',', ''))
                    
                    result[key] = {'long': long_val, 'short': short_val, 'net': net_val}
                else:
                    print(f"解析 {name} 數據欄位數量不足")
                    return None
            else:
                print(f"找不到 {name} 的數據列")
                return None
                
        return result
    except Exception as e:
        print(f"抓取或解析失敗: {e}")
        return None

def update_web():
    new_data = get_taifex_data()
    if not new_data:
        print("今日未能成功取得數據。")
        return
        
    with open("index.html", "r", encoding="utf-8") as f:
        html_content = f.read()
        
    start_tag = 'const rawData = '
    end_tag = '; // 初始空陣列，爬蟲會把資料填在這裡'
    
    start_idx = html_content.find(start_tag) + len(start_tag)
    end_idx = html_content.find(end_tag)
    
    if start_idx == -1 or end_idx == -1:
        print("找不到 index.html 中的資料標籤位置，請檢查網頁原始碼。")
        return
        
    old_data_str = html_content[start_idx:end_idx]
    try:
        data_list = json.loads(old_data_str)
    except:
        data_list = []
        
    if not any(d['date'] == new_data['date'] for d in data_list):
        data_list.append(new_data)
        if len(data_list) > 10:
            data_list.pop(0)
            
    new_data_str = json.dumps(data_list, ensure_ascii=False)
    new_html = html_content[:start_idx] + new_data_str + html_content[end_idx:]
    
    with open("index.html", "w", encoding="utf-8") as f:
        f.write(new_html)
    print(f"成功將 {new_data['date']} 的數據寫入網頁！")

if __name__ == "__main__":
    update_web()
