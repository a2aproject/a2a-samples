document.addEventListener("DOMContentLoaded", function () {
    const sendButton = document.getElementById("send-button");
    const messageInput = document.getElementById("message-input");
    const chatMessages = document.getElementById("chat-messages");
    const a2aEndpointInput = document.getElementById("a2a-endpoint");
    const initializeButton = document.getElementById("initialize-button");
    const authCheckbox = document.getElementById("auth-checkbox");
    const configContainer = document.getElementById("config-container");
    const configHeader = document.getElementById("config-header");
    const agentCardContainer = document.getElementById("agent-card-container");
    const debugToggle = document.getElementById("debug-toggle");
    const debugPanel = document.getElementById("debug-panel");
    const statsToggle = document.getElementById("stats-toggle");
    const statsPanel = document.getElementById("stats-panel");

    let bearerToken = null;
    let contextId = null;
    const stats = {
        totalCharsReceived: 0,
        responseCount: 0,
        totalLatency: 0,
        averageLatency: 0,
    };

    messageInput.disabled = true;
    sendButton.disabled = true;

    function showSpinner(container) {
        const spinner = document.createElement("div");
        spinner.className = "message bot-message typing-indicator";
        spinner.innerHTML = "<span></span><span></span><span></span>";
        container.appendChild(spinner);
        container.scrollTop = container.scrollHeight;
    }

    function hideSpinner(container) {
        const spinner = container.querySelector(".typing-indicator");
        if (spinner) {
            spinner.remove();
        }
    }

    configHeader.addEventListener("click", () => {
        configContainer.classList.toggle("collapsed");
    });

    debugToggle.addEventListener("click", () => {
        const isHidden =
            debugPanel.style.display === "none" ||
            debugPanel.style.display === "";
        debugPanel.style.display = isHidden ? "block" : "none";
        debugToggle.textContent = isHidden ? "Hide Debug" : "Show Debug";
    });

    statsToggle.addEventListener("click", () => {
        const isHidden =
            statsPanel.style.display === "none" ||
            statsPanel.style.display === "";
        statsPanel.style.display = isHidden ? "block" : "none";
        statsToggle.textContent = isHidden ? "Hide Stats" : "Show Stats";
    });

    initializeButton.addEventListener("click", initialize);
    sendButton.addEventListener("click", sendMessage);
    messageInput.addEventListener("keypress", function (e) {
        if (e.key === "Enter") {
            sendMessage();
        }
    });

    async function getToken() {
        if (!authCheckbox.checked) {
            bearerToken = null;
            return true;
        }
        try {
            const response = await fetch("/get-token");
            if (!response.ok) {
                const errorData = await response.json();
                throw new Error(
                    `Failed to get token: ${JSON.stringify(errorData)}`
                );
            }
            const data = await response.json();
            if (data.token) {
                bearerToken = data.token;
                return true;
            } else {
                throw new Error(
                    `Token not found in response: ${JSON.stringify(data)}`
                );
            }
        } catch (error) {
            console.error("Authentication failed:", error);
            agentCardContainer.innerHTML = `Error: Automatic authentication failed. Please ensure you are logged in with gcloud and have access to the agent. Details: ${error.message}`;
            return false;
        }
    }

    async function initialize() {
        initializeButton.disabled = true;
        contextId = null; // Reset context on initialization
        showSpinner(agentCardContainer);

        let a2aEndpoint = a2aEndpointInput.value;
        if (!a2aEndpoint.startsWith("http")) {
            a2aEndpoint = "https://" + a2aEndpoint;
        }

        if (!a2aEndpoint) {
            agentCardContainer.innerHTML = "Please enter an A2A Endpoint URL.";
            hideSpinner(agentCardContainer);
            initializeButton.disabled = false;
            return;
        }

        const isAuthenticated = await getToken();
        if (!isAuthenticated) {
            hideSpinner(agentCardContainer);
            initializeButton.disabled = false;
            return;
        }

        try {
            const headers = bearerToken
                ? { Authorization: `Bearer ${bearerToken}` }
                : {};
            const response = await fetch("/", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({
                    url: a2aEndpoint,
                    headers: headers,
                    body: {},
                    method: "POST",
                }),
            });

            if (!response.ok) {
                const errorData = await response.json();
                throw new Error(
                    `HTTP error! status: ${response.status}, message: ${JSON.stringify(errorData)}`
                );
            }

            const card = await response.json();
            displayAgentCard(card);
            messageInput.disabled = false;
            sendButton.disabled = false;
            configContainer.classList.remove("collapsed");
        } catch (error) {
            console.error("Error:", error);
            agentCardContainer.innerHTML = `Error: Could not connect to the A2A endpoint. ${error.message}`;
        } finally {
            hideSpinner(agentCardContainer);
            initializeButton.disabled = false;
        }
    }

    function displayAgentCard(card) {
        agentCardContainer.innerHTML = "";
        const cardDiv = document.createElement("div");
        cardDiv.className = "agent-card";

        const header = document.createElement("div");
        header.className = "agent-card-header";
        header.innerHTML = `Agent Card <span class="chevron">▼</span>`;
        header.addEventListener("click", () => {
            cardDiv.classList.toggle("collapsed");
        });
        cardDiv.appendChild(header);

        const body = document.createElement("div");
        body.className = "agent-card-body";

        const nameDiv = document.createElement("div");
        nameDiv.className = "agent-card-name";
        nameDiv.textContent = card.name || "A2A Agent";
        body.appendChild(nameDiv);

        if (card.description) {
            const descriptionP = document.createElement("p");
            descriptionP.textContent = card.description;
            body.appendChild(descriptionP);
        }

        const capabilitiesDetails = document.createElement("div");
        capabilitiesDetails.className = "agent-card-details";
        const capabilitiesStrong = document.createElement("strong");
        capabilitiesStrong.textContent = "Capabilities:";
        capabilitiesDetails.appendChild(capabilitiesStrong);
        const capabilitiesUl = document.createElement("ul");
        for (const [key, value] of Object.entries(card.capabilities)) {
            const capabilitiesLi = document.createElement("li");
            capabilitiesLi.textContent = `${key}: ${value}`;
            capabilitiesUl.appendChild(capabilitiesLi);
        }
        capabilitiesDetails.appendChild(capabilitiesUl);
        body.appendChild(capabilitiesDetails);

        const skillsDetails = document.createElement("div");
        skillsDetails.className = "agent-card-details";
        const skillsStrong = document.createElement("strong");
        skillsStrong.textContent = "Skills:";
        skillsDetails.appendChild(skillsStrong);
        const skillsUl = document.createElement("ul");
        for (const skill of card.skills || []) {
            const skillsLi = document.createElement("li");
            const skillStrong = document.createElement("strong");
            skillStrong.textContent = `${skill.name}: `;
            skillsLi.appendChild(skillStrong);
            skillsLi.appendChild(document.createTextNode(skill.description));
            skillsUl.appendChild(skillsLi);
        }
        skillsDetails.appendChild(skillsUl);
        body.appendChild(skillsDetails);

        const collapsible = document.createElement("button");
        collapsible.className = "collapsible";
        collapsible.textContent = "View Raw JSON";
        body.appendChild(collapsible);

        const content = document.createElement("div");
        content.className = "content";
        const pre = document.createElement("pre");
        pre.textContent = JSON.stringify(card, null, 2);
        content.appendChild(pre);
        body.appendChild(content);

        collapsible.addEventListener("click", function () {
            this.classList.toggle("active");
            content.style.display =
                content.style.display === "block" ? "none" : "block";
        });

        cardDiv.appendChild(body);
        agentCardContainer.appendChild(cardDiv);
    }

    async function sendMessage() {
        configContainer.classList.add("collapsed");
        const messageText = messageInput.value;
        if (!messageText) return;

        appendMessage("user", messageText);
        messageInput.value = "";
        showSpinner(chatMessages);
        const startTime = performance.now();
        let firstChunkTime = null;

        try {
            const headers = bearerToken
                ? { Authorization: `Bearer ${bearerToken}` }
                : {};
            const payload = {
                message: { role: "user", parts: [{ text: messageText }] },
                context_id: contextId,
            };
            const a2aEndpoint = a2aEndpointInput.value.startsWith("http")
                ? a2aEndpointInput.value
                : "https://" + a2aEndpointInput.value;

            const response = await fetch("/", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({
                    url: a2aEndpoint,
                    headers: headers,
                    body: payload,
                }),
            });

            if (!response.ok) {
                const errorData = await response.json();
                throw new Error(
                    `HTTP error! status: ${response.status}, message: ${JSON.stringify(errorData)}`
                );
            }

            const reader = response.body.getReader();
            const decoder = new TextDecoder();
            let buffer = "";

            while (true) {
                const { value, done } = await reader.read();
                if (done) {
                    const endTime = performance.now();
                    stats.responseCount++;
                    stats.totalLatency += endTime - startTime;
                    stats.averageLatency =
                        stats.totalLatency / stats.responseCount;
                    updateStatsPanel(firstChunkTime, endTime - startTime);
                    break;
                }

                buffer += decoder.decode(value, { stream: true });
                const lines = buffer.split("\n");
                buffer = lines.pop();

                for (const line of lines) {
                    if (line.startsWith("data:")) {
                        const data = line.substring(5).trim();
                        if (!data) continue;
                        try {
                            const json = JSON.parse(data);
                            if (firstChunkTime === null) {
                                firstChunkTime = performance.now() - startTime;
                                hideSpinner(chatMessages);
                            }
                            if (json.contextId && !contextId) {
                                contextId = json.contextId;
                            }
                            if (
                                json.kind === "artifact-update" &&
                                json.artifact &&
                                json.artifact.parts
                            ) {
                                const textPart = json.artifact.parts.find(
                                    (p) => p.text
                                );
                                if (textPart) {
                                    stats.totalCharsReceived +=
                                        textPart.text.length;
                                    appendMessage("bot", textPart.text, true);
                                }
                            }
                            appendDebugMessage(JSON.stringify(json, null, 2));
                        } catch (e) {
                            appendDebugMessage(`Error parsing SSE: ${data}`);
                        }
                    }
                }
            }
        } catch (error) {
            appendMessage("bot", `Error: ${error.message}`);
        } finally {
            hideSpinner(chatMessages);
        }
    }

    function appendMessage(sender, text, stream = false) {
        let messageElement;
        const lastMessage = chatMessages.lastChild;
        const isStreamingBotMessage =
            stream &&
            lastMessage &&
            lastMessage.classList.contains("bot-message");

        if (isStreamingBotMessage) {
            messageElement = lastMessage;
            messageElement.innerHTML += text.replace(/\n/g, "<br>");
        } else {
            messageElement = document.createElement("div");
            messageElement.className = `message ${sender}-message`;
            messageElement.innerHTML = text.replace(/\n/g, "<br>");
            chatMessages.appendChild(messageElement);
        }
        chatMessages.scrollTop = chatMessages.scrollHeight;
    }

    function appendDebugMessage(text) {
        const pre = document.createElement("pre");
        pre.textContent = text;
        debugPanel.appendChild(pre);
        debugPanel.scrollTop = debugPanel.scrollHeight;
    }

    function updateStatsPanel(firstChunkTime, totalTime) {
        statsPanel.innerHTML = "";
        const statsContent = `
            <pre>Time to first chunk: ${firstChunkTime ? Math.round(firstChunkTime) + " ms" : "N/A"}</pre>
            <pre>Total response time: ${Math.round(totalTime)} ms</pre>
            <pre>Total characters received: ${stats.totalCharsReceived}</pre>
            <pre>Average latency: ${Math.round(stats.averageLatency)} ms</pre>
        `;
        statsPanel.innerHTML = statsContent;
    }
});
