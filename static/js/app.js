// Global Chart Instances
let equityChartInstance = null;
let outcomeChartInstance = null;
let dailyPnlChartInstance = null;
let setupChartInstance = null;

// App Initialization
document.addEventListener('DOMContentLoaded', () => {
    // Set default date to today
    const today = new Date().toISOString().split('T')[0];
    document.getElementById('tradeDate').value = today;
    
    // Checkbox listener for rule count
    document.querySelectorAll('input[name="ruleCheck"]').forEach(cb => {
        cb.addEventListener('change', updateRuleScoreDisplay);
    });

    // Auto-calculate RR in modal when SL, TP, Entry change
    ['tradeEntry', 'tradeSL', 'tradeTP'].forEach(id => {
        document.getElementById(id).addEventListener('input', autoCalculateRR);
    });

    // Fetch initial data
    fetchSettings();
    fetchStats();
    loadTrades();
});

// Update the checkbox counter in the modal
function updateRuleScoreDisplay() {
    const checked = document.querySelectorAll('input[name="ruleCheck"]:checked').length;
    const total = 8;
    const el = document.getElementById('formRuleScore');
    el.textContent = `${checked}/${total} Rules Checked (${Math.round((checked/total)*100)}%)`;
    if (checked === total) {
        el.className = 'text-[10px] text-emerald-400 font-mono font-bold';
    } else {
        el.className = 'text-[10px] text-cyan-400 font-mono';
    }
}

// Auto calculate R:R ratio
function autoCalculateRR() {
    const entry = parseFloat(document.getElementById('tradeEntry').value);
    const sl = parseFloat(document.getElementById('tradeSL').value);
    const tp = parseFloat(document.getElementById('tradeTP').value);
    const dir = document.getElementById('tradeDirection').value;

    if (!isNaN(entry) && !isNaN(sl) && !isNaN(tp) && entry > 0 && sl > 0 && tp > 0) {
        let risk = 0;
        let reward = 0;
        if (dir === 'BUY') {
            risk = entry - sl;
            reward = tp - entry;
        } else {
            risk = sl - entry;
            reward = entry - tp;
        }

        if (risk > 0 && reward > 0) {
            const rr = (reward / risk).toFixed(1);
            document.getElementById('tradeRR').value = rr;
        }
    }
}

// ----------------- DATA FETCHING ----------------- //

async function fetchStats() {
    try {
        const res = await fetch('/api/stats');
        const data = await res.json();
        renderKPIs(data);
        renderCharts(data.charts, data.account);
        renderAlertBanner(data.today, data.account);
    } catch (err) {
        console.error('Failed to fetch stats:', err);
    }
}

async function fetchSettings() {
    try {
        const res = await fetch('/api/settings');
        const data = await res.json();
        document.getElementById('settingInitialBalance').value = data.initial_balance || '100.00';
        document.getElementById('settingTargetBalance').value = data.target_balance || '1000.00';
        document.getElementById('settingDailyTarget').value = data.daily_profit_target || '10.00';
        document.getElementById('settingMaxLoss').value = data.daily_max_loss || '5.00';
        document.getElementById('settingTgToken').value = data.telegram_bot_token || '';
        document.getElementById('settingTgChatId').value = data.telegram_chat_id || '';
        document.getElementById('settingTgEnabled').checked = data.telegram_enabled === '1';
    } catch (err) {
        console.error('Failed to fetch settings:', err);
    }
}

async function loadTrades() {
    const outcome = document.getElementById('filterOutcome').value;
    const setup = document.getElementById('filterSetup').value;
    
    let url = '/api/trades?';
    if (outcome) url += `outcome=${encodeURIComponent(outcome)}&`;
    if (setup) url += `setup=${encodeURIComponent(setup)}&`;

    try {
        const res = await fetch(url);
        const trades = await res.json();
        renderTradesTable(trades);
    } catch (err) {
        console.error('Failed to load trades:', err);
    }
}

