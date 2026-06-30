let trendChartInstance = null;
let durationChartInstance = null;
let heatmapChartInstance = null;
let roomsChartInstance = null;

let currentPage = 1;
let currentLimit = 15;
let currentSearch = "";
let currentTimezone = "UTC";

document.addEventListener("DOMContentLoaded", () => {
    initMouseGlow();
    setupEventListeners();
    loadDashboardStats();
    loadMeetingsTable();
});

function setupEventListeners() {
    const yearSelect = document.getElementById("filter-year");
    if (yearSelect) {
        yearSelect.addEventListener("change", (e) => {
            loadDashboardStats(e.target.value);
        });
    }

    const searchInput = document.getElementById("table-search");
    let debounceTimer;
    if (searchInput) {
        searchInput.addEventListener("input", (e) => {
            clearTimeout(debounceTimer);
            debounceTimer = setTimeout(() => {
                currentSearch = e.target.value;
                currentPage = 1;
                loadMeetingsTable();
            }, 300);
        });
    }

    const tzSelect = document.getElementById("tz-select");
    if (tzSelect) {
        tzSelect.addEventListener("change", (e) => {
            currentTimezone = e.target.value;
            updateTimezoneHeader();
            loadMeetingsTable();
        });
    }

    document.getElementById("btn-prev").addEventListener("click", () => {
        if (currentPage > 1) {
            currentPage--;
            loadMeetingsTable();
        }
    });

    document.getElementById("btn-next").addEventListener("click", () => {
        currentPage++;
        loadMeetingsTable();
    });
}

function updateTimezoneHeader() {
    const th = document.getElementById("th-start-time");
    if (!th) return;
    if (currentTimezone === "UTC") {
        th.textContent = "Start Time (UTC)";
    } else if (currentTimezone === "LOCAL") {
        const short = Intl.DateTimeFormat().resolvedOptions().timeZone;
        th.textContent = `Start Time (${short})`;
    } else {
        th.textContent = `Start Time (${currentTimezone})`;
    }
}

function convertUTCToTimezone(utcString, timezone) {
    if (!utcString || utcString.length < 19) return utcString || "";
    // Parse the UTC datetime string "YYYY-MM-DD HH:MM:SS UTC"
    const cleaned = utcString.replace(" UTC", "").trim();
    const date = new Date(cleaned + "Z"); // Treat as UTC
    if (isNaN(date.getTime())) return cleaned;

    if (timezone === "UTC") {
        return cleaned;
    }

    try {
        let options = {
            year: "numeric",
            month: "2-digit",
            day: "2-digit",
            hour: "2-digit",
            minute: "2-digit",
            second: "2-digit",
            hour12: false
        };

        if (timezone === "LOCAL") {
            // Use browser's local timezone
        } else {
            options.timeZone = timezone;
        }

        const formatter = new Intl.DateTimeFormat("en-CA", options);
        const parts = formatter.formatToParts(date);
        const get = (type) => (parts.find(p => p.type === type) || {}).value || "";
        return `${get("year")}-${get("month")}-${get("day")} ${get("hour")}:${get("minute")}:${get("second")}`;
    } catch (e) {
        return cleaned;
    }
}

function initMouseGlow() {
    document.addEventListener("mousemove", (e) => {
        for (const card of document.querySelectorAll(".glass-card")) {
            const rect = card.getBoundingClientRect();
            const x = e.clientX - rect.left;
            const y = e.clientY - rect.top;
            card.style.setProperty("--mouse-x", `${x}px`);
            card.style.setProperty("--mouse-y", `${y}px`);
        }
    });
}

async function loadDashboardStats(year = "ALL") {
    try {
        const urlParams = new URLSearchParams(window.location.search);
        const modeParam = urlParams.get("mode") === "owner" ? "&mode=owner" : "";
        const response = await fetch(`/api/stats?year=${year}${modeParam}`);
        const data = await response.json();

        updateYearDropdown(data.years, year);
        updateKPIs(data.kpi);
        renderInsights(data.insights);
        renderCharts(data);
    } catch (err) {
        console.error("Error loading stats:", err);
    }
}

