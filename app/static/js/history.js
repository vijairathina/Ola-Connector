/**
 * History & Telemetry Visualization
 * Renders SVG charts and telemetry tables without heavy external frameworks.
 */

document.addEventListener("DOMContentLoaded", () => {
  loadBatteryHistory();
  loadChargingSessions();
  loadCommandLogs();
});

async function loadBatteryHistory() {
  try {
    const res = await fetch("/api/history/battery?limit=50");
    const data = await res.json();
    renderChart(data);
  } catch (e) {
    console.error("Failed to load battery history:", e);
  }
}

function renderChart(data) {
  const svg = document.getElementById("battery-chart");
  if (!svg) return;
  svg.innerHTML = "";

  const width = 800;
  const height = 240;
  const padLeft = 45;
  const padRight = 20;
  const padTop = 20;
  const padBottom = 35;

  const chartW = width - padLeft - padRight;
  const chartH = height - padTop - padBottom;

  // Gridlines & Y-axis labels
  [0, 25, 50, 75, 100].forEach(val => {
    const y = padTop + chartH - (val / 100) * chartH;
    
    // Grid line
    const line = document.createElementNS("http://www.w3.org/2000/svg", "line");
    line.setAttribute("x1", padLeft);
    line.setAttribute("x2", width - padRight);
    line.setAttribute("y1", y);
    line.setAttribute("y2", y);
    line.setAttribute("stroke", "rgba(255, 255, 255, 0.06)");
    line.setAttribute("stroke-dasharray", "4,4");
    svg.appendChild(line);

    // Label
    const text = document.createElementNS("http://www.w3.org/2000/svg", "text");
    text.setAttribute("x", padLeft - 10);
    text.setAttribute("y", y + 4);
    text.setAttribute("text-anchor", "end");
    text.setAttribute("fill", "var(--text-muted)");
    text.setAttribute("font-size", "11px");
    text.setAttribute("font-family", "'JetBrains Mono', monospace");
    text.textContent = `${val}%`;
    svg.appendChild(text);
  });

  if (!data || data.length === 0) {
    const emptyText = document.createElementNS("http://www.w3.org/2000/svg", "text");
    emptyText.setAttribute("x", width / 2);
    emptyText.setAttribute("y", height / 2);
    emptyText.setAttribute("text-anchor", "middle");
    emptyText.setAttribute("fill", "var(--text-muted)");
    emptyText.textContent = "No telemetry points recorded yet.";
    svg.appendChild(emptyText);
    return;
  }

  // Calculate points
  const points = [];
  data.forEach((d, i) => {
    const x = padLeft + (i / Math.max(1, data.length - 1)) * chartW;
    const soc = Math.min(100, Math.max(0, d.battery_percent || 0));
    const y = padTop + chartH - (soc / 100) * chartH;
    points.push({ x, y, soc, ts: d.timestamp });
  });

  // Draw smooth path
  let pathD = `M ${points[0].x} ${points[0].y}`;
  for (let i = 1; i < points.length; i++) {
    const prev = points[i - 1];
    const curr = points[i];
    const cpX = (prev.x + curr.x) / 2;
    pathD += ` C ${cpX} ${prev.y}, ${cpX} ${curr.y}, ${curr.x} ${curr.y}`;
  }

  // Gradient area fill
  const areaD = `${pathD} L ${points[points.length - 1].x} ${padTop + chartH} L ${points[0].x} ${padTop + chartH} Z`;
  const areaPath = document.createElementNS("http://www.w3.org/2000/svg", "path");
  areaPath.setAttribute("d", areaD);
  areaPath.setAttribute("fill", "rgba(0, 242, 254, 0.08)");
  svg.appendChild(areaPath);

  // Line stroke
  const linePath = document.createElementNS("http://www.w3.org/2000/svg", "path");
  linePath.setAttribute("d", pathD);
  linePath.setAttribute("fill", "none");
  linePath.setAttribute("stroke", "var(--accent-cyan)");
  linePath.setAttribute("stroke-width", "3");
  linePath.setAttribute("filter", "drop-shadow(0 0 6px rgba(0, 242, 254, 0.4))");
  svg.appendChild(linePath);

  // Draw dots on each point
  points.forEach(p => {
    const circle = document.createElementNS("http://www.w3.org/2000/svg", "circle");
    circle.setAttribute("cx", p.x);
    circle.setAttribute("cy", p.y);
    circle.setAttribute("r", "4");
    circle.setAttribute("fill", "#0a0e17");
    circle.setAttribute("stroke", "var(--accent-cyan)");
    circle.setAttribute("stroke-width", "2");

    const title = document.createElementNS("http://www.w3.org/2000/svg", "title");
    title.textContent = `${p.soc}% at ${p.ts}`;
    circle.appendChild(title);
    svg.appendChild(circle);
  });
}

