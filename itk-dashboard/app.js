document.addEventListener("DOMContentLoaded", () => {
    const sdkTabs = document.getElementById("sdk-tabs");
    const loadingState = document.getElementById("loading-state");
    const dashboardBody = document.getElementById("dashboard-body");
    const lastRunTime = document.getElementById("last-run-time");
    const lastCommit = document.getElementById("last-commit");
    const historyCount = document.getElementById("history-count");
    const historyTimelineList = document.getElementById(
        "history-timeline-list"
    );
    const topologiesList = document.getElementById("topologies-list");

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

    // Render currently selected run
    function renderActiveRun() {
        const run = historyData[activeRunIndex];
        if (!run) return;

        // Update Header Meta
        const runDate = new Date(run.timestamp);
        lastRunTime.textContent = runDate.toLocaleString();
        lastCommit.innerHTML = `<a href="https://github.com/a2aproject/a2a-${activeSDK}/commit/${run.commit_sha}" target="_blank">${run.commit_sha.substring(0, 7)}</a>`;

        topologiesList.innerHTML = "";

        // Process and render each scenario / topology card
        const scenarios = run.scenarios || [];

        if (scenarios.length === 0) {
            topologiesList.innerHTML =
                '<div class="panel glass topology-card"><p>No test scenarios executed in this run.</p></div>';
            return;
        }

        // Group scenarios by SDK list
        const groupedTopologies = {};
        scenarios.forEach((scenario) => {
            const sdkKey = (scenario.sdks || []).join(",");
            if (!groupedTopologies[sdkKey]) {
                groupedTopologies[sdkKey] = {
                    sdks: scenario.sdks || [],
                    edges: scenario.edges || [],
                    traversal: scenario.traversal || "euler",
                    scenarios: [],
                };
            }
            groupedTopologies[sdkKey].scenarios.push(scenario);
        });

        // Render each grouped topology card
        Object.keys(groupedTopologies).forEach((sdkKey, idx) => {
            const group = groupedTopologies[sdkKey];
            const card = document.createElement("div");
            card.className = "panel glass topology-card";

            const cardId = `topology-card-${idx}`;
            const svgId = `svg-canvas-${idx}`;

            // Create clean dynamic name based on list of SDKs
            const topologyName = `Star Topology (${group.sdks.length} Nodes)`;

            card.innerHTML = `
                <div class="topology-visual-grid">
                    <!-- Graph Drawing Canvas -->
                    <div class="topology-graph-canvas" id="${cardId}">
                        <svg id="${svgId}" viewBox="0 0 400 300">
                            <defs>
                                <!-- Arrowhead Marker definition for directed edges -->
                                <marker id="arrow-${idx}" viewBox="0 0 10 10" refX="20" refY="5" 
                                    markerWidth="6" markerHeight="6" orient="auto-start-reverse">
                                    <path d="M 0 0 L 10 5 L 0 10 z" fill="rgba(255, 255, 255, 0.3)" />
                                </marker>
                            </defs>
                            <!-- SVG content drawn dynamically -->
                        </svg>
                    </div>

                    <!-- Compatibility Matrix Grid -->
                    <div class="matrix-container">
                        <table class="matrix-table">
                            <thead>
                                <tr>
                                    <th>Protocol</th>
                                    ${BEHAVIORS.map((b) => `<th>${b.label}</th>`).join("")}
                                </tr>
                            </thead>
                            <tbody id="matrix-body-${idx}">
                                <!-- Populated by JS -->
                            </tbody>
                        </table>
                    </div>
                </div>
            `;

            topologiesList.appendChild(card);

            // 1. Draw topology graph SVG
            drawTopologyGraph(svgId, group.sdks, group.edges, topologyName);

            // 2. Render the consolidated matrix content for this group
            renderGroupMatrix(`matrix-body-${idx}`, group.scenarios);
        });
    }

    // Helper: Render SVG Topology Node-Link diagram
    function drawTopologyGraph(svgId, sdks, edges, scenarioName) {
        const svg = document.getElementById(svgId);
        if (!svg) return;

        const width = 400;
        const height = 300;
        const centerX = width / 2;
        const centerY = height / 2;
        const numNodes = sdks.length;

        const nodePositions = {};

        // Determine Layout strategy
        const isStar =
            scenarioName.toLowerCase().includes("star") || numNodes > 3;
        const isChain =
            scenarioName.toLowerCase().includes("chain") ||
            scenarioName.toLowerCase().includes("linear");

        if (isStar) {
            // Node 0 in center, others arranged in circle
            nodePositions[0] = { x: centerX, y: centerY, isCenter: true };
            const radius = 115;
            for (let i = 1; i < numNodes; i++) {
                const angle =
                    ((i - 1) / (numNodes - 1)) * 2 * Math.PI - Math.PI / 2;
                nodePositions[i] = {
                    x: centerX + radius * Math.cos(angle),
                    y: centerY + radius * Math.sin(angle),
                    isCenter: false,
                };
            }
        } else if (isChain && numNodes > 1) {
            // Arrange horizontally in a line
            const startX = 60;
            const spacing = (width - 2 * startX) / (numNodes - 1);
            for (let i = 0; i < numNodes; i++) {
                nodePositions[i] = {
                    x: startX + i * spacing,
                    y: centerY,
                    isCenter: false,
                };
            }
        } else {
            // Standard circular layout
            const radius = 110;
            for (let i = 0; i < numNodes; i++) {
                const angle = (i / numNodes) * 2 * Math.PI - Math.PI / 2;
                nodePositions[i] = {
                    x: centerX + radius * Math.cos(angle),
                    y: centerY + radius * Math.sin(angle),
                    isCenter: false,
                };
            }
        }

        // 1. Draw edges/links
        edges.forEach((edge) => {
            const parts = edge.split("->");
            if (parts.length !== 2) return;
            const fromIdx = parseInt(parts[0], 10);
            const toIdx = parseInt(parts[1], 10);

            const fromNode = nodePositions[fromIdx];
            const toNode = nodePositions[toIdx];

            if (fromNode && toNode) {
                const line = document.createElementNS(
                    "http://www.w3.org/2000/svg",
                    "line"
                );
                line.setAttribute("x1", fromNode.x);
                line.setAttribute("y1", fromNode.y);
                line.setAttribute("x2", toNode.x);
                line.setAttribute("y2", toNode.y);
                line.setAttribute("class", "svg-edge");
                line.setAttribute(
                    "marker-end",
                    `url(#arrow-${svgId.split("-").pop()})`
                );

                // Style bi-directional links subtly different
                const reverseEdge = `${toIdx}->${fromIdx}`;
                if (edges.includes(reverseEdge)) {
                    line.setAttribute("class", "svg-edge bi-directional");
                }

                svg.appendChild(line);
            }
        });

        // 2. Draw nodes
        sdks.forEach((sdk, idx) => {
            const pos = nodePositions[idx];
            if (!pos) return;

            const g = document.createElementNS(
                "http://www.w3.org/2000/svg",
                "g"
            );
            g.setAttribute(
                "class",
                `svg-node ${pos.isCenter ? "center-node" : ""}`
            );

            const rectWidth = 100;
            const rectHeight = 24;

            const rect = document.createElementNS(
                "http://www.w3.org/2000/svg",
                "rect"
            );
            rect.setAttribute("x", pos.x - rectWidth / 2);
            rect.setAttribute("y", pos.y - rectHeight / 2);
            rect.setAttribute("width", rectWidth);
            rect.setAttribute("height", rectHeight);

            const text = document.createElementNS(
                "http://www.w3.org/2000/svg",
                "text"
            );
            text.setAttribute("x", pos.x);
            text.setAttribute("y", pos.y);
            text.textContent = sdk;

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

        PROTOCOLS.forEach((proto) => {
            const tr = document.createElement("tr");

            // Cell 1: Protocol Name
            const protocolTd = document.createElement("td");
            protocolTd.className = "protocol-name";
            protocolTd.textContent = proto;
            tr.appendChild(protocolTd);

            // Cells 2..5: Behaviors
            BEHAVIORS.forEach((behavior) => {
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