function updateYearDropdown(years, selectedYear) {
    const select = document.getElementById("filter-year");
    if (!select || select.options.length > 1) return; // Populate only once

    years.forEach(y => {
        const opt = document.createElement("option");
        opt.value = y;
        opt.textContent = y;
        select.appendChild(opt);
    });
    select.value = selectedYear;
}

function updateKPIs(kpi) {
    animateValue("kpi-total", kpi.total_meetings, 0);
    document.getElementById("kpi-hours").textContent = `${kpi.total_hours} hrs`;
    document.getElementById("kpi-days-sub").textContent = `~${kpi.total_days} full days of sync`;
    document.getElementById("kpi-avg").textContent = `${kpi.avg_duration_min} min`;
    
    if (kpi.longest_meeting) {
        document.getElementById("kpi-longest").textContent = kpi.longest_meeting.duration_fmt;
        document.getElementById("kpi-longest-sub").textContent = `${kpi.longest_meeting.code} on ${kpi.longest_meeting.date}`;
    }
}

function animateValue(id, end, decimals = 0) {
    const obj = document.getElementById(id);
    if (!obj) return;
    let start = 0;
    const duration = 1000;
    const startTime = performance.now();

    function update(now) {
        const elapsed = now - startTime;
        const progress = Math.min(elapsed / duration, 1);
        const current = start + (end - start) * easeOutQuart(progress);
        obj.textContent = current.toFixed(decimals);
        if (progress < 1) {
            requestAnimationFrame(update);
        }
    }
    requestAnimationFrame(update);
}

function easeOutQuart(x) {
    return 1 - Math.pow(1 - x, 4);
}

function renderInsights(insights) {
    const container = document.getElementById("insights-grid");
    if (!container) return;
    container.innerHTML = "";

    insights.forEach((item, idx) => {
        const card = document.createElement("div");
        card.className = "glass-card insight-card animate-in";
        card.style.animationDelay = `${idx * 0.1}s`;
        card.innerHTML = `
            <div class="insight-top">
                <span class="kpi-icon icon-purple">${item.icon}</span>
                <span class="insight-tag">${item.tag}</span>
            </div>
            <h4>${item.title}</h4>
            <p>${item.description}</p>
        `;
        container.appendChild(card);
    });
}