async function loadChargingSessions() {
  const tbody = document.getElementById("charging-tbody");
  try {
    const res = await fetch("/api/history/charging");
    const sessions = await res.json();
    tbody.innerHTML = "";

    if (!sessions || sessions.length === 0) {
      tbody.innerHTML = "<tr><td colspan='5' style='padding: 1.5rem; text-align: center; color: var(--text-muted);'>No charging sessions recorded yet.</td></tr>";
      return;
    }

    sessions.forEach(s => {
      const tr = document.createElement("tr");
      tr.style.borderBottom = "1px solid var(--border-color)";
      tr.innerHTML = `
        <td style="padding: 0.75rem 0.5rem; font-family: 'JetBrains Mono', monospace; font-size: 0.85rem;">${s.start_time.replace("T", " ").slice(0, 19)}</td>
        <td style="padding: 0.75rem 0.5rem; font-family: 'JetBrains Mono', monospace; font-size: 0.85rem;">${s.end_time ? s.end_time.replace("T", " ").slice(0, 19) : "In Progress"}</td>
        <td style="padding: 0.75rem 0.5rem; font-weight: 600;">${s.start_battery || "--"}%</td>
        <td style="padding: 0.75rem 0.5rem; font-weight: 600; color: var(--accent-emerald);">${s.end_battery || "--"}%</td>
        <td style="padding: 0.75rem 0.5rem;">${s.duration_minutes ? s.duration_minutes + " min" : "--"}</td>
      `;
      tbody.appendChild(tr);
    });
  } catch (e) {
    console.error("Error loading charging sessions:", e);
  }
}

async function loadCommandLogs() {
  const list = document.getElementById("command-log-list");
  try {
    const res = await fetch("/api/history/commands");
    const logs = await res.json();
    list.innerHTML = "";

    if (!logs || logs.length === 0) {
      list.innerHTML = "<div style='text-align: center; padding: 1.5rem; color: var(--text-muted);'>No commands executed yet.</div>";
      return;
    }

    logs.forEach(l => {
      const item = document.createElement("div");
      item.className = "stat-tile";
      item.style.padding = "0.75rem 1rem";
      const icon = l.command.toUpperCase() === "LOCK" ? "🔒" : "🔓";
      const color = l.success ? "var(--accent-emerald)" : "var(--accent-rose)";

      item.innerHTML = `
        <div style="display: flex; align-items: center; gap: 0.75rem;">
          <span>${icon}</span>
          <div>
            <div style="font-weight: 600; font-size: 0.9rem;">${l.command.toUpperCase()} (${l.username})</div>
            <div style="font-family: 'JetBrains Mono', monospace; font-size: 0.75rem; color: var(--text-muted);">${l.timestamp.replace("T", " ").slice(0, 19)}</div>
          </div>
        </div>
        <span style="font-size: 0.8rem; font-weight: 700; color: ${color};">
          ${l.success ? "SUCCESS" : "FAILED"}
        </span>
      `;
      list.appendChild(item);
    });
  } catch (e) {
    console.error("Error loading command logs:", e);
  }
}

async function confirmClearHistory() {
  if (confirm("Are you sure you want to clear all telemetry and command history? This cannot be undone.")) {
    try {
      const res = await fetch("/api/history/clear", { method: "POST" });
      const data = await res.json();
      if (data.success) {
        location.reload();
      }
    } catch (e) {
      alert("Failed to clear history: " + e.message);
    }
  }
}