// ----------------- UI RENDERING ----------------- //

function renderKPIs(data) {
    const acc = data.account;
    const perf = data.performance;
    const today = data.today;

    // Challenge section
    document.getElementById('statStartBalance').textContent = `$${acc.initial_balance.toFixed(2)}`;
    document.getElementById('statTargetBalance').textContent = `$${acc.target_balance.toFixed(2)}`;
    document.getElementById('statRemainingGoal').textContent = `$${acc.remaining_to_goal.toFixed(2)}`;
    
    document.getElementById('challengeProgressText').textContent = `${acc.progress_pct}% Completed`;
    document.getElementById('challengeProgressBar').style.width = `${acc.progress_pct}%`;

    // Cards
    document.getElementById('cardBalance').textContent = `$${acc.current_balance.toFixed(2)}`;
    const plSign = acc.total_pl >= 0 ? '+' : '-';
    const totalPlPercent = ((acc.total_pl / acc.initial_balance) * 100).toFixed(1);
    const plColor = acc.total_pl >= 0 ? 'text-emerald-400' : 'text-rose-400';
    document.getElementById('cardTotalPL').innerHTML = `<span class="${plColor}">${plSign}$${Math.abs(acc.total_pl).toFixed(2)} (${totalPlPercent}%)</span>`;

    // Today's P&L
    const daySign = today.pl >= 0 ? '+' : '-';
    const dayColor = today.pl >= 0 ? 'text-emerald-400' : 'text-rose-400';
    document.getElementById('cardTodayPL').innerHTML = `<span class="${dayColor}">${daySign}$${Math.abs(today.pl).toFixed(2)}</span>`;
    document.getElementById('cardTodayTarget').textContent = `Target: $${acc.daily_profit_target.toFixed(2)} (${today.trades_count}/2 Trades)`;

    // Win Rate & Counts
    document.getElementById('cardWinRate').textContent = `${perf.win_rate}%`;
    document.getElementById('cardTradeCounts').textContent = `${perf.wins}W / ${perf.losses}L / ${perf.breakevens}BE`;
    document.getElementById('totalTradesBadge').textContent = `${perf.total_trades} Total Trades`;

    // Avg RR & Profit Factor
    document.getElementById('cardAvgRR').textContent = `1:${perf.avg_rr.toFixed(1)}`;
    document.getElementById('cardProfitFactor').textContent = `${perf.profit_factor.toFixed(2)}`;
    document.getElementById('cardGrossPL').textContent = `+${perf.gross_profit.toFixed(1)} / -${perf.gross_loss.toFixed(1)}`;

    // Discipline
    document.getElementById('cardDiscipline').textContent = `${perf.avg_compliance}%`;
}

