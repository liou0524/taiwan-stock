import requests
import io
import pandas as pd
import json
from datetime import datetime, timedelta

def get_today_live_data():
    """第一軌：抓取今日最新即時籌碼（防擋、即時）"""
    url = "https://openapi.twse.com.tw/v1/taiwanFuturesBigTraders/callsAndPutsDate"
    today_str = datetime.now().strftime("%Y/%m/%d")
    try:
        response = requests.get(url, timeout=15)
        if response.status_code != 200: return None
        data_json = response.json()
        tx_data = [item for item in data_json if "臺股期貨" in item.get('CommodityId', '') or item.get('CommodityId') == 'TX']
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
        
        if 'foreign' in result and 'sitc' in result and 'dealers' in result:
            return result
        return None
    except:
        return None

def get_history_data():
    """第二軌：動態解析官方歷史 CSV 檔（穩健、無誤差）"""
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
        if response.status_code != 200: return []
        
        df_headers = pd.read_csv(io.StringIO(response.text), nrows=0)
        headers = [c.strip() for c in df_headers.columns]
        
        long_idx = headers.index('未平倉多方口數')
        short_idx = headers.index('未平倉空方口數')
        net_idx = headers.index('未平倉多空淨額')
        date_idx = headers.index('日期')
        prod_idx = headers.index('商品名稱')
        name_idx = headers.index('身份別')

        df = pd.read_csv(io.StringIO(response.text), header=None, skiprows=1)
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
        return final_list
    except:
        return []

def update_web():
    # 1. 先抓歷史基底
    data_list = get_history_data()
    
    # 2. 抓今天最新的即時數據
    today_data = get_today_live_data()
    
    # 3. 雙軌大融合機制
    if today_data:
        # 如果歷史資料裡還沒有今天，就把今天強力黏在最後面
        if not any(d['date'] == today_data['date'] for d in data_list):
            data_list.append(today_data)
        else:
            # 如果歷史資料已經有今天了，用最新即時數據覆蓋，確保萬無一失
            for idx, d in enumerate(data_list):
                if d['date'] == today_data['date']:
                    data_list[idx] = today_data
                    break
    
    # 防錯安全熔斷
    if len(data_list) < 10:
        print("【安全機制】最終合併資料量嚴重不足，取消寫入防止損壞網頁！")
        return
        
    # 永遠保留最完美的最新 30 筆交易日紀錄
    data_list = data_list[-30:]
        
    with open("index.html", "r", encoding="utf-8") as f:
        html_content = f.read()
        
    start_tag = 'const rawData = '
    end_tag = '; // 供未來機器人每天疊加最新數據使用'
    start_idx = html_content.find(start_tag) + len(start_tag)
    end_idx = html_content.find(end_tag)
    
    if start_idx == -1 or end_idx == -1: return
        
    new_data_str = json.dumps(data_list, ensure_ascii=False)
    new_html = html_content[:start_idx] + new_data_str + html_content[end_idx:]
    
    with open("index.html", "w", encoding="utf-8") as f:
        f.write(new_html)
    print(f"【全面成功】雙軌籌碼校正寫入完畢！目前最新交易日為：{data_list[-1]['date']}")

if __name__ == "__main__":
    update_web()