function renderCharts(data) {
    Chart.defaults.color = "#94A3B8";
    Chart.defaults.font.family = "'Inter', sans-serif";

    // 1. Trend Chart
    const trendCtx = document.getElementById("trendChart").getContext("2d");
    if (trendChartInstance) trendChartInstance.destroy();

    const gradientTrend = trendCtx.createLinearGradient(0, 0, 0, 300);
    gradientTrend.addColorStop(0, "rgba(99, 102, 241, 0.4)");
    gradientTrend.addColorStop(1, "rgba(99, 102, 241, 0.0)");

    trendChartInstance = new Chart(trendCtx, {
        type: "line",
        data: {
            labels: data.monthly_trend.map(d => d.month),
            datasets: [{
                label: "Meetings Count",
                data: data.monthly_trend.map(d => d.count),
                borderColor: "#6366F1",
                backgroundColor: gradientTrend,
                fill: true,
                tension: 0.4,
                borderWidth: 3,
                pointRadius: 4,
                pointBackgroundColor: "#6366F1"
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: { legend: { display: false } },
            scales: {
                y: { grid: { color: "rgba(255,255,255,0.05)" } },
                x: { grid: { display: false } }
            }
        }
    });

    // 2. Duration Doughnut Chart
    const durCtx = document.getElementById("durationChart").getContext("2d");
    if (durationChartInstance) durationChartInstance.destroy();

    durationChartInstance = new Chart(durCtx, {
        type: "doughnut",
        data: {
            labels: Object.keys(data.buckets),
            datasets: [{
                data: Object.values(data.buckets),
                backgroundColor: ["#06B6D4", "#10B981", "#6366F1", "#EC4899"],
                borderWidth: 0,
                hoverOffset: 6
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            cutout: "72%",
            plugins: {
                legend: { position: "bottom", labels: { padding: 15, usePointStyle: true } }
            }
        }
    });

    // 3. Heatmap Chart (Day of Week)
    const heatCtx = document.getElementById("heatmapChart").getContext("2d");
    if (heatmapChartInstance) heatmapChartInstance.destroy();

    heatmapChartInstance = new Chart(heatCtx, {
        type: "bar",
        data: {
            labels: Object.keys(data.day_of_week),
            datasets: [{
                label: "Meetings",
                data: Object.values(data.day_of_week),
                backgroundColor: "rgba(236, 72, 153, 0.7)",
                hoverBackgroundColor: "#EC4899",
                borderRadius: 8
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: { legend: { display: false } },
            scales: {
                y: { grid: { color: "rgba(255,255,255,0.05)" } },
                x: { grid: { display: false } }
            }
        }
    });

    // 4. Top Rooms Chart — Horizontal bar showing HOURS per room
    const roomsCtx = document.getElementById("roomsChart").getContext("2d");
    if (roomsChartInstance) roomsChartInstance.destroy();

    const roomColors = [
        "rgba(16, 185, 129, 0.8)",
        "rgba(99, 102, 241, 0.8)",
        "rgba(236, 72, 153, 0.8)",
        "rgba(6, 182, 212, 0.8)",
        "rgba(245, 158, 11, 0.8)",
        "rgba(139, 92, 246, 0.8)",
        "rgba(244, 63, 94, 0.8)",
        "rgba(34, 197, 94, 0.8)"
    ];

    roomsChartInstance = new Chart(roomsCtx, {
        type: "bar",
        data: {
            labels: data.top_rooms.map(r => r.code),
            datasets: [{
                label: "Hours Spent",
                data: data.top_rooms.map(r => r.hours),
                backgroundColor: roomColors.slice(0, data.top_rooms.length),
                borderRadius: 6
            }]
        },
        options: {
            indexAxis: "y",
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: { display: false },
                tooltip: {
                    callbacks: {
                        label: (ctx) => {
                            const room = data.top_rooms[ctx.dataIndex];
                            return `${room.hours} hours across ${room.count} meetings`;
                        }
                    }
                }
            },
            scales: {
                x: {
                    grid: { color: "rgba(255,255,255,0.05)" },
                    title: { display: true, text: "Hours", color: "#64748B" }
                },
                y: { grid: { display: false } }
            }
        }
    });
}

async function loadMeetingsTable() {
    try {
        const urlParams = new URLSearchParams(window.location.search);
        const modeParam = urlParams.get("mode") === "owner" ? "&mode=owner" : "";
        const response = await fetch(`/api/meetings?page=${currentPage}&limit=${currentLimit}&search=${encodeURIComponent(currentSearch)}${modeParam}`);
        const data = await response.json();
        
        renderTableRows(data.records);
        updatePagination(data.pagination);
    } catch (err) {
        console.error("Error loading table:", err);
    }
}

function renderTableRows(records) {
    const tbody = document.getElementById("table-body");
    if (!tbody) return;
    tbody.innerHTML = "";

    if (records.length === 0) {
        tbody.innerHTML = `<tr><td colspan="5" style="text-align: center; color: var(--text-dim);">No meeting records found.</td></tr>`;
        return;
    }

    records.forEach(r => {
        const tr = document.createElement("tr");
        const partBadge = r.participation === "PARTICIPATED"
            ? `<span class="badge-part part-yes">Participated</span>`
            : `<span class="badge-part part-no">Invited / Calendar</span>`;

        const displayTime = convertUTCToTimezone(r.start_time, currentTimezone);

        tr.innerHTML = `
            <td class="whitespace-nowrap"><span class="badge-code whitespace-nowrap inline-block font-mono min-w-max">${r.meeting_code}</span></td>
            <td class="whitespace-nowrap">${displayTime}</td>
            <td style="font-weight: 600;" class="whitespace-nowrap">${r.duration_fmt}</td>
            <td class="whitespace-nowrap">${r.day_of_week}</td>
            <td class="whitespace-nowrap">${partBadge}</td>
        `;
        tbody.appendChild(tr);
    });
}

function updatePagination(pagination) {
    const prevBtn = document.getElementById("btn-prev");
    const nextBtn = document.getElementById("btn-next");
    const pageInfo = document.getElementById("page-info");

    if (prevBtn) prevBtn.disabled = pagination.page <= 1;
    if (nextBtn) nextBtn.disabled = pagination.page >= pagination.total_pages;
    if (pageInfo) pageInfo.textContent = `Page ${pagination.page} of ${pagination.total_pages}`;
}
