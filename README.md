<!DOCTYPE html>
<html lang="zh-TW">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>外資期貨留倉觀測戰</title>
    <!-- 引入美化網頁與圖表的工具 -->
    <script src="https://cdn.tailwindcss.com"></script>
    <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
</head>
<body class="bg-slate-900 text-slate-100 min-h-screen flex items-center justify-center p-4">

    <div class="w-full max-w-3xl bg-slate-800 rounded-2xl shadow-2xl border border-slate-700 p-6 md:p-8">
        <!-- 標題 -->
        <div class="flex justify-between items-center mb-6 border-b border-slate-700 pb-4">
            <div>
                <h1 class="text-2xl font-bold bg-gradient-to-r from-red-400 to-amber-400 bg-clip-text text-transparent">
                    📊 外資台指期貨留倉看板
                </h1>
                <p class="text-xs text-slate-400 mt-1">資料更新：2026/05/28 (今日最新)</p>
            </div>
            <span class="px-3 py-1 bg-red-500/10 text-red-400 text-xs font-semibold rounded-full border border-red-500/20 animate-pulse">
                空單高水位警示
            </span>
        </div>

        <!-- 數據卡片 -->
        <div class="grid grid-cols-1 md:grid-cols-3 gap-4 mb-8">
            <div class="bg-slate-800/50 border border-slate-700 p-4 rounded-xl">
                <p class="text-sm text-slate-400">多方未平倉</p>
                <p class="text-xl font-bold text-emerald-400 mt-1">16,585 <span class="text-xs text-slate-500">口</span></p>
            </div>
            <div class="bg-slate-800/50 border border-red-500/30 p-4 rounded-xl relative overflow-hidden">
                <p class="text-sm text-red-400 font-medium">空方未平倉 (聚焦)</p>
                <p class="text-2xl font-black text-red-500 mt-1">74,781 <span class="text-xs text-slate-500">口</span></p>
                <div class="absolute right-0 bottom-0 text-red-500/5 text-6xl font-bold select-none pointer-events-none transform translate-x-2 translate-y-2">SHORT</div>
            </div>
            <div class="bg-slate-800/50 border border-slate-700 p-4 rounded-xl">
                <p class="text-sm text-slate-400">多空淨額 (Net)</p>
                <p class="text-xl font-bold text-amber-500 mt-1">-58,196 <span class="text-xs text-slate-500">口</span></p>
                <p class="text-xs text-emerald-400 mt-1">▲ 今日回補 1,554 口</p>
            </div>
        </div>

        <!-- 圖表區 -->
        <div class="bg-slate-800/30 border border-slate-700 p-4 rounded-xl">
            <h3 class="text-sm font-semibold text-slate-300 mb-4">📈 近 5 日外資留倉趨勢變化</h3>
            <div class="h-64 w-full">
                <canvas id="futuresChart"></canvas>
            </div>
        </div>
    </div>

    <script>
        // 近 5 日數據 (05/22 ~ 05/28)
        const ctx = document.getElementById('futuresChart').getContext('2d');
        new Chart(ctx, {
            type: 'line',
            data: {
                labels: ['05/22', '05/23', '05/26', '05/27', '05/28'],
                datasets: [
                    {
                        label: '空方留倉 (口)',
                        data: [68000, 71000, 73500, 75650, 74781],
                        borderColor: '#f43f5e',
                        backgroundColor: 'rgba(244, 63, 94, 0.1)',
                        borderWidth: 3,
                        tension: 0.3,
                        fill: true
                    },
                    {
                        label: '淨部位 (口)',
                        data: [-52800, -56200, -57400, -59750, -58196],
                        borderColor: '#f59e0b',
                        borderWidth: 2,
                        borderDash: [5, 5],
                        tension: 0.3,
                        fill: false
                    }
                ]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: { labels: { color: '#94a3b8' } }
                },
                scales: {
                    x: { grid: { color: '#334155' }, ticks: { color: '#94a3b8' } },
                    y: { grid: { color: '#334155' }, ticks: { color: '#94a3b8' } }
                }
            }
        });
    </script>
</body>
</html>