function renderAlertBanner(today, acc) {
    const banner = document.getElementById('statusAlertBanner');
    
    if (today.stop_loss_hit) {
        banner.className = 'rounded-2xl p-4 bg-rose-950/80 border-2 border-rose-500 animate-pulse-stop flex flex-col md:flex-row items-center justify-between gap-4 text-rose-100 shadow-neon-rose';
        banner.innerHTML = `
            <div class="flex items-center gap-3">
                <div class="w-10 h-10 rounded-xl bg-rose-500 text-cyber-950 flex items-center justify-center font-bold text-xl">
                    <i class="fa-solid fa-hand"></i>
                </div>
                <div>
                    <div class="text-sm font-extrabold tracking-wide uppercase flex items-center gap-2">
                        <span>RULE 8 STOP TRADING LOCKOUT TRIGGERED</span>
                        <span class="px-2 py-0.5 rounded bg-rose-500/30 text-rose-300 text-xs">-$${Math.abs(today.pl).toFixed(2)} / -$${acc.daily_max_loss.toFixed(2)} Limit</span>
                    </div>
                    <p class="text-xs text-rose-200/80 mt-0.5">You have reached the maximum $5 daily risk. Close your charts, protect your capital, and come back fresh tomorrow!</p>
                </div>
            </div>
            <div class="px-3.5 py-1.5 rounded-xl bg-rose-900/60 border border-rose-500/50 text-xs font-mono font-bold text-rose-300 whitespace-nowrap">
                🛑 TRADING HALTED
            </div>
        `;
        banner.classList.remove('hidden');
    } else if (today.target_achieved) {
        banner.className = 'rounded-2xl p-4 bg-emerald-950/60 border border-emerald-500/80 flex flex-col md:flex-row items-center justify-between gap-4 text-emerald-100 shadow-neon-emerald';
        banner.innerHTML = `
            <div class="flex items-center gap-3">
                <div class="w-10 h-10 rounded-xl bg-emerald-500 text-cyber-950 flex items-center justify-center font-bold text-xl">
                    <i class="fa-solid fa-trophy"></i>
                </div>
                <div>
                    <div class="text-sm font-extrabold tracking-wide uppercase flex items-center gap-2">
                        <span>DAILY PROFIT TARGET ACHIEVED (+$${today.pl.toFixed(2)})</span>
                        <span class="px-2 py-0.5 rounded bg-emerald-500/30 text-emerald-300 text-xs">Goal: $${acc.daily_profit_target.toFixed(2)}</span>
                    </div>
                    <p class="text-xs text-emerald-200/80 mt-0.5">Great discipline! Lock in your gains and avoid overtrading.</p>
                </div>
            </div>
            <div class="px-3.5 py-1.5 rounded-xl bg-emerald-900/60 border border-emerald-500/50 text-xs font-mono font-bold text-emerald-300 whitespace-nowrap">
                🎯 TARGET HIT
            </div>
        `;
        banner.classList.remove('hidden');
    } else if (today.max_trades_warning) {
        banner.className = 'rounded-2xl p-4 bg-amber-950/60 border border-amber-500/80 flex flex-col md:flex-row items-center justify-between gap-4 text-amber-100 shadow-glow-card';
        banner.innerHTML = `
            <div class="flex items-center gap-3">
                <div class="w-10 h-10 rounded-xl bg-amber-500 text-cyber-950 flex items-center justify-center font-bold text-xl">
                    <i class="fa-solid fa-triangle-exclamation"></i>
                </div>
                <div>
                    <div class="text-sm font-extrabold tracking-wide uppercase flex items-center gap-2">
                        <span>RULE 3 NOTICE: ${today.trades_count} SETUPS TAKEN TODAY</span>
                    </div>
                    <p class="text-xs text-amber-200/80 mt-0.5">Maximum recommended daily setups is 1 to 2. Maintain strict discipline against overtrading.</p>
                </div>
            </div>
            <div class="px-3.5 py-1.5 rounded-xl bg-amber-900/60 border border-amber-500/50 text-xs font-mono font-bold text-amber-300 whitespace-nowrap">
                ⚠️ DAILY LIMIT MET
            </div>
        `;
        banner.classList.remove('hidden');
    } else {
        banner.classList.add('hidden');
    }
}

