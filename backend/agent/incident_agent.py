from groq import Groq

from backend.config.settings import (
    GROQ_API_KEY,
    GROQ_MODEL,
)

from backend.memory.hindsight_client import recall_memory


class IncidentAgent:

    def __init__(self):
        self.llm = Groq(api_key=GROQ_API_KEY)

    # =====================================================
    # ANALYZE INCIDENT
    # =====================================================

    async def analyze(self, incident: str):

        # -------------------------------------------------
        # 1. Search Hindsight for historical incidents
        # -------------------------------------------------

        memory_result = await recall_memory(incident)

        # -------------------------------------------------
        # 2. Extract historical memories
        # -------------------------------------------------

        memories = []

        if memory_result and hasattr(memory_result, "results"):

            for memory in memory_result.results:

                if hasattr(memory, "text"):
                    memories.append(memory.text)

                else:
                    memories.append(str(memory))

        historical_memory = "\n".join(
            f"- {memory}"
            for memory in memories
        )

        # -------------------------------------------------
        # 3. Build reasoning prompt
        # -------------------------------------------------

        prompt = f"""
You are MemoryOps, an AI production incident-response assistant.

Your job is to help an engineer investigate a production incident.

You have access to historical incident experiences from the organization.

IMPORTANT REASONING RULES:

1. Analyze the CURRENT incident separately from historical incidents.

2. Never assume that a previous root cause is the root cause
   of the current incident.

3. Historical incidents are supporting evidence, not proof.

4. Distinguish clearly between:
   - Observed evidence
   - Historical evidence
   - Hypothesis
   - Confirmed root cause

5. Do not state a root cause as confirmed unless the CURRENT incident
   contains direct evidence supporting it.

6. If current evidence strongly suggests a component but does not prove
   causality, describe it as a leading hypothesis.

7. Explain what additional evidence would confirm or reject the hypothesis.

8. Pay attention to previously failed approaches.

9. Do not blindly repeat a previously failed approach.

10. IMPORTANT EVIDENCE RULE:
    Never claim that an action was performed during the CURRENT incident
    unless the current incident explicitly states that it was performed.

11. Do not convert observations into actions.

12. Distinguish between:
    - CURRENTLY OBSERVED
    - CURRENTLY ATTEMPTED
    - HISTORICALLY ATTEMPTED
    - RECOMMENDED NEXT STEP

13. If an action is not mentioned as having been attempted during the
    current incident, describe it as "not yet tested".

14. Never use a numerical confidence percentage unless explicitly requested.

15. Use only:
    - High
    - Medium
    - Low

16. Confidence must reflect CURRENT evidence.

17. Do not increase confidence merely because a historical incident
    had similar symptoms.

CURRENT INCIDENT:

{incident}

HISTORICAL INCIDENT MEMORY:

{historical_memory}

Provide your response using exactly these sections:

1. Incident Assessment

Describe the symptoms and important evidence from the CURRENT incident.

2. Relevant Historical Experience

Describe historical incidents that are relevant to the current incident.
Explain why they are relevant.

3. Previously Failed Approaches

Separate approaches that failed historically from anything attempted
during the current incident.

4. Recommended Investigation Steps

Give a practical ordered list of investigation steps.

Prioritize steps that can confirm or reject the leading hypothesis.

5. Likely Root Cause

State the leading hypothesis.

If the evidence is insufficient to identify a likely root cause,
explicitly say that the root cause is not yet confirmed.

6. Confidence

Use High, Medium, or Low.

Explain why that confidence level was chosen based on CURRENT evidence.

Keep the response concise and practical for a production engineer.
"""

        # -------------------------------------------------
        # 4. Ask Groq
        # -------------------------------------------------

        response = self.llm.chat.completions.create(
            model=GROQ_MODEL,
            messages=[
                {
                    "role": "system",
                    "content": (
                        "You are a careful production "
                        "incident-response assistant."
                    ),
                },
                {
                    "role": "user",
                    "content": prompt,
                },
            ],
            temperature=0.2,
        )

        # -------------------------------------------------
        # 5. Return result
        # -------------------------------------------------

        return {
            "analysis": response.choices[0].message.content,
            "memories": memories,
        }