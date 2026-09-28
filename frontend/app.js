const analyzeButton = document.getElementById("analyzeButton");
const incidentInput = document.getElementById("incidentInput");

const statusText = document.getElementById("status");

const results = document.getElementById("results");
const analysis = document.getElementById("analysis");
const memories = document.getElementById("memories");


analyzeButton.addEventListener("click", async () => {

    const incident = incidentInput.value.trim();

    if (!incident) {
        statusText.textContent = "Please enter an incident.";
        return;
    }

    analyzeButton.disabled = true;
    statusText.textContent = "Analyzing incident...";
    results.classList.add("hidden");

    try {

        const response = await fetch(
            "http://127.0.0.1:8000/analyze",
            {
                method: "POST",

                headers: {
                    "Content-Type": "application/json"
                },

                body: JSON.stringify({
                    incident: incident
                })
            }
        );

        if (!response.ok) {
            throw new Error(
                `Server returned ${response.status}`
            );
        }

        const data = await response.json();

        analysis.textContent = data.analysis;

        memories.innerHTML = "";

        data.memories.forEach(memory => {

            const memoryElement = document.createElement("div");

            memoryElement.className = "memory";

            memoryElement.textContent = memory;

            memories.appendChild(memoryElement);
        });

        results.classList.remove("hidden");

        statusText.textContent = "Analysis completed.";

    } catch (error) {

        console.error(error);

        statusText.textContent =
            "Failed to connect to the backend. Make sure FastAPI is running.";

    } finally {

        analyzeButton.disabled = false;
    }
});