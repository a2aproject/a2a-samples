document.addEventListener("DOMContentLoaded", () => {
    const sdkTabs = document.getElementById("sdk-tabs");
    const loadingState = document.getElementById("loading-state");
    const dashboardBody = document.getElementById("dashboard-body");
    const historyCount = document.getElementById("history-count");
    const historyTimelineList = document.getElementById(
        "history-timeline-list"
    );
    const summaryContainer = document.getElementById("summary-container");
    const pairwiseList = document.getElementById("pairwise-list");

    // List of protocols and behaviors to draw the matrix grid
    const PROTOCOLS = ["jsonrpc", "grpc", "http_json"];
    const BEHAVIORS = [
        {
            id: "send_message_flat",
            name: "send_message",
            streaming: false,
            label: "Send Message",
        },
        {
            id: "send_message_streaming",
            name: "send_message",
            streaming: true,
            label: "Send Message (Streaming)",
        },
        {
            id: "push_notification",
            name: "push_notification",
            streaming: false,
            label: "Push Notification",
        },
        {
            id: "resubscribe",
            name: "resubscribe",
            streaming: true,
            label: "Resubscribe",
        },
    ];

    let activeSDK = "python";
    let historyData = [];
    let activeRunIndex = 0;
    let maxTopologySdks = []; // Dynamic list of all SDK nodes in the full parent topology

    // Initial setup: add event listeners to tabs
    sdkTabs.querySelectorAll(".tab-btn").forEach((btn) => {
        btn.addEventListener("click", (e) => {
            const targetBtn = e.currentTarget;
            sdkTabs
                .querySelectorAll(".tab-btn")
                .forEach((b) => b.classList.remove("active"));
            targetBtn.classList.add("active");

            activeSDK = targetBtn.dataset.sdk;
            loadDashboardData(targetBtn.dataset.url);
        });
    });

    // Dynamically track max SDKs from the current run for helper calculations
    function initializeMaxTopologySdks(run) {
        const scenarios = run.scenarios || [];
        let maxSDKs = 0;
        maxTopologySdks = [];
        scenarios.forEach((scenario) => {
            const sdks = scenario.sdks || [];
            if (sdks.length > maxSDKs) {
                maxSDKs = sdks.length;
                maxTopologySdks = [...sdks];
            }
        });
        console.log(
            `[ITK-DASHBOARD] Dynamically derived parent SDKs list:`,
            maxTopologySdks
        );
    }

    // Load data by URL natively (CORS-free served locally)
    async function loadDashboardData(url) {
        console.log(
            `[ITK-DASHBOARD] loadDashboardData called for SDK: ${activeSDK.toUpperCase()}`
        );
        console.log(`[ITK-DASHBOARD] Fetching local asset:`, url);

        showLoading();
        try {
            const response = await fetch(url);
            if (!response.ok) {
                throw new Error(
                    `HTTP error! Status: ${response.status} - ${response.statusText}`
                );
            }
            historyData = await response.json();
            console.log(
                `[ITK-DASHBOARD] JSON successfully loaded. Total runs:`,
                historyData.length
            );
        } catch (err) {
            console.error(
                `[ITK-DASHBOARD] All cascading download streams failed.`,
                err
            );
            showNoDataState(
                `Metrics for the ${activeSDK.toUpperCase()} SDK are not available.`
            );
            return;
        }

        try {
            if (!Array.isArray(historyData) || historyData.length === 0) {
                console.warn(
                    `[ITK-DASHBOARD] Loaded JSON is empty or invalid:`,
                    historyData
                );
                showNoDataState(
                    `Metrics for the ${activeSDK.toUpperCase()} SDK are not available.`
                );
                return;
            }

            // Sort history runs in reverse chronological order (newest first)
            historyData.sort(
                (a, b) => new Date(b.timestamp) - new Date(a.timestamp)
            );
            console.log(
                `[ITK-DASHBOARD] Sorted timeline. Newest run:`,
                historyData[0].timestamp
            );

            activeRunIndex = 0;
            initializeMaxTopologySdks(historyData[0]);
            renderDashboard();
            console.log(`[ITK-DASHBOARD] Dashboard populated successfully!`);
        } catch (err) {
            console.error(
                `[ITK-DASHBOARD] Error building metrics timeline:`,
                err
            );
            showNoDataState(
                `Metrics for the ${activeSDK.toUpperCase()} SDK are not available.`
            );
        }
    }

    function showLoading() {
        loadingState.classList.remove("hidden");
        dashboardBody.classList.add("hidden");
        document.getElementById("dashboard-legend").classList.add("hidden");
    }

    function showNoDataState(message) {
        loadingState.classList.remove("hidden");
        dashboardBody.classList.add("hidden");
        document.getElementById("dashboard-legend").classList.add("hidden");
        loadingState.querySelector("p").textContent = message;
        loadingState.querySelector(".loader").style.display = "none";
    }

    function hideLoading() {
        loadingState.classList.add("hidden");
        dashboardBody.classList.remove("hidden");
        document.getElementById("dashboard-legend").classList.remove("hidden");
        loadingState.querySelector(".loader").style.display = "block";
    }

    // Main Render Function
    function renderDashboard() {
        hideLoading();

        // Render timeline sidebar
        historyCount.textContent = `${historyData.length} runs`;
        historyTimelineList.innerHTML = "";

        historyData.forEach((run, index) => {
            const date = new Date(run.timestamp);
            const formattedTime = date.toLocaleString();
            const shortSha = run.commit_sha.substring(0, 7);
            const runScenarios = run.scenarios || [];
            const allPassed = runScenarios.every((s) => s.passed);
            const statusClass = allPassed ? "passed" : "failed";
            const activeClass = index === activeRunIndex ? "active" : "";

            const item = document.createElement("div");
            item.className = `timeline-item ${statusClass} ${activeClass}`;
            item.innerHTML = `
                <span class="status-dot"></span>
                <div class="timeline-info">
                    <span class="timeline-time">${formattedTime}</span>
                    <span class="timeline-commit">commit: ${shortSha}</span>
                </div>
            `;
            item.addEventListener("click", () => {
                activeRunIndex = index;
                initializeMaxTopologySdks(historyData[index]);
                // Re-render active run context
                document
                    .querySelectorAll(".timeline-item")
                    .forEach((el, idx) => {
                        el.classList.toggle("active", idx === index);
                    });
                renderActiveRun();
            });
            historyTimelineList.appendChild(item);
        });

        renderActiveRun();
    }

    // Render currently selected run statically (Summary Star Topology at top, Pairwise at bottom)
    function renderActiveRun() {
        const run = historyData[activeRunIndex];
        if (!run) return;

        summaryContainer.innerHTML = "";
        pairwiseList.innerHTML = "";

        const scenarios = run.scenarios || [];

        if (scenarios.length === 0) {
            summaryContainer.innerHTML =
                '<div class="panel glass topology-card"><p>No test scenarios executed in this run.</p></div>';
            return;
        }

        // 1. Identify the top-level (maximum node count) topology key and its matching scenarios
        let maxNodes = 0;
        let summaryTopologyKey = "";
        scenarios.forEach((scenario) => {
            const size = (scenario.sdks || []).length;
            if (size > maxNodes) {
                maxNodes = size;
                summaryTopologyKey = (scenario.sdks || []).join(",");
            }
        });

        const summarySdks = summaryTopologyKey
            ? summaryTopologyKey.split(",")
            : [];

        if (summaryTopologyKey) {
            const summaryScenarios = scenarios.filter(
                (s) => (s.sdks || []).join(",") === summaryTopologyKey
            );

            if (summaryScenarios.length > 0) {
                const edges = summaryScenarios[0].edges || [];
                const card = document.createElement("div");
                card.className = "panel glass topology-card";

                const cardId = "topology-card-summary";
                const svgId = "svg-canvas-summary";

                const commitLink = `<a href="https://github.com/a2aproject/a2a-${activeSDK}/commit/${run.commit_sha}" target="_blank" class="mono">${run.commit_sha.substring(0, 7)}</a>`;
                const runDateStr = new Date(run.timestamp).toLocaleString();

                card.innerHTML = `
                    <div class="summary-card-header" style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 16px; padding-bottom: 12px; border-bottom: 1px solid rgba(255, 255, 255, 0.05); font-size: 13px; color: var(--text-muted);">
                        <div class="run-time-info">Nightly Run: <span class="value" style="color: var(--text-main); font-weight: 500;">${runDateStr}</span></div>
                        <div class="commit-info">Commit SHA: ${commitLink}</div>
                    </div>
                    <div class="topology-visual-grid">
                        <!-- Graph Drawing Canvas -->
                        <div class="topology-graph-canvas" id="${cardId}">
                            <svg id="${svgId}" viewBox="0 0 400 300">
                                <defs>
                                    <marker id="arrow-end-${svgId}" viewBox="0 0 10 10" refX="10" refY="5" 
                                        markerWidth="6" markerHeight="6" orient="auto">
                                        <path d="M 0 0 L 10 5 L 0 10 z" fill="rgba(255, 255, 255, 0.3)" />
                                    </marker>
                                    <marker id="arrow-start-${svgId}" viewBox="0 0 10 10" refX="0" refY="5" 
                                        markerWidth="6" markerHeight="6" orient="auto">
                                        <path d="M 10 0 L 0 5 L 10 10 z" fill="rgba(255, 255, 255, 0.3)" />
                                    </marker>
                                </defs>
                            </svg>
                        </div>

                        <!-- Compatibility Matrix Grid -->
                        <div class="matrix-container">
                            <table class="matrix-table">
                                <thead>
                                    <tr>
                                        <th>Behavior / Feature</th>
                                        ${PROTOCOLS.map((p) => `<th>${p}</th>`).join("")}
                                    </tr>
                                </thead>
                                <tbody id="matrix-body-${svgId}">
                                    <!-- Populated dynamically -->
                                </tbody>
                            </table>
                        </div>
                    </div>
                `;

                summaryContainer.appendChild(card);

                // Draw node graph and render fully filled behavior rows vs protocol columns compatibility matrix
                drawTopologyGraph(svgId, summarySdks, edges);
                renderGroupMatrix(`matrix-body-${svgId}`, summaryScenarios);
            }
        } else {
            summaryContainer.innerHTML =
                '<div class="panel glass topology-card"><p>No summary scenario found.</p></div>';
        }

        // 2. Identify all unique pairwise (exactly 2 nodes) topology keys and render their fully-filled grids
        const uniquePairwiseKeys = [];
        scenarios.forEach((scenario) => {
            const sdks = scenario.sdks || [];
            if (sdks.length === 2) {
                const key = sdks.join(",");
                if (!uniquePairwiseKeys.includes(key)) {
                    uniquePairwiseKeys.push(key);
                }
            }
        });

        // Sort pairwise keys deterministically based on the order of SDKs in the summary visualization
        uniquePairwiseKeys.sort((keyA, keyB) => {
            const getRank = (key) => {
                const sdks = key.split(",");
                const ranks = sdks.map((s) => {
                    const idx = summarySdks.findIndex(
                        (sumSdk) => sumSdk.toLowerCase() === s.toLowerCase()
                    );
                    return idx !== -1 ? idx : 999;
                });
                ranks.sort((a, b) => a - b);
                return ranks;
            };
            const rankA = getRank(keyA);
            const rankB = getRank(keyB);
            if (rankA[0] !== rankB[0]) {
                return rankA[0] - rankB[0];
            }
            return rankA[1] - rankB[1];
        });

        if (uniquePairwiseKeys.length > 0) {
            uniquePairwiseKeys.forEach((key, idx) => {
                const pairwiseSdks = key.split(",");
                const pairwiseScenarios = scenarios.filter(
                    (s) => (s.sdks || []).join(",") === key
                );

                if (pairwiseScenarios.length > 0) {
                    const edges = pairwiseScenarios[0].edges || [];
                    const card = document.createElement("div");
                    card.className = "panel glass topology-card";

                    const cardId = `topology-card-pairwise-${idx}`;
                    const svgId = `svg-canvas-pairwise-${idx}`;

                    card.innerHTML = `
                        <div class="topology-visual-grid">
                            <!-- Graph Drawing Canvas -->
                            <div class="topology-graph-canvas" id="${cardId}">
                                <svg id="${svgId}" viewBox="0 0 400 300">
                                    <defs>
                                        <marker id="arrow-end-${svgId}" viewBox="0 0 10 10" refX="10" refY="5" 
                                            markerWidth="6" markerHeight="6" orient="auto">
                                            <path d="M 0 0 L 10 5 L 0 10 z" fill="rgba(255, 255, 255, 0.3)" />
                                        </marker>
                                        <marker id="arrow-start-${svgId}" viewBox="0 0 10 10" refX="0" refY="5" 
                                            markerWidth="6" markerHeight="6" orient="auto">
                                            <path d="M 10 0 L 0 5 L 10 10 z" fill="rgba(255, 255, 255, 0.3)" />
                                        </marker>
                                    </defs>
                                </svg>
                            </div>

                            <!-- Compatibility Matrix Grid -->
                            <div class="matrix-container">
                                <table class="matrix-table">
                                    <thead>
                                        <tr>
                                            <th>Behavior / Feature</th>
                                            ${PROTOCOLS.map((p) => `<th>${p}</th>`).join("")}
                                        </tr>
                                    </thead>
                                    <tbody id="matrix-body-${svgId}">
                                        <!-- Populated dynamically -->
                                    </tbody>
                                </table>
                            </div>
                        </div>
                    `;

                    pairwiseList.appendChild(card);

                    drawTopologyGraph(svgId, pairwiseSdks, edges);
                    renderGroupMatrix(
                        `matrix-body-${svgId}`,
                        pairwiseScenarios
                    );
                }
            });
        } else {
            pairwiseList.innerHTML =
                '<div class="panel glass topology-card"><p>No pairwise scenarios executed in this run.</p></div>';
        }
    }

    // Helper: Format SDK string into pretty display names
    function formatSdkName(sdk) {
        if (!sdk) return "";
        if (sdk.toLowerCase() === "current") return "Current";

        const parts = sdk.split("_");
        let lang = parts[0];
        if (lang.toLowerCase() === "dotnet") {
            lang = ".NET";
        } else {
            lang = lang.charAt(0).toUpperCase() + lang.slice(1);
        }

        if (parts.length > 1) {
            let ver = parts[1];
            if (ver.startsWith("v") && ver.length === 3) {
                ver = `v${ver[1]}.${ver[2]}`;
            }
            return `${lang} ${ver}`;
        }
        return lang;
    }

    // Helper: Get premium styling colors for a given language/SDK string
    function getSdkColors(sdk) {
        const str = (sdk || "").toLowerCase();
        if (str === "current") {
            return { fill: "#1e3a8a", stroke: "#3b82f6", text: "#eff6ff" };
        }
        if (str.startsWith("python")) {
            return { fill: "#422006", stroke: "#eab308", text: "#fef08a" }; // Yellow Gold
        }
        if (str.startsWith("go")) {
            return { fill: "#083344", stroke: "#06b6d4", text: "#cffafe" }; // Cyan
        }
        if (str.startsWith("java")) {
            return { fill: "#450a0a", stroke: "#ef4444", text: "#fee2e2" }; // Red/Orange
        }
        if (str.startsWith("dotnet")) {
            return { fill: "#2e1065", stroke: "#a855f7", text: "#f3e8ff" }; // Purple
        }
        return { fill: "#1e293b", stroke: "#64748b", text: "#f8fafc" }; // Slate Default
    }

    // Helper: Calculate exact intersection of line segment with target node rectangle border
    function getBorderIntersection(fromPos, toPos) {
        const dx = toPos.x - fromPos.x;
        const dy = toPos.y - fromPos.y;
        if (dx === 0 && dy === 0) return { x: fromPos.x, y: fromPos.y };

        const w = 55; // half width of pill rectangle
        const h = 14; // half height of pill rectangle

        const tx = dx !== 0 ? w / Math.abs(dx) : Infinity;
        const ty = dy !== 0 ? h / Math.abs(dy) : Infinity;
        const t = Math.min(tx, ty);

        return {
            x: fromPos.x + t * dx,
            y: fromPos.y + t * dy,
        };
    }

    // Helper: Render SVG Topology Node-Link diagram in a gorgeous tree layout
    function drawTopologyGraph(svgId, sdks, edges) {
        const svg = document.getElementById(svgId);
        if (!svg) return;

        // End and start markers are statically pre-configured in the SVG defs template

        const height = 300;
        const numNodes = sdks.length;

        // Determine root index (Current is usually index 0)
        let rootIdx = sdks.findIndex((s) => s.toLowerCase() === "current");
        if (rootIdx === -1) rootIdx = 0;

        const nodePositions = {};

        // Root positioned on the left
        nodePositions[rootIdx] = { x: 80, y: height / 2, isRoot: true };

        // Other nodes spreading to the right in a clean tree hierarchy
        const childrenIndices = [];
        for (let i = 0; i < numNodes; i++) {
            if (i !== rootIdx) childrenIndices.push(i);
        }

        const numChildren = childrenIndices.length;
        if (numChildren === 1) {
            nodePositions[childrenIndices[0]] = {
                x: 320,
                y: height / 2,
                isRoot: false,
            };
        } else if (numChildren > 1) {
            const startY = 50;
            const endY = height - 50;
            const spacing = (endY - startY) / (numChildren - 1);
            childrenIndices.forEach((childIdx, i) => {
                nodePositions[childIdx] = {
                    x: 320,
                    y: startY + i * spacing,
                    isRoot: false,
                };
            });
        }

        // 1. Draw single connecting lines strictly between the dynamic inner rectangle borders of connected nodes
        const drawnPairs = new Set();
        edges.forEach((edge) => {
            const parts = edge.split("->");
            if (parts.length !== 2) return;
            const fromIdx = parseInt(parts[0], 10);
            const toIdx = parseInt(parts[1], 10);

            if (fromIdx === toIdx) return;

            const pairKey =
                Math.min(fromIdx, toIdx) + "-" + Math.max(fromIdx, toIdx);
            if (drawnPairs.has(pairKey)) return;
            drawnPairs.add(pairKey);

            const fromNode = nodePositions[fromIdx];
            const toNode = nodePositions[toIdx];

            if (fromNode && toNode) {
                const line = document.createElementNS(
                    "http://www.w3.org/2000/svg",
                    "line"
                );

                // Dynamically calculate precise border intersection points for any arbitrary connection angle
                const startPt = getBorderIntersection(fromNode, toNode);
                const endPt = getBorderIntersection(toNode, fromNode);

                line.setAttribute("x1", startPt.x);
                line.setAttribute("y1", startPt.y);
                line.setAttribute("x2", endPt.x);
                line.setAttribute("y2", endPt.y);
                line.setAttribute("class", "svg-edge");

                // Check if reverse edge exists to show bi-directional arrows pointing both ways
                const reverseEdge = `${toIdx}->${fromIdx}`;
                const isBidirectional = edges.includes(reverseEdge);

                if (isBidirectional) {
                    line.classList.add("bi-directional");
                    line.style.stroke = "rgba(255, 255, 255, 0.25)";
                } else {
                    line.style.stroke = "rgba(255, 255, 255, 0.15)";
                }

                svg.appendChild(line);

                // Explicitly render arrowheads near the middle of the edge to avoid any node container overlap
                const dx = endPt.x - startPt.x;
                const dy = endPt.y - startPt.y;
                const length = Math.hypot(dx, dy);
                if (length > 20) {
                    const ux = dx / length;
                    const uy = dy / length;
                    const mx = (startPt.x + endPt.x) / 2;
                    const my = (startPt.y + endPt.y) / 2;
                    const arrowLen = 9;
                    const arrowHalfWidth = 4.5;
                    const arrowFill = "rgba(255, 255, 255, 0.3)";

                    // Helper to append a polygonal arrowhead given tip position and normalized vector pointing to tip
                    const drawArrowhead = (tipX, tipY, vx, vy) => {
                        const baseX = tipX - arrowLen * vx;
                        const baseY = tipY - arrowLen * vy;
                        // Perpendicular vector (-vy, vx)
                        const c1x = baseX - arrowHalfWidth * -vy;
                        const c1y = baseY - arrowHalfWidth * vx;
                        const c2x = baseX + arrowHalfWidth * -vy;
                        const c2y = baseY + arrowHalfWidth * vx;

                        const poly = document.createElementNS(
                            "http://www.w3.org/2000/svg",
                            "polygon"
                        );
                        poly.setAttribute(
                            "points",
                            `${tipX},${tipY} ${c1x},${c1y} ${c2x},${c2y}`
                        );
                        poly.setAttribute("fill", arrowFill);
                        svg.appendChild(poly);
                    };

                    if (isBidirectional) {
                        // Calculate 1/4 and 3/4 split points along the line segment
                        const pt1_4X = startPt.x + 0.25 * dx;
                        const pt1_4Y = startPt.y + 0.25 * dy;
                        const pt3_4X = startPt.x + 0.75 * dx;
                        const pt3_4Y = startPt.y + 0.75 * dy;

                        // Forward arrow centered at 3/4 split pointing towards target node
                        drawArrowhead(
                            pt3_4X + (arrowLen / 2) * ux,
                            pt3_4Y + (arrowLen / 2) * uy,
                            ux,
                            uy
                        );
                        // Reverse arrow centered at 1/4 split pointing towards source node
                        drawArrowhead(
                            pt1_4X - (arrowLen / 2) * ux,
                            pt1_4Y - (arrowLen / 2) * uy,
                            -ux,
                            -uy
                        );
                    } else {
                        // Single direction arrow pointing to target node exactly at midpoint
                        drawArrowhead(
                            mx + (arrowLen / 2) * ux,
                            my + (arrowLen / 2) * uy,
                            ux,
                            uy
                        );
                    }
                }
            }
        });

        // 2. Draw pretty stylized SDK nodes
        sdks.forEach((sdk, idx) => {
            const pos = nodePositions[idx];
            if (!pos) return;

            const g = document.createElementNS(
                "http://www.w3.org/2000/svg",
                "g"
            );
            g.setAttribute(
                "class",
                `svg-node ${pos.isRoot ? "root-node" : ""}`
            );

            const rectWidth = 110;
            const rectHeight = 28;
            const colors = getSdkColors(sdk);

            const rect = document.createElementNS(
                "http://www.w3.org/2000/svg",
                "rect"
            );
            rect.setAttribute("x", pos.x - rectWidth / 2);
            rect.setAttribute("y", pos.y - rectHeight / 2);
            rect.setAttribute("width", rectWidth);
            rect.setAttribute("height", rectHeight);
            rect.setAttribute("rx", "6");
            rect.setAttribute("ry", "6");

            // Apply dedicated language color codes inline
            rect.style.fill = colors.fill;
            rect.style.stroke = colors.stroke;
            rect.style.strokeWidth = pos.isRoot ? "2px" : "1.5px";

            const text = document.createElementNS(
                "http://www.w3.org/2000/svg",
                "text"
            );
            text.setAttribute("x", pos.x);
            text.setAttribute("y", pos.y);
            text.textContent = formatSdkName(sdk);
            text.style.fill = colors.text;
            text.style.fontSize = "11px";
            text.style.fontWeight = "600";

            g.appendChild(rect);
            g.appendChild(text);
            svg.appendChild(g);
        });
    }

    // Render Matrix cells for a group of scenarios sharing the same topology
    function renderGroupMatrix(tbodyId, groupScenarios) {
        const tbody = document.getElementById(tbodyId);
        if (!tbody) return;

        tbody.innerHTML = "";

        BEHAVIORS.forEach((behavior) => {
            const tr = document.createElement("tr");

            // Cell 1: Behavior Name
            const behaviorTd = document.createElement("td");
            behaviorTd.className = "protocol-name";
            behaviorTd.textContent = behavior.label;
            tr.appendChild(behaviorTd);

            // Cells 2..N: Protocols
            PROTOCOLS.forEach((proto) => {
                const td = document.createElement("td");

                // Find all scenarios in the group that cover this Protocol and Behavior
                const matchingScenarios = groupScenarios.filter((scenario) => {
                    const scenarioProtos = scenario.protocols || [];
                    const hasProtocol = scenarioProtos.includes(proto);

                    const matchesBehavior = scenario.behavior === behavior.name;
                    const matchesStreaming =
                        (scenario.streaming === true) ===
                        (behavior.streaming === true);

                    return hasProtocol && matchesBehavior && matchesStreaming;
                });

                if (matchingScenarios.length > 0) {
                    // Determine if all matching scenarios passed
                    const allPassed = matchingScenarios.every((s) => s.passed);
                    if (allPassed) {
                        td.className = "cell-pass";
                        td.textContent = "PASS";
                    } else {
                        td.className = "cell-fail";
                        td.textContent = "FAIL";
                    }
                } else {
                    // No scenario covers this configuration for this topology
                    td.className = "cell-disabled";
                    td.textContent = "-";
                }

                tr.appendChild(td);
            });

            tbody.appendChild(tr);
        });
    }

    // Initialize dashboard with Python SDK by default
    loadDashboardData("itk_python.json");
});