function renderTradesTable(trades) {
    const tbody = document.getElementById('tradesTableBody');
    if (!trades || trades.length === 0) {
        tbody.innerHTML = `
            <tr>
                <td colspan="10" class="text-center py-8 text-slate-500 font-mono text-xs">
                    <i class="fa-solid fa-chart-simple text-2xl mb-2 block opacity-40"></i>
                    No trades logged yet. Click <span class="text-cyan-400 font-bold cursor-pointer" onclick="openTradeModal()">+ Log Trade</span> or load demo data to start!
                </td>
            </tr>
        `;
        return;
    }

    let html = '';
    trades.forEach(t => {
        const isWin = t.profit_loss > 0;
        const isLoss = t.profit_loss < 0;
        const plClass = isWin ? 'text-emerald-400 font-bold' : (isLoss ? 'text-rose-400 font-bold' : 'text-slate-400 font-bold');
        const plSign = isWin ? '+' : (isLoss ? '-' : '');
        const plFormatted = `${plSign}$${Math.abs(t.profit_loss).toFixed(2)}`;

        const dirBadge = t.direction === 'BUY'
            ? `<span class="px-2 py-0.5 rounded bg-emerald-500/20 text-emerald-400 border border-emerald-500/40 text-[10px] font-bold">BUY</span>`
            : `<span class="px-2 py-0.5 rounded bg-rose-500/20 text-rose-400 border border-rose-500/40 text-[10px] font-bold">SELL</span>`;

        const complianceBadge = t.compliance_rate >= 100
            ? `<span class="px-2 py-0.5 rounded bg-emerald-500/20 text-emerald-400 border border-emerald-500/30 text-[10px]">100% 🎯</span>`
            : `<span class="px-2 py-0.5 rounded bg-amber-500/20 text-amber-400 border border-amber-500/30 text-[10px]">${t.compliance_rate}% ⚠️</span>`;

        html += `
            <tr class="hover:bg-cyber-900/50 transition-colors border-b border-slate-800/40">
                <td class="py-3 px-3 text-slate-300">${t.trade_date}</td>
                <td class="py-3 px-3 font-bold text-slate-100 flex items-center gap-1.5">
                    <span>${t.pair}</span>
                    ${t.notes ? `<span title="${escapeHtml(t.notes)}" class="cursor-pointer text-slate-500 hover:text-cyan-400"><i class="fa-regular fa-comment-dots text-xs"></i></span>` : ''}
                </td>
                <td class="py-3 px-3">${dirBadge}</td>
                <td class="py-3 px-3 text-slate-300 text-[11px] max-w-[180px] truncate" title="${t.setup_type}">${t.setup_type}</td>
                <td class="py-3 px-3 text-slate-400">${t.entry_price || '--'} ➔ ${t.exit_price || '--'}</td>
                <td class="py-3 px-3 text-slate-400">${t.stop_loss || '--'} / ${t.take_profit || '--'}</td>
                <td class="py-3 px-3 text-cyan-400">1:${t.rr_ratio}</td>
                <td class="py-3 px-3 ${plClass}">${plFormatted}</td>
                <td class="py-3 px-3">${complianceBadge}</td>
                <td class="py-3 px-3 text-right space-x-1 whitespace-nowrap">
                    <button onclick="editTrade(${t.id})" class="p-1.5 rounded hover:bg-slate-800 text-slate-400 hover:text-cyan-400" title="Edit">
                        <i class="fa-solid fa-pen-to-square text-xs"></i>
                    </button>
                    <button onclick="deleteTrade(${t.id})" class="p-1.5 rounded hover:bg-rose-950 text-slate-400 hover:text-rose-400" title="Delete">
                        <i class="fa-solid fa-trash-can text-xs"></i>
                    </button>
                </td>
            </tr>
        `;
    });

    tbody.innerHTML = html;
}

