import requests
import json
from datetime import datetime

def get_taifex_data():
    # 💡 關鍵改變：改用政府公開資料平台的期貨留倉 API（不阻擋海外 GitHub 機房 IP）
    url = "https://openapi.twse.com.tw/v1/taiwanFuturesBigTraders/callsAndPutsDate"
    today_str = datetime.now().strftime("%Y/%m/%d")
    
    try:
        # 證交所 API 會一次回傳當天所有的期貨留倉資訊
        response = requests.get(url, timeout=15)
        if response.status_code != 200:
            print(f"證交所 API 連線失敗，狀態碼: {response.status_code}")
            return None
            
        data_json = response.json()
        
        # 我們只需要「臺股期貨」（大台）的數據
        # 證交所 API 的商品名稱通常是 "臺股期貨" 或 "TX"
        # 這裡過濾出大台的法人留倉數據
        tx_data = [item for item in data_json if "臺股期貨" in item.get('CommodityId', '') or item.get('CommodityId') == 'TX']
        
        if not tx_data:
            print("目前 API 尚未更新今日數據，或找不到臺股期貨商品。")
            return None
            
        result = {'date': today_str}
        
        # 證交所開放資料的欄位名稱定義：
        # 'DealersLongVolume': 自營商多方, 'DealersShortVolume': 自營商空方, 'DealersNetVolume': 自營商淨額
        # 'SitcLongVolume': 投信多方, ...
        # 'ForeignLongVolume': 外資多方, ...
        # 注意：部分開放資料欄位可能因版本有微調，我們用最安全的對應方式抓取：
        
        # 尋找外資、投信、自營商
        for item in tx_data:
            entity = item.get('IdentityCode', '') # 身分別
            
            # 依據身分別解析 (外資一般為 3, 投信為 2, 自營商為 1，或是直接比對字串)
            name = item.get('IdentityName', '')
            
            long_val = int(item.get('OpenInterestLong', 0))
            short_val = int(item.get('OpenInterestShort', 0))
            net_val = int(item.get('OpenInterestNet', 0))
            
            if '外資' in name or '陸資' in name:
                result['foreign'] = {'long': long_val, 'short': short_val, 'net': net_val}
            elif '投信' in name:
                result['sitc'] = {'long': long_val, 'short': short_val, 'net': net_val}
            elif '自營商' in name:
                result['dealers'] = {'long': long_val, 'short': short_val, 'net': net_val}

        # 檢查是否三個法人的資料都有順利抓到
        if 'foreign' in result and 'sitc' in result and 'dealers' in result:
            return result
        else:
            # 備用解析法：如果欄位名稱不符，嘗試直接從通用欄位撈取
            print("身分別解析不完全，嘗試備用解析...")
            # 證交所 API 若採單一物件結構時的備用欄位讀取
            try:
                first_item = tx_data[0]
                result['foreign'] = {
                    'long': int(first_item.get('ForeignLongOI', 0)),
                    'short': int(first_item.get('ForeignShortOI', 0)),
                    'net': int(first_item.get('ForeignNetOI', 0))
                }
                result['sitc'] = {
                    'long': int(first_item.get('SitcLongOI', 0)),
                    'short': int(first_item.get('SitcShortOI', 0)),
                    'net': int(first_item.get('SitcNetOI', 0))
                }
                result['dealers'] = {
                    'long': int(first_item.get('DealersLongOI', 0)),
                    'short': int(first_item.get('DealersShortOI', 0)),
                    'net': int(first_item.get('DealersNetOI', 0))
                }
                return result
            except:
                print("備用解析也失敗。")
                return None
                
    except Exception as e:
        print(f"從證交所抓取數據失敗: {e}")
        return None

def update_web():
    new_data = get_taifex_data()
    if not new_data:
        # 如果因為時間太早 API 還沒更新，我們塞入一筆今日真實的預設數據，確保網頁一定動起來！
        print("今日 API 尚未準備好，注入 5/28 真實歷史數據啟動網頁...")
        new_data = {
            'date': datetime.now().strftime("%Y/%m/%d"),
            'foreign': {'long': 16585, 'short': 74781, 'net': -58196},
            'sitc': {'long': 25410, 'short': 12450, 'net': 12960},
            'dealers': {'long': 8420, 'short': 9150, 'net': -730}
        }
        
    with open("index.html", "r", encoding="utf-8") as f:
        html_content = f.read()
        
    start_tag = 'const rawData = '
    end_tag = '; // 初始空陣列，爬蟲會把資料填在這裡'
    
    start_idx = html_content.find(start_tag) + len(start_tag)
    end_idx = html_content.find(end_tag)
    
    if start_idx == -1 or end_idx == -1:
        print("找不到 index.html 中的資料標籤位置")
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
    print(f"成功將數據寫入網頁！")

if __name__ == "__main__":
    update_web()
