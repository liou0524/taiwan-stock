import requests
import io
import pandas as pd
import json
import os
from datetime import datetime, timedelta

def get_today_live_data():
    """第一軌：抓取今日最新即時數據"""
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
    """第二軌：下載期交所官方歷史 CSV"""
    url = "https://www.taifex.com.tw/cht/3/futThreeBigProductInstiDown"
    end_date = datetime.now()
    start_date = end_date - timedelta(days=40) # 抓40天確保扣除假日有超過10個交易日
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

def generate_html_template(data_list_json):
    """將網頁骨架硬編碼在 Python 中，徹底避免讀取與取代出錯的問題"""
    return f"""<!DOCTYPE html>
<html lang="zh-TW">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>🎛️ TRI-法人期貨留倉高級觀測站</title>
    <script src="https://cdn.tailwindcss.com"></script>
    <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
    <style>
        .neon-border {{
            box-shadow: 0 0 15px rgba(6, 182, 212, 0.15), inset 0 0 15px rgba(6, 182, 212, 0.05);
            border: 1px solid rgba(6, 182, 212, 0.3);
        }}
        .neon-text-orange {{ text-shadow: 0 0 8px rgba(245, 158, 11, 0.6); }}
        .neon-text-cyan {{ text-shadow: 0 0 8px rgba(6, 182, 212, 0.6); }}
    </style>
</head>
<body class="bg-[#0b0f19] text-slate-200 min-h-screen p-4 md:p-8 flex flex-col items-center justify-start font-mono">

    <div class="w-full max-w-5xl bg-[#111827]/80 backdrop-blur-md rounded-2xl p-6 my-2 neon-border">
        
        <div class="flex justify-between items-center border-b border-cyan-500/30 pb-4 mb-6">
            <div>
                <h1 class="text-xl md:text-2xl font-black tracking-widest text-cyan-400 neon-text-cyan">
                    SYSTEM://TRI_法人期貨留倉觀測站
                </h1>
                <p class="text-[10px] text-slate-500 mt-1 uppercase tracking-wider">
                    SYS_STATUS: ACTIVE // REFRESH_TIME: <span id="update-date" class="text-slate-400">LOADING...</span>
                </p>
            </div>
            <div class="flex space-x-2 text-[10px]">
                <span class="px-2 py-1 bg-cyan-500/10 text-cyan-400 border border-cyan-500/20 rounded">📊 近10日數據變化</span>
            </div>
        </div>

        <div class="overflow-x-auto mb-8 rounded-xl border border-slate-800 bg-[#0d1321]">
            <table class="w-full text-left border-collapse">
                <thead>
                    <tr class="border-b border-slate-800 text-slate-400 text-xs tracking-wider uppercase bg-slate-900/50">
                        <th class="p-4">法人項目 [ENTITY]</th>
                        <th class="p-4 text-right">多方未平倉 (口)</th>
                        <th class="p-4 text-right">空方未平倉 (口)</th>
                        <th class="p-4 text-right">淨部位 (口) [NET]</th>
                    </tr>
                </thead>
                <tbody class="text-sm divide-y divide-slate-800/60">
                    <tr>
                        <td class="p-4 font-bold text-amber-400 neon-text-orange tracking-wide">■ 外資及陸資</td>
                        <td id="foreign-long" class="p-4 text-right font-semibold">--</td>
                        <td id="foreign-short" class="p-4 text-right font-semibold">--</td>
                        <td id="foreign-net" class="p-4 text-right font-black text-base">--</td>
                    </tr>
                    <tr>
                        <td class="p-4 font-bold text-blue-400 tracking-wide">■ 投信</td>
                        <td id="sitc-long" class="p-4 text-right font-semibold">--</td>
                        <td id="sitc-short" class="p-4 text-right font-semibold">--</td>
                        <td id="sitc-net" class="p-4 text-right font-black text-base">--</td>
                    </tr>
                    <tr>
                        <td class="p-4 font-bold text-emerald-400 tracking-wide">■ 自營商</td>
                        <td id="dealers-long" class="p-4 text-right font-semibold">--</td>
                        <td id="dealers-short" class="p-4 text-right font-semibold">--</td>
                        <td id="dealers-net" class="p-4 text-right font-black text-base">--</td>
                    </tr>
                </tbody>
            </table>
        </div>

        <div class="bg-[#0d1321] border border-slate-800 p-4 rounded-xl">
            <h3 class="text-xs font-bold text-slate-400 uppercase tracking-widest mb-4">
                📈 三大法人淨部位近10日歷史趨勢線
            </h3>
            <div class="h-72 md:h-80 w-full">
                <canvas id="trendsChart"></canvas>
            </div>
        </div>
    </div>

    <script>
        const rawData = {data_list_json};

        if (rawData.length > 0) {{
            const latest = rawData[rawData.length - 1];
            document.getElementById('update-date').innerText = latest.date + " (數據就緒)";
            
            const fillRow = (prefix, data) => {{
                document.getElementById(prefix + '-long').innerText = data.long.toLocaleString();
                document.getElementById(prefix + '-short').innerText = data.short.toLocaleString();
                const net = data.net;
                const netEl = document.getElementById(prefix + '-net');
                netEl.innerText = (net > 0 ? "+" : "") + net.toLocaleString();
                netEl.className = net >= 0 ? "p-4 text-right font-black text-base text-rose-500" : "p-4 text-right font-black text-base text-emerald-400";
            }};
            
            fillRow('foreign', latest.foreign);
            fillRow('sitc', latest.sitc);
            fillRow('dealers', latest.dealers);

            const dates = rawData.map(d => d.date.substring(5));
            const foreignNets = rawData.map(d => d.foreign.net);
            const sitcNets = rawData.map(d => d.sitc.net);
            const dealersNets = rawData.map(d => d.dealers.net);

            const ctx = document.getElementById('trendsChart').getContext('2d');
            new Chart(ctx, {{
                type: 'line',
                data: {{
                    labels: dates,
                    datasets: [
                        {{ label: '外資淨額', data: foreignNets, borderColor: '#f59e0b', backgroundColor: 'rgba(245,158,11,0.03)', borderWidth: 3, pointRadius: 3, tension: 0.15, fill: true }},
                        {{ label: '投信淨額', data: sitcNets, borderColor: '#3b82f6', borderWidth: 2, pointRadius: 3, tension: 0.15 }},
                        {{ label: '自營商淨額', data: dealersNets, borderColor: '#10b981', borderWidth: 2, pointRadius: 3, tension: 0.15 }}
                    ]
                }},
                options: {{
                    responsive: true,
                    maintainAspectRatio: false,
                    plugins: {{ legend: {{ labels: {{ color: '#94a3b8', font: {{ family: 'monospace', size: 11 }} }} }} }},
                    scales: {{
                        x: {{ grid: {{ color: 'rgba(51, 65, 85, 0.2)' }}, ticks: {{ color: '#64748b', font: {{ family: 'monospace', size: 10 }} }} }},
                        y: {{ grid: {{ color: 'rgba(51, 65, 85, 0.2)' }}, ticks: {{ color: '#64748b', font: {{ family: 'monospace' }} }} }}
                    }}
                }}
            }});
        }}
    </script>
</body>
</html>
"""

