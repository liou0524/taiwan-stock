import requests
import io
import pandas as pd
import json
from datetime import datetime, timedelta

def get_today_live_data():
    """第一軌：抓取今日最新即時數據"""
    url = "https://openapi.twse.com.tw/v1/taiwanFuturesBigTraders/callsAndPutsDate"
    today_str = datetime.now().strftime("%Y/%m/%d")
    try:
        response = requests.get(url, timeout=15)
        print(f"[Log] 證交所 API 連線狀態碼: {response.status_code}")
        if response.status_code != 200: return None
        data_json = response.json()
        tx_data = [item for item in data_json if "臺股期貨" in item.get('CommodityId', '') or item.get('CommodityId') == 'TX']
        print(f"[Log] 證交所今日大台指原始列數: {len(tx_data)}")
        
        if not tx_data: return None
            
        result = {'date': today_str}
        for item in tx_data:
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
        
        print(f"[Log] 今日即時數據解析結果: {result}")
        if 'foreign' in result and 'sitc' in result and 'dealers' in result:
            return result
        return None
    except Exception as e:
        print(f"[Log] 今日即時數據抓取發生異常: {e}")
        return None

def get_history_data():
    """第二軌：下載期交所歷史 CSV"""
    url = "https://www.taifex.com.tw/cht/3/futThreeBigProductInstiDown"
    end_date = datetime.now()
    start_date = end_date - timedelta(days=60)
    payload = {
        'down_type': '1',
        'queryStartDate': start_date.strftime("%Y/%m/%d"),
        'queryEndDate': end_date.strftime("%Y/%m/%d"),
        'commodityId': 'TX'
    }
    try:
        response = requests.post(url, data=payload, timeout=20)
        print(f"[Log] 期交所歷史 CSV 連線狀態碼: {response.status_code}")
        if response.status_code != 200: return []
        
        df_headers = pd.read_csv(io.StringIO(response.text), nrows=0)
        headers = [c.strip() for c in df_headers.columns]
        print(f"[Log] 期交所 CSV 偵測到的欄位標頭: {headers}")
        
        # 尋找關鍵欄位位置
        long_idx = headers.index('未平倉多方口數')
        short_idx = headers.index('未平倉空方口數')
        net_idx = headers.index('未平倉多空淨額')
        date_idx = headers.index('日期')
        prod_idx = headers.index('商品名稱')
        name_idx = headers.index('身份別')

        df = pd.read_csv(io.StringIO(response.text), header=None, skiprows=1)
        print(f"[Log] 歷史 CSV 總讀取列數: {len(df)}")
        
        results = {}
        for _, row in df.iterrows():
            try:
                commodity = str(row[prod_idx]).strip()
                if '臺股期貨' not in commodity and 'TX' not in commodity: continue
                date_str = str(row[date_idx]).strip().replace('-', '/')
                name = str(row[name_idx]).strip()
                
                long_val = int(row[long_idx])
                short_val = int(row[short_idx])
                net_val = int(row[net_idx])
                
                if date_str not in results:
                    results[date_str] = {'date': date_str}
                if '外資' in name or '陸資' in name:
                    results[date_str]['foreign'] = {'long': long_val, 'short': short_val, 'net': net_val}
                elif '投信' in name:
                    results[date_str]['sitc'] = {'long': long_val, 'short': short_val, 'net': net_val}
                elif '自營商' in name:
                    results[date_str]['dealers'] = {'long': long_val, 'short': short_val, 'net': net_val}
            except:
                continue
        
        final_list = [v for k, v in results.items() if 'foreign' in v and 'sitc' in v and 'dealers' in v]
        final_list.sort(key=lambda x: x['date'])
        print(f"[Log] 歷史數據成功解析總天數: {len(final_list)}")
        if final_list:
            print(f"[Log] 歷史數據第一筆: {final_list[0]['date']}, 最後一筆: {final_list[-1]['date']}")
        return final_list
    except Exception as e:
        print(f"[Log] 歷史數據抓取發生異常: {e}")
        return []

def update_web():
    data_list = get_history_data()
    today_data = get_today_live_data()
    
    if today_data:
        if not any(d['date'] == today_data['date'] for d in data_list):
            print(f"[Log] 歷史資料未包含今日，手動將今日資料黏上: {today_data['date']}")
            data_list.append(today_data)
        else:
            print(f"[Log] 歷史資料已包含今日，進行覆蓋校正: {today_data['date']}")
            for idx, d in enumerate(data_list):
                if d['date'] == today_data['date']:
                    data_list[idx] = today_data
                    break
                    
    print(f"[Log] 準備寫入網頁的最終總天數: {len(data_list)}")
    data_list = data_list[-30:]
        
    with open("index.html", "r", encoding="utf-8") as f:
        html_content = f.read()
        
    start_marker = "// START_DATA"
    end_marker = "// END_DATA"
    
    start_pos = html_content.find(start_marker)
    end_pos = html_content.find(end_marker)
    
    if start_pos == -1 or end_pos == -1:
        print(f"[Log] 嚴重錯誤：在 index.html 裡找不到暗號地標！位置分別為: {start_pos}, {end_pos}")
        return
        
    data_string = json.dumps(data_list, ensure_ascii=False)
    injection = f"{start_marker}\n        const rawData = {data_string};\n        "
    
    new_html = html_content[:start_pos] + injection + html_content[end_pos:]
    
    with open("index.html", "w", encoding="utf-8") as f:
        f.write(new_html)
    print(f"[Log] 檔案寫入動作執行完畢！")

if __name__ == "__main__":
    update_web()