// Helper to escape HTML in notes
function escapeHtml(str) {
    if (!str) return '';
    return str.replace(/&/g, '&amp;').replace(/"/g, '&quot;').replace(/'/g, '&#39;').replace(/</g, '&lt;').replace(/>/g, '&gt;');
}

// ----------------- CHARTS INITIALIZATION ----------------- //

function renderCharts(charts, account) {
    // 1. Main Equity Growth Curve Chart
    const eqCtx = document.getElementById('equityChart').getContext('2d');
    const eqData = charts.equity_curve || [];
    const eqLabels = eqData.map(d => d.date);
    const eqBalances = eqData.map(d => d.balance);

    if (equityChartInstance) equityChartInstance.destroy();

    const cyanGradient = eqCtx.createLinearGradient(0, 0, 0, 240);
    cyanGradient.addColorStop(0, 'rgba(0, 242, 254, 0.35)');
    cyanGradient.addColorStop(1, 'rgba(0, 242, 254, 0.0)');

    equityChartInstance = new Chart(eqCtx, {
        type: 'line',
        data: {
            labels: eqLabels,
            datasets: [
                {
                    label: 'Account Equity ($)',
                    data: eqBalances,
                    borderColor: '#00f2fe',
                    backgroundColor: cyanGradient,
                    fill: true,
                    tension: 0.35,
                    borderWidth: 3,
                    pointRadius: 4,
                    pointBackgroundColor: '#00f2fe',
                    pointHoverRadius: 6,
                    pointHoverBackgroundColor: '#ffffff'
                },
                {
                    label: '$1,000 Target Milestone',
                    data: Array(eqLabels.length).fill(account.target_balance),
                    borderColor: 'rgba(255, 215, 0, 0.6)',
                    borderDash: [6, 6],
                    borderWidth: 1.5,
                    pointRadius: 0,
                    fill: false
                }
            ]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: {
                    labels: { color: '#94a3b8', font: { family: 'JetBrains Mono', size: 11 } }
                },
                tooltip: {
                    backgroundColor: '#0b0f19',
                    borderColor: '#1e293b',
                    borderWidth: 1,
                    titleFont: { family: 'JetBrains Mono' },
                    bodyFont: { family: 'JetBrains Mono' },
                    callbacks: {
                        label: function(context) {
                            return ` ${context.dataset.label}: $${context.parsed.y.toFixed(2)}`;
                        }
                    }
                }
            },
            scales: {
                x: {
                    grid: { color: 'rgba(255, 255, 255, 0.05)' },
                    ticks: { color: '#64748b', font: { family: 'JetBrains Mono', size: 10 } }
                },
                y: {
                    grid: { color: 'rgba(255, 255, 255, 0.05)' },
                    ticks: {
                        color: '#64748b',
                        font: { family: 'JetBrains Mono', size: 10 },
                        callback: val => `$${val}`
                    }
                }
            }
        }
    });

    // 2. Win / Loss Doughnut Chart
    const outCtx = document.getElementById('outcomeChart').getContext('2d');
    if (outcomeChartInstance) outcomeChartInstance.destroy();

    const disc = charts.discipline;
    const wins = (disc.full_compliant.wins || 0) + (disc.broken_rules.wins || 0);
    const total = (disc.full_compliant.total || 0) + (disc.broken_rules.total || 0);
    const losses = total - wins;

    outcomeChartInstance = new Chart(outCtx, {
        type: 'doughnut',
        data: {
            labels: ['Wins', 'Losses'],
            datasets: [{
                data: [wins, losses],
                backgroundColor: ['#00f59b', '#ff3366'],
                borderColor: '#0b0f19',
                borderWidth: 3,
                hoverOffset: 6
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            cutout: '70%',
            plugins: {
                legend: {
                    position: 'bottom',
                    labels: { color: '#94a3b8', font: { family: 'JetBrains Mono', size: 11 } }
                }
            }
        }
    });

    // 3. Daily P&L Bar Chart
    const dayCtx = document.getElementById('dailyPnlChart').getContext('2d');
    if (dailyPnlChartInstance) dailyPnlChartInstance.destroy();

    const dailyData = charts.daily_pnl || [];
    const dayLabels = dailyData.map(d => d.date);
    const dayValues = dailyData.map(d => d.pl);
    const dayColors = dayValues.map(v => v >= 0 ? '#00f59b' : '#ff3366');

    dailyPnlChartInstance = new Chart(dayCtx, {
        type: 'bar',
        data: {
            labels: dayLabels,
            datasets: [{
                label: 'Daily P&L ($)',
                data: dayValues,
                backgroundColor: dayColors,
                borderRadius: 4
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: { display: false },
                tooltip: {
                    callbacks: {
                        label: ctx => ` P&L: ${ctx.parsed.y >= 0 ? '+' : ''}$${ctx.parsed.y.toFixed(2)}`
                    }
                }
            },
            scales: {
                x: {
                    grid: { display: false },
                    ticks: { color: '#64748b', font: { family: 'JetBrains Mono', size: 10 } }
                },
                y: {
                    grid: { color: 'rgba(255, 255, 255, 0.05)' },
                    ticks: {
                        color: '#64748b',
                        font: { family: 'JetBrains Mono', size: 10 },
                        callback: val => `$${val}`
                    }
                }
            }
        }
    });

    // 4. Setup Performance Chart
    const setupCtx = document.getElementById('setupChart').getContext('2d');
    if (setupChartInstance) setupChartInstance.destroy();

    const setups = charts.setups || {};
    const setupLabels = Object.keys(setups);
    const setupValues = setupLabels.map(k => setups[k].pl);
    const setupColors = setupValues.map(v => v >= 0 ? '#00f2fe' : '#f43f5e');

    setupChartInstance = new Chart(setupCtx, {
        type: 'bar',
        data: {
            labels: setupLabels.map(s => s.length > 20 ? s.substring(0, 18) + '...' : s),
            datasets: [{
                label: 'Total Net P&L ($)',
                data: setupValues,
                backgroundColor: setupColors,
                borderRadius: 4
            }]
        },
        options: {
            indexAxis: 'y',
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: { display: false }
            },
            scales: {
                x: {
                    grid: { color: 'rgba(255, 255, 255, 0.05)' },
                    ticks: { color: '#64748b', font: { family: 'JetBrains Mono', size: 10 } }
                },
                y: {
                    grid: { display: false },
                    ticks: { color: '#94a3b8', font: { family: 'JetBrains Mono', size: 10 } }
                }
            }
        }
    });
}

// ----------------- MODAL ACTIONS & FORMS ----------------- //

function openTradeModal() {
    document.getElementById('editTradeId').value = '';
    document.getElementById('tradeModalTitle').textContent = 'Log New Trade Execution';
    document.getElementById('tradeForm').reset();
    document.getElementById('tradeDate').value = new Date().toISOString().split('T')[0];
    document.getElementById('tradeLot').value = '0.01';
    document.getElementById('tradeRR').value = '2.0';
    document.querySelectorAll('input[name="ruleCheck"]').forEach(cb => cb.checked = false);
    updateRuleScoreDisplay();
    document.getElementById('tradeModal').classList.remove('hidden');
}

function closeTradeModal() {
    document.getElementById('tradeModal').classList.add('hidden');
}

function openSettingsModal() {
    fetchSettings();
    document.getElementById('tgTestStatus').textContent = '';
    document.getElementById('settingsModal').classList.remove('hidden');
}

function closeSettingsModal() {
    document.getElementById('settingsModal').classList.add('hidden');
}

function openCalcModal() {
    document.getElementById('calcModal').classList.remove('hidden');
    calculateLotSize();
}

function closeCalcModal() {
    document.getElementById('calcModal').classList.add('hidden');
}

// Risk & Lot Calculator Engine (Rule 8 Enforcer)
function calculateLotSize() {
    const risk = parseFloat(document.getElementById('calcRiskAmount').value) || 5.0;
    const entry = parseFloat(document.getElementById('calcEntry').value);
    const sl = parseFloat(document.getElementById('calcSL').value);
    const asset = document.getElementById('calcAsset').value;

    if (isNaN(entry) || isNaN(sl) || entry <= 0 || sl <= 0 || entry === sl) {
        document.getElementById('calcDistance').textContent = '--';
        document.getElementById('calcLotResult').textContent = '0.01 Lot';
        document.getElementById('calcTPResult').textContent = '--';
        return;
    }

    const distance = Math.abs(entry - sl);
    document.getElementById('calcDistance').textContent = distance.toFixed(2);

    let recommendedLot = 0.01;
    let tp = 0;

    if (asset === 'GOLD') {
        // Gold: 1 lot = 100 oz. $1 move per 0.01 lot = $1.00
        // Total dollar loss for distance D with lot L: D * 100 * L = Risk
        // L = Risk / (D * 100)
        recommendedLot = risk / (distance * 100);
    } else if (asset === 'FX') {
        // Forex: 1 pip = 0.0001 (or 0.01 for JPY). 1 standard lot = $10 per pip. 0.01 lot = $0.10 per pip.
        const pips = distance * 10000;
        recommendedLot = risk / (pips * 10);
    } else {
        recommendedLot = risk / distance;
    }

    recommendedLot = Math.max(0.01, Math.round(recommendedLot * 100) / 100);
    document.getElementById('calcLotResult').textContent = `${recommendedLot.toFixed(2)} Lot`;

    // Rule 4: Minimum 1:2 TP
    const isBuy = entry > sl;
    if (isBuy) {
        tp = entry + (distance * 2);
    } else {
        tp = entry - (distance * 2);
    }
    document.getElementById('calcTPResult').textContent = `$${tp.toFixed(2)} (1:2 R:R)`;
}

// Handle Trade Form Submission
async function handleTradeSubmit(e) {
    e.preventDefault();

    const tradeId = document.getElementById('editTradeId').value;
    const rulesChecked = Array.from(document.querySelectorAll('input[name="ruleCheck"]:checked')).map(cb => parseInt(cb.value));

    const payload = {
        trade_date: document.getElementById('tradeDate').value,
        pair: document.getElementById('tradePair').value,
        direction: document.getElementById('tradeDirection').value,
        setup_type: document.getElementById('tradeSetupType').value,
        timeframe: document.getElementById('tradeTimeframe').value,
        entry_price: parseFloat(document.getElementById('tradeEntry').value) || 0,
        exit_price: parseFloat(document.getElementById('tradeExit').value) || 0,
        stop_loss: parseFloat(document.getElementById('tradeSL').value) || 0,
        take_profit: parseFloat(document.getElementById('tradeTP').value) || 0,
        lot_size: parseFloat(document.getElementById('tradeLot').value) || 0.01,
        profit_loss: parseFloat(document.getElementById('tradePL').value) || 0,
        rr_ratio: parseFloat(document.getElementById('tradeRR').value) || 2.0,
        rules_followed: rulesChecked,
        notes: document.getElementById('tradeNotes').value
    };

    try {
        const url = tradeId ? `/api/trades/${tradeId}` : '/api/trades';
        const method = tradeId ? 'PUT' : 'POST';

        const res = await fetch(url, {
            method: method,
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(payload)
        });

        const data = await res.json();
        if (data.status === 'success') {
            closeTradeModal();
            fetchStats();
            loadTrades();
        } else {
            alert('Error saving trade: ' + (data.message || 'Unknown error'));
        }
    } catch (err) {
        alert('Network error saving trade: ' + err.message);
    }
}

// Edit Trade
async function editTrade(id) {
    try {
        const res = await fetch('/api/trades');
        const trades = await res.json();
        const t = trades.find(item => item.id === id);
        if (!t) return;

        document.getElementById('editTradeId').value = t.id;
        document.getElementById('tradeModalTitle').textContent = `Edit Trade #${t.id} (${t.pair})`;
        document.getElementById('tradeDate').value = t.trade_date;
        document.getElementById('tradePair').value = t.pair;
        document.getElementById('tradeDirection').value = t.direction;
        document.getElementById('tradeSetupType').value = t.setup_type;
        document.getElementById('tradeTimeframe').value = t.timeframe || '';
        document.getElementById('tradeEntry').value = t.entry_price || '';
        document.getElementById('tradeExit').value = t.exit_price || '';
        document.getElementById('tradeSL').value = t.stop_loss || '';
        document.getElementById('tradeTP').value = t.take_profit || '';
        document.getElementById('tradeLot').value = t.lot_size || 0.01;
        document.getElementById('tradePL').value = t.profit_loss;
        document.getElementById('tradeRR').value = t.rr_ratio || 2.0;
        document.getElementById('tradeNotes').value = t.notes || '';

        // Check rules
        const followed = t.rules_followed || [];
        document.querySelectorAll('input[name="ruleCheck"]').forEach(cb => {
            cb.checked = followed.includes(parseInt(cb.value));
        });
        updateRuleScoreDisplay();

        document.getElementById('tradeModal').classList.remove('hidden');
    } catch (err) {
        console.error('Failed to load trade for edit:', err);
    }
}

// Delete Trade
async function deleteTrade(id) {
    if (!confirm(`Are you sure you want to delete trade #${id}?`)) return;

    try {
        const res = await fetch(`/api/trades/${id}`, { method: 'DELETE' });
        const data = await res.json();
        if (data.status === 'success') {
            fetchStats();
            loadTrades();
        }
    } catch (err) {
        alert('Failed to delete trade: ' + err.message);
    }
}

// Handle Settings Form Submission
async function handleSettingsSubmit(e) {
    e.preventDefault();

    const payload = {
        initial_balance: document.getElementById('settingInitialBalance').value,
        target_balance: document.getElementById('settingTargetBalance').value,
        daily_profit_target: document.getElementById('settingDailyTarget').value,
        daily_max_loss: document.getElementById('settingMaxLoss').value,
        telegram_bot_token: document.getElementById('settingTgToken').value,
        telegram_chat_id: document.getElementById('settingTgChatId').value,
        telegram_enabled: document.getElementById('settingTgEnabled').checked ? '1' : '0'
    };

    try {
        const res = await fetch('/api/settings', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(payload)
        });
        const data = await res.json();
        if (data.status === 'success') {
            closeSettingsModal();
            fetchStats();
            alert('Settings saved successfully!');
        }
    } catch (err) {
        alert('Failed to save settings: ' + err.message);
    }
}

// Test Telegram Bot
async function testTelegramBot() {
    const statusEl = document.getElementById('tgTestStatus');
    statusEl.textContent = 'Sending test message...';
    statusEl.className = 'text-[11px] text-cyan-400 font-mono';

    const payload = {
        telegram_bot_token: document.getElementById('settingTgToken').value,
        telegram_chat_id: document.getElementById('settingTgChatId').value
    };

    try {
        const res = await fetch('/api/telegram/test', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(payload)
        });
        const data = await res.json();
        if (data.status === 'success') {
            statusEl.textContent = '✅ Alert sent! Check Telegram!';
            statusEl.className = 'text-[11px] text-emerald-400 font-mono font-bold';
        } else {
            statusEl.textContent = `❌ ${data.message}`;
            statusEl.className = 'text-[11px] text-rose-400 font-mono';
        }
    } catch (err) {
        statusEl.textContent = `❌ Error: ${err.message}`;
        statusEl.className = 'text-[11px] text-rose-400 font-mono';
    }
}

// Load Sample Demo Data
async function loadSampleTrades() {
    if (!confirm('Load sample trading data for preview? This will populate sample trades.')) return;
    try {
        const res = await fetch('/api/seed', { method: 'POST' });
        const data = await res.json();
        if (data.status === 'success') {
            fetchStats();
            loadTrades();
        }
    } catch (err) {
        alert('Failed to load sample data: ' + err.message);
    }
}

// Clear All Trades
async function resetTrades() {
    if (!confirm('Are you sure you want to clear ALL trades? This resets your trading history to 0.')) return;
    try {
        const res = await fetch('/api/reset', { method: 'POST' });
        const data = await res.json();
        if (data.status === 'success') {
            fetchStats();
            loadTrades();
        }
    } catch (err) {
        alert('Failed to reset data: ' + err.message);
    }
}
