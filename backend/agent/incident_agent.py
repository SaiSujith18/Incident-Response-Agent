from groq import Groq
import re

from backend.config.settings import (
    GROQ_API_KEY,
    GROQ_MODEL,
)

from backend.memory.hindsight_client import (
    recall_memory,
    retain_memory,
)


class IncidentAgent:

    def __init__(self):
        self.llm = Groq(
            api_key=GROQ_API_KEY
        )

        # Maximum number of relevant memories
        # sent to Groq.
        self.max_memories = 15

        # Minimum local relevance score.
        #
        # Hindsight performs semantic retrieval first.
        # This local filter removes obviously unrelated
        # memories without being too aggressive.
        self.relevance_threshold = 0.12

    # =========================================================
    # TEXT NORMALIZATION
    # =========================================================

    def _normalize_text(
        self,
        text: str,
    ):

        if not text:
            return ""

        text = text.lower().strip()

        text = re.sub(
            r"[^a-z0-9\s_-]",
            " ",
            text,
        )

        text = re.sub(
            r"\s+",
            " ",
            text,
        )

        return text

    # =========================================================
    # TOKEN EXTRACTION
    # =========================================================

    def _extract_terms(
        self,
        text: str,
    ):

        normalized = self._normalize_text(
            text
        )

        stop_words = {
            "the",
            "a",
            "an",
            "is",
            "are",
            "was",
            "were",
            "be",
            "been",
            "being",
            "has",
            "have",
            "had",
            "this",
            "that",
            "these",
            "those",
            "and",
            "or",
            "but",
            "because",
            "due",
            "to",
            "of",
            "in",
            "on",
            "for",
            "with",
            "from",
            "by",
            "as",
            "at",
            "into",
            "during",
            "after",
            "before",
            "current",
            "incident",
            "production",
            "system",
            "issue",
            "problem",
            "error",
            "event",
            "reported",
            "occurred",
            "occur",
            "there",
            "their",
            "they",
            "it",
            "its",
            "not",
            "no",
            "only",
            "also",
            "very",
            "some",
            "more",
            "than",
        }

        words = re.findall(
            r"[a-z0-9_-]+",
            normalized,
        )

        return {
            word
            for word in words
            if len(word) >= 3
            and word not in stop_words
        }

    # =========================================================
    # INCIDENT CATEGORY DETECTION
    # =========================================================

    def _detect_categories(
        self,
        text: str,
    ):

        normalized = self._normalize_text(
            text
        )

        categories = {

            "authentication": [
                "login",
                "authentication",
                "credential",
                "password",
                "mfa",
                "account compromise",
                "unauthorized access",
                "suspicious login",
                "failed login",
                "account",
            ],

            "database": [
                "database",
                "db",
                "sql",
                "query",
                "connection pool",
                "pool exhaustion",
                "long-running query",
                "stale connection",
            ],

            "network": [
                "network",
                "dns",
                "latency",
                "packet",
                "firewall",
                "connectivity",
                "timeout",
            ],

            "availability": [
                "service unavailable",
                "downtime",
                "outage",
                "unavailable",
                "service failure",
            ],

            "infrastructure": [
                "server",
                "cpu",
                "memory",
                "disk",
                "storage",
                "resource exhaustion",
            ],

            "malware": [
                "malware",
                "ransomware",
                "trojan",
                "virus",
                "payload",
                "infection",
            ],

            "api": [
                "api",
                "endpoint",
                "request",
                "response",
                "http",
                "rest",
            ],

        }

        detected = set()

        for category, keywords in categories.items():

            for keyword in keywords:

                if keyword in normalized:

                    detected.add(
                        category
                    )

                    break

        return detected

    # =========================================================
    # RELEVANCE SCORE
    # =========================================================

    def _calculate_relevance(
        self,
        incident: str,
        memory: str,
    ):

        incident_terms = (
            self._extract_terms(
                incident
            )
        )

        memory_terms = (
            self._extract_terms(
                memory
            )
        )

        if (
            not incident_terms
            or not memory_terms
        ):
            return 0.0

        # -----------------------------------------------------
        # Lexical similarity
        # -----------------------------------------------------

        common_terms = (
            incident_terms
            & memory_terms
        )

        lexical_score = (
            len(common_terms)
            / max(
                len(incident_terms),
                1,
            )
        )

        # -----------------------------------------------------
        # Category similarity
        # -----------------------------------------------------

        incident_categories = (
            self._detect_categories(
                incident
            )
        )

        memory_categories = (
            self._detect_categories(
                memory
            )
        )

        category_score = 0.0

        if (
            incident_categories
            and memory_categories
        ):

            common_categories = (
                incident_categories
                & memory_categories
            )

            if common_categories:

                category_score = (
                    len(common_categories)
                    / max(
                        len(incident_categories),
                        1,
                    )
                )

        # -----------------------------------------------------
        # Important phrase similarity
        # -----------------------------------------------------

        incident_normalized = (
            self._normalize_text(
                incident
            )
        )

        memory_normalized = (
            self._normalize_text(
                memory
            )
        )

        phrase_score = 0.0

        important_phrases = [

            "connection pool",
            "pool exhaustion",
            "database connection",
            "long-running query",

            "suspicious login",
            "failed login",
            "authentication",
            "credential",
            "account compromise",
            "unauthorized access",
            "password",
            "mfa",

            "malware",
            "ransomware",

            "api failure",
            "service unavailable",

            "memory exhaustion",
            "cpu exhaustion",
            "disk full",
            "network failure",

        ]

        for phrase in important_phrases:

            if (
                phrase in incident_normalized
                and phrase in memory_normalized
            ):

                phrase_score += 0.15

        phrase_score = min(
            phrase_score,
            0.45,
        )

        # -----------------------------------------------------
        # Final relevance
        # -----------------------------------------------------

        score = (
            lexical_score * 0.40
            + category_score * 0.40
            + phrase_score * 0.20
        )

        return min(
            score,
            1.0,
        )

    # =========================================================
    # RECALL + DEDUPLICATE + FILTER
    # =========================================================

    async def _get_memories(
        self,
        incident: str,
    ):

        try:

            memory_result = (
                await recall_memory(
                    incident
                )
            )

        except Exception as exc:

            print(
                f"[MEMORY] Hindsight recall failed: "
                f"{exc}"
            )

            return []

        if not memory_result:
            return []

        results = getattr(
            memory_result,
            "results",
            [],
        )

        memories = []

        # -----------------------------------------------------
        # Extract memory text
        # -----------------------------------------------------

        for memory in results:

            text = getattr(
                memory,
                "text",
                None,
            )

            if not text:
                continue

            text = text.strip()

            if text:

                memories.append(
                    text
                )

        # -----------------------------------------------------
        # Exact deduplication
        # -----------------------------------------------------

        unique_memories = list(
            dict.fromkeys(
                memories
            )
        )

        if not unique_memories:

            print(
                "[MEMORY] No memories returned."
            )

            return []

        # -----------------------------------------------------
        # Score memories
        # -----------------------------------------------------

        scored_memories = []

        for memory in unique_memories:

            score = (
                self._calculate_relevance(
                    incident,
                    memory,
                )
            )

            scored_memories.append(
                (
                    score,
                    memory,
                )
            )

        # -----------------------------------------------------
        # Sort highest relevance first
        # -----------------------------------------------------

        scored_memories.sort(
            key=lambda item: item[0],
            reverse=True,
        )

        # -----------------------------------------------------
        # Filter relevant memories
        # -----------------------------------------------------

        relevant_memories = [

            memory

            for score, memory
            in scored_memories

            if score >= self.relevance_threshold

        ]

        relevant_memories = (
            relevant_memories[
                : self.max_memories
            ]
        )

        # -----------------------------------------------------
        # Logging
        # -----------------------------------------------------

        print(
            f"[MEMORY] Hindsight returned: "
            f"{len(unique_memories)}"
        )

        print(
            f"[MEMORY] Relevant memories: "
            f"{len(relevant_memories)}"
        )

        for score, memory in (
            scored_memories[:10]
        ):

            print(
                f"[MEMORY] score={score:.3f} "
                f"{memory[:150]}"
            )

        return relevant_memories

    # =========================================================
    # EXTRACT INCIDENT IDS
    # =========================================================

    def _extract_incident_ids(
        self,
        memories,
    ):

        incident_ids = set()

        for memory in memories:

            matches = re.findall(
                r"\bINC[-_ ]?\d+\b",
                memory,
                flags=re.IGNORECASE,
            )

            for match in matches:

                normalized = (
                    match.upper()
                )

                normalized = (
                    normalized.replace(
                        "_",
                        "-",
                    )
                )

                normalized = (
                    normalized.replace(
                        " ",
                        "-",
                    )
                )

                incident_ids.add(
                    normalized
                )

        return sorted(
            incident_ids
        )

    # =========================================================
    # BUILD HISTORICAL MEMORY
    # =========================================================

    def _build_historical_memory(
        self,
        memories,
    ):

        if not memories:

            return (
                "NO RELEVANT HISTORICAL "
                "EVIDENCE WAS FOUND."
            )

        return "\n\n".join(

            f"Historical Evidence "
            f"{index + 1}:\n{memory}"

            for index, memory
            in enumerate(memories)

        )

    # =========================================================
    # BUILD MEMORY FOR FUTURE LEARNING
    # =========================================================

    def _build_learning_memory(
        self,
        incident: str,
        analysis: str,
    ):
        """
        Convert the current investigation result into a
        structured organizational memory.

        This is the critical part that allows:

        Incident #1
            ↓
        Analysis
            ↓
        Hindsight retain
            ↓
        Incident #2
            ↓
        Historical match
            ↓
        Learning
        """

        return f"""
MEMORYOPS HISTORICAL INCIDENT RECORD

CURRENT INCIDENT:
{incident.strip()}

INCIDENT ANALYSIS:
{analysis.strip()}

IMPORTANT:
This record represents a previous incident investigation.

It is historical organizational evidence.

It must NOT be treated as proof of the root cause of
future incidents.

Future investigations should compare new incidents against
this record and determine whether the symptoms, indicators,
components, causes, approaches, outcomes, and resolutions
are actually similar.

END HISTORICAL INCIDENT RECORD
""".strip()

    # =========================================================
    # RETAIN ANALYSIS INTO HINDSIGHT
    # =========================================================

    async def _retain_analysis(
        self,
        incident: str,
        analysis: str,
    ):
        """
        Store the completed investigation in Hindsight.

        This enables the system to learn from previous
        incidents.
        """

        try:

            memory_content = (
                self._build_learning_memory(
                    incident,
                    analysis,
                )
            )

            await retain_memory(
                content=memory_content,
                context=(
                    "MemoryOps incident "
                    "investigation and "
                    "organizational learning"
                ),
            )

            print(
                "[MEMORY] Incident analysis "
                "stored in Hindsight."
            )

            return True

        except Exception as exc:

            print(
                f"[MEMORY] Failed to retain "
                f"incident analysis: {exc}"
            )

            return False

    # =========================================================
    # ANALYZE INCIDENT
    # =========================================================

    async def analyze(
        self,
        incident: str,
    ):

        incident = (
            incident.strip()
            if incident
            else ""
        )

        if not incident:

            return {
                "analysis": (
                    "Please provide an incident "
                    "description."
                ),
                "memories": [],
                "evidence_count": 0,
                "incident_count": 0,
                "incident_ids": [],
                "memory_retained": False,
            }

        # -----------------------------------------------------
        # 1. RECALL PREVIOUS INCIDENTS
        # -----------------------------------------------------

        memories = (
            await self._get_memories(
                incident
            )
        )

        incident_ids = (
            self._extract_incident_ids(
                memories
            )
        )

        print()
        print("=" * 60)
        print("[ANALYZE] INCIDENT ANALYSIS")
        print("=" * 60)

        print(
            f"[ANALYZE] Relevant historical memories: "
            f"{len(memories)}"
        )

        print(
            f"[ANALYZE] Historical incident IDs: "
            f"{len(incident_ids)}"
        )

        # -----------------------------------------------------
        # 2. BUILD HISTORICAL CONTEXT
        # -----------------------------------------------------

        historical_memory = (
            self._build_historical_memory(
                memories
            )
        )

        # -----------------------------------------------------
        # 3. GROQ PROMPT
        # -----------------------------------------------------

        prompt = f"""
You are MemoryOps, an evidence-based production and
cybersecurity incident-response assistant.

Your job is to investigate the CURRENT INCIDENT and learn
from RELEVANT HISTORICAL INCIDENTS.

============================================================
CURRENT INCIDENT
============================================================

{incident}

============================================================
HISTORICAL MEMORY MATCHES
============================================================

{historical_memory}

============================================================
IMPORTANT LEARNING BEHAVIOR
============================================================

This may be:

A FIRST OCCURRENCE

or

A REPEATED / SIMILAR OCCURRENCE.

If no relevant historical evidence exists:

Clearly state:

"No relevant historical pattern was found."

This means the incident is currently being analyzed without
relevant prior organizational evidence.

If relevant historical evidence exists:

DO NOT simply say that history exists.

Instead:

1. Identify what the previous incident experienced.
2. Identify its observed indicators.
3. Identify its affected component.
4. Identify its root cause if explicitly documented.
5. Identify what investigation was performed.
6. Identify what worked.
7. Identify what failed.
8. Identify the documented resolution.
9. Identify recovery time if explicitly documented.
10. Compare those facts with the CURRENT incident.
11. Explain what is similar.
12. Explain what is different.
13. Use previous learning to improve the current investigation.

Historical evidence is supporting evidence only.

Historical evidence is NOT proof.

============================================================
STRICT ANTI-HALLUCINATION RULE
============================================================

Use ONLY:

CURRENT INCIDENT

and

HISTORICAL MEMORY MATCHES

Never invent:

- IP addresses
- usernames
- timestamps
- devices
- locations
- authentication methods
- MFA status
- failed attempts
- actions
- resolutions
- recovery times
- outcomes
- incident IDs
- root causes

If information is missing:

Use:

"Not provided"

or

"Unknown"

Never turn missing information into an observation.

============================================================
CURRENT INCIDENT
============================================================

Analyze the current incident independently first.

Identify:

- observed symptoms
- indicators
- affected component
- attempted actions
- missing information

============================================================
HISTORICAL MEMORY MATCHES
============================================================

If history exists, explicitly explain:

Previous Incident Evidence

Previous Root Cause

Previous Investigation

Previous Successful Approach

Previous Failed Approach

Previous Resolution

Previous Recovery Time

Only include information explicitly present in memory.

============================================================
LEARNING FROM PREVIOUS INCIDENTS
============================================================

If a previous incident is similar:

Explain:

"Based on the historical incident..."

Then identify which previous investigation steps may be
useful to test again.

Do NOT claim they already worked in the CURRENT incident.

Use:

"Not yet tested"

when the current incident does not say that an action was
performed.

============================================================
WHAT CHANGED
============================================================

Compare:

Historical indicators

Current indicators

Common indicators

New indicators

Missing historical indicators

Meaningful differences

Do not invent differences.

============================================================
ROOT CAUSE
============================================================

If current evidence is insufficient:

"The root cause is not yet confirmed."

If historical evidence contains a root cause:

Describe it as historical.

For example:

"Historical incident INC-001 had a documented root cause
of X. The current incident has not yet confirmed whether
the same cause applies."

============================================================
RECOMMENDATIONS
============================================================

Recommendations must primarily address the CURRENT incident.

Historical successful approaches may be recommended as
investigation steps when the current evidence is compatible.

Historical failed approaches should NOT be blindly repeated.

High-impact actions require human approval.

============================================================
CONFIDENCE
============================================================

Use only:

High

Medium

Low

Confidence refers to the CURRENT incident assessment.

Historical evidence alone must not create high confidence.

============================================================
RESPONSE FORMAT
============================================================

1. Incident Assessment

CURRENTLY OBSERVED:
- ...

CURRENTLY ATTEMPTED:
- ...

MISSING INFORMATION:
- ...

2. Historical Memory Matches

If history exists:

- Historical incident:
- Similarity:
- Historical evidence:
- Historical root cause:
- Historical resolution:

If none:

No relevant historical pattern was found.

3. What We Learned From Previous Incidents

If historical evidence exists:

- What worked:
- What failed:
- Recovery-time evidence:
- Useful investigation lesson:

If none:

No previous organizational learning is available.

4. Current vs Historical Comparison

Common Indicators:
- ...

New Indicators:
- ...

Missing Indicators:
- ...

Meaningful Differences:
- ...

5. Recommended Investigation Steps

Maximum 5 steps.

Prioritize steps that can confirm or reject the historical
hypothesis.

Clearly mark historical actions as:

"Not yet tested"

unless the CURRENT incident explicitly says they were done.

6. Likely Root Cause

If insufficient current evidence:

"The root cause is not yet confirmed."

7. Recommendation

Provide ONE primary recommendation.

8. Confidence

Level: High / Medium / Low

Brief explanation.

9. Human Approval

Use exactly:

Required

or

Not Required

High-impact or destructive actions:

Required

============================================================
FINAL SAFETY RULE
============================================================

Historical memory helps the organization learn.

Historical memory is not proof.

Do not invent evidence.

Do not claim historical actions happened in the current
incident.

Do not convert historical root causes into current root
causes without current evidence.

Keep the answer concise and practical.
"""

        # -----------------------------------------------------
        # 4. CALL GROQ
        # -----------------------------------------------------

        try:

            response = (
                self.llm.chat.completions.create(
                    model=GROQ_MODEL,

                    messages=[
                        {
                            "role": "system",
                            "content": (
                                "You are MemoryOps, a strict "
                                "evidence-based incident "
                                "response analyst. "
                                "Learn from relevant "
                                "historical memory without "
                                "treating history as proof."
                            ),
                        },
                        {
                            "role": "user",
                            "content": prompt,
                        },
                    ],

                    temperature=0.0,
                )
            )

            analysis = (
                response
                .choices[0]
                .message
                .content
            )

        except Exception as exc:

            print(
                f"[ANALYZE] Groq failed: {exc}"
            )

            return {
                "analysis": (
                    "Incident analysis could not be "
                    "completed because the LLM request "
                    f"failed: {str(exc)}"
                ),
                "memories": memories,
                "evidence_count": len(
                    memories
                ),
                "incident_count": len(
                    incident_ids
                ),
                "incident_ids": incident_ids,
                "memory_retained": False,
            }

        # -----------------------------------------------------
        # 5. IMPORTANT:
        # RETAIN THIS INCIDENT AFTER ANALYSIS
        # -----------------------------------------------------

        memory_retained = (
            await self._retain_analysis(
                incident=incident,
                analysis=analysis,
            )
        )

        # -----------------------------------------------------
        # 6. RETURN
        # -----------------------------------------------------

        print(
            f"[ANALYZE] Memory retained: "
            f"{memory_retained}"
        )

        print("=" * 60)
        print()

        return {
            "analysis": analysis,
            "memories": memories,
            "evidence_count": len(
                memories
            ),
            "incident_count": len(
                incident_ids
            ),
            "incident_ids": incident_ids,
            "memory_retained": (
                memory_retained
            ),
        }

    # =========================================================
    # MULTI-INCIDENT PATTERN DETECTION
    # =========================================================

    async def detect_patterns(
        self,
        incident: str,
    ):

        incident = (
            incident.strip()
            if incident
            else ""
        )

        if not incident:

            return {
                "pattern": (
                    "Please provide an incident "
                    "description."
                ),
                "evidence_count": 0,
                "incident_count": 0,
                "incident_ids": [],
                "memories": [],
            }

        # -----------------------------------------------------
        # 1. RECALL
        # -----------------------------------------------------

        memories = (
            await self._get_memories(
                incident
            )
        )

        incident_ids = (
            self._extract_incident_ids(
                memories
            )
        )

        print()
        print("=" * 60)
        print("[PATTERN] MULTI-INCIDENT PATTERN DETECTION")
        print("=" * 60)

        print(
            f"[PATTERN] Relevant memories: "
            f"{len(memories)}"
        )

        print(
            f"[PATTERN] Distinct incidents: "
            f"{len(incident_ids)}"
        )

        # -----------------------------------------------------
        # 2. NO HISTORY
        # -----------------------------------------------------

        if not memories:

            return {
                "pattern": (
                    "No relevant historical pattern "
                    "was found for this incident."
                ),
                "evidence_count": 0,
                "incident_count": 0,
                "incident_ids": [],
                "memories": [],
            }

        # -----------------------------------------------------
        # 3. SINGLE HISTORICAL INCIDENT
        # -----------------------------------------------------

        if len(incident_ids) < 2:

            return {
                "pattern": (
                    "Relevant historical evidence exists, "
                    "but there are not enough distinct "
                    "historical incidents to establish a "
                    "multi-incident organizational pattern."
                ),
                "evidence_count": len(
                    memories
                ),
                "incident_count": len(
                    incident_ids
                ),
                "incident_ids": incident_ids,
                "memories": memories,
            }

        # -----------------------------------------------------
        # 4. BUILD HISTORY
        # -----------------------------------------------------

        historical_memory = (
            self._build_historical_memory(
                memories
            )
        )

        # -----------------------------------------------------
        # 5. PATTERN PROMPT
        # -----------------------------------------------------

        prompt = f"""
You are MemoryOps, an evidence-based organizational
incident-pattern analyst.

Identify recurring patterns only when supported by MULTIPLE
relevant historical incidents.

============================================================
CURRENT INCIDENT
============================================================

{incident}

============================================================
HISTORICAL MEMORY MATCHES
============================================================

{historical_memory}

============================================================
HISTORICAL METADATA
============================================================

Memory records:
{len(memories)}

Distinct incident IDs:
{len(incident_ids)}

Incident IDs:
{incident_ids}

============================================================
STRICT RULES
============================================================

A memory record is not necessarily an incident.

Multiple records can belong to the same incident.

Use explicit incident IDs.

Never invent incident IDs.

Never invent incidents.

Only identify patterns supported by multiple relevant
historical incidents.

If no recurring pattern is supported:

"No relevant historical pattern was found."

============================================================
ANALYZE
============================================================

Identify recurring:

- symptoms
- indicators
- affected components
- root causes
- successful approaches
- failed approaches
- resolutions
- recovery-time patterns

============================================================
CURRENT COMPARISON
============================================================

Compare the CURRENT incident with the historical pattern.

Identify:

Common indicators

New indicators

Missing indicators

Meaningful differences

Do not invent differences.

============================================================
ORGANIZATIONAL LEARNING
============================================================

Provide ONE useful organizational insight supported by
multiple historical incidents.

Do not claim the pattern proves the current root cause.

============================================================
RESPONSE FORMAT
============================================================

Recurring Pattern:

...


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


Current Differences:

- ...


New Indicators:

- ...


Evidence:

Historical memory records retrieved:
{len(memories)}

Distinct incident IDs:
{len(incident_ids)}

Incident IDs:
{incident_ids}


New Security / Operational Insight:

Provide ONE evidence-supported insight.


Pattern Confidence:

High / Medium / Low

Explain briefly.


Historical Evidence Summary:

Briefly identify the historical evidence supporting
the pattern.

============================================================
FINAL RULE
============================================================

Only relevant evidence.

No speculation.

No invented facts.

No forced patterns.

Keep the response concise.
"""

        # -----------------------------------------------------
        # 6. GROQ
        # -----------------------------------------------------

        try:

            response = (
                self.llm.chat.completions.create(
                    model=GROQ_MODEL,

                    messages=[
                        {
                            "role": "system",
                            "content": (
                                "You are a strict "
                                "evidence-based organizational "
                                "incident-pattern analyst. "
                                "Identify patterns only when "
                                "multiple relevant historical "
                                "incidents support them."
                            ),
                        },
                        {
                            "role": "user",
                            "content": prompt,
                        },
                    ],

                    temperature=0.0,
                )
            )

            pattern = (
                response
                .choices[0]
                .message
                .content
            )

        except Exception as exc:

            print(
                f"[PATTERN] Groq failed: {exc}"
            )

            return {
                "pattern": (
                    "Pattern detection could not be "
                    "completed because the LLM request "
                    f"failed: {str(exc)}"
                ),
                "evidence_count": len(
                    memories
                ),
                "incident_count": len(
                    incident_ids
                ),
                "incident_ids": incident_ids,
                "memories": memories,
            }

        # -----------------------------------------------------
        # 7. RETURN
        # -----------------------------------------------------

        print(
            "[PATTERN] Pattern detection completed."
        )

        print(
            f"[PATTERN] Relevant evidence: "
            f"{len(memories)}"
        )

        print(
            f"[PATTERN] Distinct incidents: "
            f"{len(incident_ids)}"
        )

        print("=" * 60)
        print()

        return {
            "pattern": pattern,
            "evidence_count": len(
                memories
            ),
            "incident_count": len(
                incident_ids
            ),
            "incident_ids": incident_ids,
            "memories": memories,
        }