def update_web():
    # 1. 先抓官方歷史資料庫
    data_list = get_history_data()
    
    # 2. 嘗試抓今天最新的盤後數據
    today_data = get_today_live_data()
    
    # 3. 智慧融合與補償防空轉機制
    if today_data:
        # 如果歷史資料裡還沒有今天，就把今天黏在最右端
        if not any(d['date'] == today_data['date'] for d in data_list):
            data_list.append(today_data)
        else:
            # 歷史資料已經有今天，用最新即時數據覆蓋
            for idx, d in enumerate(data_list):
                if d['date'] == today_data['date']:
                    data_list[idx] = today_data
                    break
    else:
        print("[💡 提示] 今日最新數據尚未公佈（或證交所尚未更新）。系統自動沿用歷史資料最新一天作為展示數據！")
    
    # 如果遇到極端假日或完全抓不到資料，防錯熔斷
    if len(data_list) == 0:
        print("[❌ 錯誤] 全線抓取失敗，終止寫入以保護原網頁。")
        return
        
    # 🎯 重點需求：截取近 10 日的數據變化畫成圖就好
    data_list = data_list[-10:]
    
    # 將數據轉換成 JSON
    data_list_json = json.dumps(data_list, ensure_ascii=False)
    
    # 🛠️ 無暗號全寫入：直接生成一整份乾淨完美的 index.html 覆蓋過去！
    final_html_content = generate_html_template(data_list_json)
    
    with open("index.html", "w", encoding="utf-8") as f:
        f.write(final_html_content)
        
    print(f"[🎉 成功] 網頁數據生成完畢！當前最新數據日期為：{data_list[-1]['date']}")

if __name__ == "__main__":
    update_web()
