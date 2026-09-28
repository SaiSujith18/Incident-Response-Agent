from groq import Groq
import re

from backend.config.settings import (
    GROQ_API_KEY,
    GROQ_MODEL,
)

from backend.memory.hindsight_client import recall_memory


class IncidentAgent:

    def __init__(self):
        self.llm = Groq(api_key=GROQ_API_KEY)

    # =========================================================
    # HELPER — RECALL + DEDUPLICATE HISTORICAL MEMORY
    # =========================================================

    async def _get_memories(self, incident: str):

        memory_result = await recall_memory(incident)

        memories = []

        for memory in memory_result.results:

            if not memory.text:
                continue

            text = memory.text.strip()

            if text:
                memories.append(text)

        # -----------------------------------------------------
        # Remove exact duplicate memory records
        # -----------------------------------------------------

        unique_memories = list(dict.fromkeys(memories))

        return unique_memories

    # =========================================================
    # HELPER — EXTRACT INCIDENT IDS
    # =========================================================

    def _extract_incident_ids(self, memories):

        incident_ids = set()

        for memory in memories:

            matches = re.findall(
                r"\bINC[-_ ]?\d+\b",
                memory,
                flags=re.IGNORECASE,
            )

            for match in matches:

                normalized = match.upper()

                normalized = normalized.replace("_", "-")
                normalized = normalized.replace(" ", "-")

                incident_ids.add(normalized)

        return sorted(incident_ids)

    # =========================================================
    # HELPER — BUILD HISTORICAL MEMORY TEXT
    # =========================================================

    def _build_historical_memory(self, memories):

        if not memories:
            return "No relevant historical incidents found."

        return "\n\n".join(
            f"Historical Evidence {index + 1}:\n{memory}"
            for index, memory in enumerate(memories)
        )

    # =========================================================
    # ANALYZE INCIDENT
    # =========================================================

    async def analyze(self, incident: str):

        # -----------------------------------------------------
        # 1. RECALL HISTORICAL INCIDENTS
        # -----------------------------------------------------

        memories = await self._get_memories(incident)

        historical_memory = self._build_historical_memory(
            memories
        )

        # -----------------------------------------------------
        # 2. BUILD INTELLIGENCE PROMPT
        # -----------------------------------------------------

        prompt = f"""
You are MemoryOps, an AI production and security
incident-response assistant.

Your job is to investigate the CURRENT incident using
historical organizational experience stored in Hindsight.

============================================================
CURRENT INCIDENT
============================================================

{incident}

============================================================
HISTORICAL EVIDENCE
============================================================

{historical_memory}

============================================================
CORE REASONING RULES
============================================================

1. Analyze the CURRENT incident separately from historical
   evidence.

2. Historical incidents are evidence, not proof.

3. Never assume a historical root cause is the root cause
   of the current incident.

4. Do not claim an action was performed during the current
   incident unless the current incident explicitly says so.

5. Clearly distinguish:

   CURRENTLY OBSERVED
   CURRENTLY ATTEMPTED
   HISTORICALLY OBSERVED
   HISTORICALLY ATTEMPTED
   RECOMMENDED NEXT STEP

6. If an action was not mentioned as attempted during the
   current incident, describe it as "not yet tested".

7. Never convert an observation into an action.

8. Do not blindly repeat historically failed approaches.

9. Historical success does not guarantee current success.

10. Never invent evidence, outcomes, recovery times,
    resolutions, or actions.

11. Use only information contained in the current incident
    and historical evidence.

============================================================
FEATURE 1 — MULTI-INCIDENT PATTERN DETECTION
============================================================

Analyze historical incidents collectively.

Do NOT simply summarize each incident independently.

Identify recurring:

- symptoms
- indicators
- root causes
- infrastructure/components
- successful resolutions
- failed approaches

Also identify indicators that are NEW in the current incident.

If multiple historical incidents show a similar pattern,
describe the recurring organizational pattern.

A recurring pattern increases relevance but does NOT prove
that the current incident has the same root cause.

============================================================
FEATURE 2 — OUTCOME-AWARE RETRIEVAL
============================================================

Evaluate historical incidents using:

- Outcome
- Resolution
- Recovery Time
- What Worked
- What Failed

Separate historical approaches into:

SUCCESSFUL APPROACHES

FAILED APPROACHES

Identify approaches that repeatedly succeeded.

Identify approaches that repeatedly failed.

Use recovery time as supporting evidence.

Do not recommend a historically failed approach unless
current evidence provides a reason to reconsider it.

Historical success is supporting evidence only.

============================================================
FEATURE 3 — CONFIDENCE + EVIDENCE
============================================================

Use only:

High
Medium
Low

Do NOT use numerical confidence percentages.

Confidence must primarily depend on CURRENT incident
evidence.

Historical evidence supports the assessment but must not
artificially increase confidence.

Explicitly identify:

- Number of relevant historical incidents
- Current evidence
- Historical evidence
- Successful historical approaches
- Failed historical approaches
- Missing evidence
- Evidence required to confirm the hypothesis

============================================================
WHAT CHANGED SINCE HISTORICAL INCIDENTS
============================================================

Compare the current incident with relevant historical
incidents.

Identify:

- historical indicators
- current indicators
- new indicators
- missing indicators
- meaningful differences

Do not invent differences.

============================================================
RECOMMENDATION SAFETY
============================================================

The AI provides recommendations only.

It must NOT automatically execute high-impact actions.

For security-sensitive or destructive actions:

Human Approval: Required

============================================================
RESPONSE FORMAT
============================================================

1. Incident Assessment

Describe the current symptoms and evidence.

2. Multi-Incident Pattern

Describe recurring patterns across historical incidents.

3. Outcome-Aware Historical Evidence

Successful Approaches:
- ...

Failed Approaches:
- ...

Recovery Time Evidence:
- ...

4. What Changed Since Historical Incidents

Describe meaningful differences.

5. Evidence

CURRENT EVIDENCE:
- ...

HISTORICAL EVIDENCE:
- ...

6. Recommended Investigation Steps

Provide ordered investigation steps.

Prioritize actions that confirm or reject the leading
hypothesis.

7. Likely Root Cause

State the leading hypothesis.

If insufficient evidence exists, say:

"The root cause is not yet confirmed."

8. Recommendation

Provide the recommended next investigation or response.

Do not claim that the action was already performed.

9. Confidence

Level: High / Medium / Low

Explain why.

10. Human Approval

Use exactly:

Required

or

Not Required

For security-sensitive or destructive actions, use:

Required

============================================================
FINAL SAFETY RULE
============================================================

Historical memory is organizational evidence.

It is NOT proof.

The human analyst remains responsible for approving
high-impact actions.

Keep the response concise and practical.
"""

        # -----------------------------------------------------
        # 3. GROQ ANALYSIS
        # -----------------------------------------------------

        try:

            response = self.llm.chat.completions.create(
                model=GROQ_MODEL,
                messages=[
                    {
                        "role": "system",
                        "content": (
                            "You are MemoryOps, a careful production "
                            "and security incident-response assistant. "
                            "Use historical memory as supporting evidence "
                            "and never treat historical evidence as proof."
                        ),
                    },
                    {
                        "role": "user",
                        "content": prompt,
                    },
                ],
                temperature=0.2,
            )

            analysis = response.choices[0].message.content

        except Exception as exc:

            return {
                "analysis": (
                    "Incident analysis could not be completed "
                    f"because the LLM request failed: {str(exc)}"
                ),
                "memories": memories,
                "evidence_count": len(memories),
            }

        # -----------------------------------------------------
        # 4. RETURN RESULT
        # -----------------------------------------------------

        return {
            "analysis": analysis,
            "memories": memories,
            "evidence_count": len(memories),
        }

    # =========================================================
    # MULTI-INCIDENT PATTERN DETECTION
    # =========================================================

    async def detect_patterns(self, incident: str):

        # -----------------------------------------------------
        # 1. RECALL HISTORICAL INCIDENTS
        # -----------------------------------------------------

        memories = await self._get_memories(incident)

        print(
            f"[PATTERN] Unique historical memories found: "
            f"{len(memories)}"
        )

        # -----------------------------------------------------
        # 2. EXTRACT DISTINCT INCIDENT IDS
        # -----------------------------------------------------

        incident_ids = self._extract_incident_ids(
            memories
        )

        print(
            f"[PATTERN] Distinct incident IDs found: "
            f"{len(incident_ids)}"
        )

        if incident_ids:

            print(
                f"[PATTERN] Incident IDs: "
                f"{', '.join(incident_ids)}"
            )

        # -----------------------------------------------------
        # 3. NO HISTORICAL EVIDENCE
        # -----------------------------------------------------

        if not memories:

            return {
                "pattern": (
                    "No relevant historical incidents were found."
                ),
                "evidence_count": 0,
                "incident_count": 0,
                "incident_ids": [],
                "memories": [],
            }

        # -----------------------------------------------------
        # 4. BUILD HISTORICAL EVIDENCE
        # -----------------------------------------------------

        historical_memory = self._build_historical_memory(
            memories
        )

        # -----------------------------------------------------
        # 5. MULTI-INCIDENT SYNTHESIS PROMPT
        # -----------------------------------------------------

        prompt = f"""
You are MemoryOps, an AI cybersecurity and production
incident-response analyst.

Your task is to synthesize MULTIPLE historical memory records
and identify organizational patterns relevant to the CURRENT
incident.

Do NOT simply summarize every memory independently.

Instead, compare the historical evidence collectively.

============================================================
CURRENT INCIDENT
============================================================

{incident}

============================================================
HISTORICAL MEMORY
============================================================

{historical_memory}

============================================================
IMPORTANT MEMORY COUNT RULE
============================================================

The system retrieved:

Historical memory records: {len(memories)}

Distinct incident IDs identified by the application:

{incident_ids if incident_ids else "No explicit incident IDs found."}

IMPORTANT:

Multiple memory records may belong to the SAME historical
incident.

Therefore:

- Do NOT treat every memory record as a separate incident.
- Do NOT say that {len(memories)} memories means
  {len(memories)} incidents.
- If explicit incident IDs are available, use those IDs to
  discuss distinct incidents.
- If incident IDs are unavailable, say that the number of
  distinct incidents cannot be reliably determined.
- Never invent incident IDs.

============================================================
1. MULTI-INCIDENT PATTERN DETECTION
============================================================

Analyze the historical evidence collectively.

Identify recurring:

- symptoms
- indicators
- root causes
- infrastructure/components
- successful resolutions
- failed approaches
- recovery-time patterns

Do not treat duplicate memory records as separate incidents.

If multiple memories refer to the same incident ID, treat
them as evidence belonging to that same incident.

Identify the recurring organizational pattern.

Explain why the pattern is relevant to the current incident.

============================================================
2. OUTCOME-AWARE ANALYSIS
============================================================

Do NOT rely only on textual similarity.

Pay attention to:

- Outcome
- Resolution
- Recovery Time
- What Worked
- What Failed

Separate historical approaches into:

SUCCESSFUL HISTORICAL APPROACHES

FAILED HISTORICAL APPROACHES

For successful approaches:

- identify what worked
- identify the supporting incident IDs when available
- identify repeated success when supported by evidence
- mention recovery time when available

For failed approaches:

- identify what failed
- identify the supporting incident IDs when available
- explain whether the failure appears repeatedly

Never recommend a historically failed approach blindly.

Never invent:

- outcomes
- recovery times
- resolutions
- actions
- incident IDs
- success/failure information

Only use information explicitly present in the historical
memory.

============================================================
3. CURRENT INCIDENT COMPARISON
============================================================

Compare the CURRENT incident with the historical evidence.

Identify:

Historical indicators:
- ...

Current indicators:
- ...

New indicators:
- ...

Missing indicators:
- ...

Meaningful differences:
- ...

If the current incident contains insufficient information,
explicitly say:

"Insufficient current evidence to determine the exact
difference."

Do not invent differences.

============================================================
4. PATTERN-BASED SECURITY / OPERATIONAL INSIGHT
============================================================

Derive ONE important organizational insight from the
combined historical evidence.

The insight must be supported by MULTIPLE historical
memory records.

The insight should explain something useful that would be
difficult to see from a single incident.

Possible categories include:

- recurring operational weakness
- recurring failed response
- recurring successful mitigation
- repeated infrastructure bottleneck
- recurring recovery-time pattern
- missing monitoring opportunity
- missing prevention opportunity

Do not claim that the pattern proves the current root cause.

============================================================
5. PATTERN CONFIDENCE
============================================================

Use only:

High
Medium
Low

Pattern confidence represents confidence in the HISTORICAL
PATTERN.

It does NOT represent certainty about the CURRENT root cause.

Explain why the confidence level is appropriate.

Do NOT use numerical percentages.

============================================================
RESPONSE FORMAT
============================================================

Recurring Pattern:

Describe the common pattern across the historical evidence.


Common Indicators:

- ...


Common Root-Cause Pattern:

- ...


Successful Historical Approaches:

- ...


Failed Historical Approaches:

- ...


Recovery-Time Evidence:

- ...

If unavailable:

"Recovery-time evidence was not available."


Current Differences:

- ...


New Indicators:

- ...

If none:

"None identified."


Evidence:

Historical memory records retrieved: {len(memories)}

Distinct incident IDs identified:
{len(incident_ids)}

Incident IDs:
{incident_ids if incident_ids else "None explicitly identified"}

IMPORTANT:

Do not claim the historical memory count represents the
number of distinct incidents.


New Security Insight:

Provide ONE important organizational insight derived from
multiple historical memory records.


Pattern Confidence:

High / Medium / Low

Explain why.


Historical Evidence Summary:

Briefly explain which historical evidence supports the
identified pattern.

============================================================
SAFETY
============================================================

Historical similarity does NOT prove the current root cause.

Do not claim that an action was executed during the current
incident unless the CURRENT incident explicitly says so.

The AI provides investigation guidance and recommendations.

High-impact actions require human approval.

Keep the response concise and practical.
"""

        # -----------------------------------------------------
        # 6. GROQ PATTERN SYNTHESIS
        # -----------------------------------------------------

        try:

            response = self.llm.chat.completions.create(
                model=GROQ_MODEL,
                messages=[
                    {
                        "role": "system",
                        "content": (
                            "You are a careful cybersecurity analyst "
                            "specialized in multi-incident pattern "
                            "detection, outcome-aware analysis, "
                            "organizational learning, and evidence-based "
                            "incident response."
                        ),
                    },
                    {
                        "role": "user",
                        "content": prompt,
                    },
                ],
                temperature=0.2,
            )

            pattern = response.choices[0].message.content

        except Exception as exc:

            print(
                f"[PATTERN] Groq pattern synthesis failed: {exc}"
            )

            return {
                "pattern": (
                    "Pattern detection could not be completed "
                    f"because the LLM request failed: {str(exc)}"
                ),
                "evidence_count": len(memories),
                "incident_count": len(incident_ids),
                "incident_ids": incident_ids,
                "memories": memories,
            }

        # -----------------------------------------------------
        # 7. RETURN PATTERN RESULT
        # -----------------------------------------------------

        return {
            "pattern": pattern,
            "evidence_count": len(memories),
            "incident_count": len(incident_ids),
            "incident_ids": incident_ids,
            "memories": memories,
        }