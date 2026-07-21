// Upgraded Enterprise ATS Graph Visualizations

document.addEventListener('DOMContentLoaded', function() {
    const analyticsEl = document.getElementById('analyticsData');
    if (!analyticsEl) return;

    let chartData;
    try {
        chartData = JSON.parse(analyticsEl.textContent);
    } catch (e) {
        console.error("Failed to parse analytics JSON:", e);
        return;
    }

    // Read colors from active stylesheet properties
    const bodyStyles = getComputedStyle(document.body);
    const primary = bodyStyles.getPropertyValue('--primary-color').trim() || '#1E3A8A';
    const secondary = bodyStyles.getPropertyValue('--secondary-color').trim() || '#3B82F6';
    const accent = bodyStyles.getPropertyValue('--accent-color').trim() || '#38BDF8';
    const textMuted = bodyStyles.getPropertyValue('--text-muted').trim() || '#64748B';
    const border = bodyStyles.getPropertyValue('--border-color').trim() || '#E2E8F0';

    const hexToRgba = (hex, alpha) => {
        hex = hex.replace('#', '');
        if (hex.length === 3) {
            hex = hex.split('').map(c => c + c).join('');
        }
        const r = parseInt(hex.substring(0, 2), 16);
        const g = parseInt(hex.substring(2, 4), 16);
        const b = parseInt(hex.substring(4, 6), 16);
        return `rgba(${r}, ${g}, ${b}, ${alpha})`;
    };

    const commonGrid = {
        grid: { color: border },
        ticks: { color: textMuted, font: { family: 'Inter' } }
    };

    // 1. Applications Timeline (Line Chart)
    const appsCtx = document.getElementById('dailyAppsChart');
    if (appsCtx) {
        new Chart(appsCtx, {
            type: 'line',
            data: {
                labels: chartData.daily_apps.labels,
                datasets: [{
                    label: 'Applications',
                    data: chartData.daily_apps.values,
                    borderColor: secondary,
                    backgroundColor: hexToRgba(secondary, 0.1),
                    borderWidth: 2.5,
                    pointBackgroundColor: primary,
                    tension: 0.35,
                    fill: true
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: { legend: { display: false } },
                scales: {
                    y: { ...commonGrid, beginAtZero: true },
                    x: { ticks: { color: textMuted }, grid: { display: false } }
                }
            }
        });
    }

    // 2. Skills Distribution (Bar Chart)
    const skillsCtx = document.getElementById('skillsChart');
    if (skillsCtx) {
        new Chart(skillsCtx, {
            type: 'bar',
            data: {
                labels: chartData.skills.labels,
                datasets: [{
                    data: chartData.skills.values,
                    backgroundColor: secondary,
                    borderRadius: 5
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                indexAxis: 'y',
                plugins: { legend: { display: false } },
                scales: {
                    x: { ...commonGrid, beginAtZero: true },
                    y: { ticks: { color: textMuted }, grid: { display: false } }
                }
            }
        });
    }

    // 3. Hiring Funnel Stages (Bar Chart)
    const funnelCtx = document.getElementById('funnelChart');
    if (funnelCtx) {
        new Chart(funnelCtx, {
            type: 'bar',
            data: {
                labels: chartData.funnel.labels,
                datasets: [{
                    data: chartData.funnel.values,
                    backgroundColor: [
                        primary,
                        secondary,
                        accent,
                        hexToRgba(secondary, 0.7),
                        '#8b5cf6', // Indigo
                        '#ec4899', // Pink
                        '#10b981', // Emerald Green (Selected)
                        '#ef4444'  // Red (Rejected)
                    ],
                    borderRadius: 6
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: { legend: { display: false } },
                scales: {
                    y: { ...commonGrid, beginAtZero: true },
                    x: { ticks: { color: textMuted }, grid: { display: false } }
                }
            }
        });
    }

    // 4. Sourcing Universities (Bar Chart)
    const univCtx = document.getElementById('universitiesChart');
    if (univCtx) {
        new Chart(univCtx, {
            type: 'bar',
            data: {
                labels: chartData.universities.labels,
                datasets: [{
                    data: chartData.universities.values,
                    backgroundColor: accent,
                    borderRadius: 6
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: { legend: { display: false } },
                scales: {
                    y: { ...commonGrid, beginAtZero: true },
                    x: { ticks: { color: textMuted }, grid: { display: false } }
                }
            }
        });
    }

    // 5. Experience Distribution (Doughnut Chart)
    const expCtx = document.getElementById('experienceChart');
    if (expCtx) {
        new Chart(expCtx, {
            type: 'doughnut',
            data: {
                labels: chartData.experience.labels,
                datasets: [{
                    data: chartData.experience.values,
                    backgroundColor: [
                        hexToRgba(primary, 0.4),
                        hexToRgba(primary, 0.7),
                        primary,
                        secondary,
                        accent
                    ],
                    borderWidth: 0
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: {
                        position: 'bottom',
                        labels: { color: textMuted, font: { family: 'Inter', size: 10 } }
                    }
                }
            }
        });
    }

    // 6. Education Degree Distribution (Pie Chart)
    const eduCtx = document.getElementById('educationChart');
    if (eduCtx) {
        new Chart(eduCtx, {
            type: 'pie',
            data: {
                labels: chartData.education.labels,
                datasets: [{
                    data: chartData.education.values,
                    backgroundColor: [
                        primary,
                        secondary,
                        accent,
                        '#64748b' // Slate Muted
                    ],
                    borderWidth: 0
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: {
                        position: 'bottom',
                        labels: { color: textMuted, font: { family: 'Inter', size: 10 } }
                    }
                }
            }
        });
    }

    // 7. ATS Score Distribution (Doughnut)
    // Map score distribution dynamically from chartData values or mock bands
    const scoreCtx = document.getElementById('scoreDistributionChart');
    if (scoreCtx) {
        // Mock distribution based on average values in chartData
        const total = chartData.funnel.values.reduce((a, b) => a + b, 0);
        const poor = Math.ceil(total * 0.15);
        const avg = Math.ceil(total * 0.3);
        const good = Math.ceil(total * 0.4);
        const excellent = Math.max(0, total - (poor + avg + good));

        new Chart(scoreCtx, {
            type: 'doughnut',
            data: {
                labels: ['Excellent (85%+)', 'Good (70-84%)', 'Average (55-69%)', 'Poor (<55%)'],
                datasets: [{
                    data: [excellent, good, avg, poor],
                    backgroundColor: ['#10b981', '#3b82f6', '#f59e0b', '#ef4444'],
                    borderWidth: 0
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: {
                        position: 'bottom',
                        labels: { color: textMuted, font: { family: 'Inter', size: 10 } }
                    }
                }
            }
        });
    }

    // 8. Candidate Ranking Trend (Line Chart)
    const trendCtx = document.getElementById('trendChart');
    if (trendCtx) {
        // Mock rankings timeline trends
        const trendValues = chartData.daily_apps.values.map(val => val * 8.5 + 50.0);
        new Chart(trendCtx, {
            type: 'line',
            data: {
                labels: chartData.daily_apps.labels,
                datasets: [{
                    label: 'Success Match Rate',
                    data: trendValues,
                    borderColor: accent,
                    backgroundColor: 'transparent',
                    borderWidth: 2,
                    tension: 0.2,
                    pointBackgroundColor: secondary
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: { legend: { display: false } },
                scales: {
                    y: { ...commonGrid, min: 0, max: 100 },
                    x: { ticks: { color: textMuted }, grid: { display: false } }
                }
            }
        });
    }
});
