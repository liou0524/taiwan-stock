```python
import requests
import json
import os
from datetime import datetime

# =========================
# 取得今日法人資料
# =========================
def get_today_live_data():

    url = "https://openapi.twse.com.tw/v1/taiwanFuturesBigTraders/callsAndPutsDate"

    today_str = datetime.now().strftime("%Y/%m/%d")

    try:
        response = requests.get(url, timeout=15)

        if response.status_code != 200:
            return None

        data_json = response.json()

        tx_data = [
            item for item in data_json
            if "臺股期貨" in item.get("CommodityId", "")
            or item.get("CommodityId") == "TX"
        ]

        if not tx_data:
            return None

        result = {
            "date": today_str,
            "foreign": {
                "long": 0,
                "short": 0,
                "net": 0
            },
            "sitc": {
                "long": 0,
                "short": 0,
                "net": 0
            },
            "dealers": {
                "long": 0,
                "short": 0,
                "net": 0
            }
        }

        for item in tx_data:

            name = item.get("IdentityName", "")

            long_val = int(item.get("OpenInterestLong", 0))
            short_val = int(item.get("OpenInterestShort", 0))
            net_val = int(item.get("OpenInterestNet", 0))

            # 外資
            if "外資" in name or "陸資" in name:
                result["foreign"] = {
                    "long": long_val,
                    "short": short_val,
                    "net": net_val
                }

            # 投信
            elif "投信" in name:
                result["sitc"] = {
                    "long": long_val,
                    "short": short_val,
                    "net": net_val
                }

            # 自營商
            elif "自營商" in name:
                result["dealers"] = {
                    "long": long_val,
                    "short": short_val,
                    "net": net_val
                }

        return result

    except Exception as e:
        print("取得資料失敗:", e)
        return None


# =========================
# 讀取歷史資料
# =========================
def load_history():

    file_name = "history.json"

    if not os.path.exists(file_name):
        return []

    try:
        with open(file_name, "r", encoding="utf-8") as f:
            return json.load(f)

    except:
        return []


# =========================
# 儲存歷史資料
# =========================
def save_history(today_data):

    history = load_history()

    # 避免同一天重複
    history = [
        item for item in history
        if item["date"] != today_data["date"]
    ]

    history.append(today_data)

    # 只保留最近10天
    history = history[-10:]

    with open("history.json", "w", encoding="utf-8") as f:
        json.dump(history, f, ensure_ascii=False, indent=2)

    return history


# =========================
# 生成 HTML
# =========================
def generate_html(data_list):

    data_json = json.dumps(data_list, ensure_ascii=False)

    html = f"""
<!DOCTYPE html>
<html lang="zh-TW">

<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">

<title>TRI 法人期貨觀測站</title>

<script src="https://cdn.tailwindcss.com"></script>
<script src="https://cdn.jsdelivr.net/npm/chart.js"></script>

<style>

body {{
    background: #0b0f19;
    color: white;
    font-family: monospace;
}}

.card {{
    background: #111827;
    border: 1px solid #1e293b;
    border-radius: 20px;
    padding: 20px;
    margin-top: 20px;
}}

</style>

</head>

<body>

<div class="max-w-5xl mx-auto p-4">

    <div class="card">

        <h1 class="text-2xl font-bold text-cyan-400 mb-2">
            TRI 法人期貨留倉觀測站
        </h1>

        <p id="update-date" class="text-slate-400 mb-6">
            載入中...
        </p>

        <div class="overflow-x-auto">

            <table class="w-full text-left">

                <thead>
                    <tr class="border-b border-slate-700">
                        <th class="p-3">法人</th>
                        <th class="p-3 text-right">多單</th>
                        <th class="p-3 text-right">空單</th>
                        <th class="p-3 text-right">淨額</th>
                    </tr>
                </thead>

                <tbody>

                    <tr>
                        <td class="p-3 text-amber-400">外資</td>
                        <td id="foreign-long" class="p-3 text-right"></td>
                        <td id="foreign-short" class="p-3 text-right"></td>
                        <td id="foreign-net" class="p-3 text-right font-bold"></td>
                    </tr>

                    <tr>
                        <td class="p-3 text-blue-400">投信</td>
                        <td id="sitc-long" class="p-3 text-right"></td>
                        <td id="sitc-short" class="p-3 text-right"></td>
                        <td id="sitc-net" class="p-3 text-right font-bold"></td>
                    </tr>

                    <tr>
                        <td class="p-3 text-emerald-400">自營商</td>
                        <td id="dealers-long" class="p-3 text-right"></td>
                        <td id="dealers-short" class="p-3 text-right"></td>
                        <td id="dealers-net" class="p-3 text-right font-bold"></td>
                    </tr>

                </tbody>

            </table>

        </div>

    </div>

    <div class="card">

        <h2 class="text-lg mb-4">
            三大法人近10日淨部位趨勢
        </h2>

        <div style="height:400px;">
            <canvas id="trendChart"></canvas>
        </div>

    </div>

</div>

<script>

const rawData = {data_json};

if(rawData.length > 0) {{

    const latest = rawData[rawData.length - 1];

    document.getElementById("update-date").innerText =
        "最後更新：" + latest.date;

    function fillRow(prefix, data) {{

        document.getElementById(prefix + "-long").innerText =
            data.long.toLocaleString();

        document.getElementById(prefix + "-short").innerText =
            data.short.toLocaleString();

        const netEl = document.getElementById(prefix + "-net");

        netEl.innerText =
            (data.net > 0 ? "+" : "") +
            data.net.toLocaleString();

        if(data.net >= 0) {{
            netEl.style.color = "#f43f5e";
        }} else {{
            netEl.style.color = "#10b981";
        }}
    }}

    fillRow("foreign", latest.foreign);
    fillRow("sitc", latest.sitc);
    fillRow("dealers", latest.dealers);

    const ctx =
        document.getElementById("trendChart")
        .getContext("2d");

    new Chart(ctx, {{

        type: "line",

        data: {{

            labels: rawData.map(d => d.date.substring(5)),

            datasets: [

                {{
                    label: "外資",
                    data: rawData.map(d => d.foreign.net),
                    borderColor: "#f59e0b",
                    borderWidth: 3,
                    tension: 0.2
                }},

                {{
                    label: "投信",
                    data: rawData.map(d => d.sitc.net),
                    borderColor: "#3b82f6",
                    borderWidth: 2,
                    tension: 0.2
                }},

                {{
                    label: "自營商",
                    data: rawData.map(d => d.dealers.net),
                    borderColor: "#10b981",
                    borderWidth: 2,
                    tension: 0.2
                }}

            ]
        }},

        options: {{
            responsive: true,
            maintainAspectRatio: false
        }}

    }});

}}

</script>

</body>
</html>
"""

    with open("index.html", "w", encoding="utf-8") as f:
        f.write(html)


# =========================
# 主程式
# =========================
def main():

    today_data = get_today_live_data()

    if not today_data:
        print("今日資料抓取失敗")
        return

    history = save_history(today_data)

    generate_html(history)

    print("網站更新完成")


if __name__ == "__main__":
    main()
```
