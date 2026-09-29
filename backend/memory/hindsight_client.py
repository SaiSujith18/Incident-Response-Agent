from hindsight_client import Hindsight

from backend.config.settings import (
    HINDSIGHT_BASE_URL,
    HINDSIGHT_API_KEY,
    HINDSIGHT_BANK_ID,
)


# =========================================================
# HINDSIGHT CLIENT
# =========================================================

client = Hindsight(
    base_url=HINDSIGHT_BASE_URL,
    api_key=HINDSIGHT_API_KEY,
)


# =========================================================
# INITIALIZE MEMORY
# =========================================================

async def initialize_memory_async():
    """
    Create the Hindsight organizational memory bank.

    Safe to call during FastAPI startup.
    If the bank already exists, the exception is ignored.
    """

    try:
        await client.acreate_bank(
            bank_id=HINDSIGHT_BANK_ID,
            name="MemoryOps Organizational Memory",
        )

        print(
            f"[HINDSIGHT] Created memory bank: "
            f"{HINDSIGHT_BANK_ID}"
        )

    except Exception as exc:

        print(
            f"[HINDSIGHT] Bank initialization: {exc}"
        )


# =========================================================
# RETAIN MEMORY
# =========================================================

async def retain_memory(
    content: str,
    context: str = "incident response",
):
    """
    Store organizational incident memory.

    Memory should preferably contain:
        - incident type
        - symptoms
        - indicators
        - affected component
        - root cause
        - actions attempted
        - successful actions
        - failed actions
        - recovery time
        - final outcome
        - lessons learned

    Example:

        Incident Type: Suspicious Login
        Symptoms: Login from unusual IP
        Indicators: Unknown device, foreign IP
        Root Cause: Compromised credentials
        Successful Action: Password reset + MFA enforcement
        Failed Action: None
        Recovery Time: 20 minutes
        Outcome: Account secured
        Lesson: Enforce MFA for privileged accounts
    """

    if not content or not content.strip():
        raise ValueError(
            "Cannot store empty organizational memory."
        )

    content = content.strip()

    return await client.aretain(
        bank_id=HINDSIGHT_BANK_ID,
        content=content,
        context=context,
    )


# =========================================================
# BUILD DYNAMIC RECALL QUERY
# =========================================================

def build_recall_query(
    incident: str,
) -> str:
    """
    Build a dynamic semantic retrieval query.

    The query is generated from the CURRENT incident.

    It does not assume:
        - database incident
        - login incident
        - API incident
        - deployment incident
        - security incident

    Hindsight is asked to retrieve historical memories that
    are semantically relevant to the current incident.

    The current incident remains separate from historical
    evidence.
    """

    if not incident or not incident.strip():
        raise ValueError(
            "Incident description cannot be empty."
        )

    incident = incident.strip()

    return f"""
CURRENT INCIDENT:

{incident}


TASK:

Retrieve historical organizational memories that are
directly relevant to investigating this CURRENT incident.


RELEVANCE PRIORITY:

1. Same incident type or closely related incident type.

2. Same affected system, service, component, account,
   infrastructure, or resource.

3. Similar symptoms or failure conditions.

4. Similar security indicators or operational indicators.

5. Similar root-cause conditions.

6. Previous incidents involving the same type of event.

7. Previously successful investigation or remediation
   approaches.

8. Previously failed investigation or remediation
   approaches.

9. Relevant recovery-time information.

10. Relevant lessons learned or prevention measures.


IMPORTANT:

Prefer semantic relevance over generic word matching.

Do NOT retrieve memories merely because they contain
generic words such as:

- incident
- issue
- error
- system
- production
- failure
- resolved
- problem


For example:

If the current incident concerns a suspicious login,
prefer memories concerning:

- suspicious logins
- failed authentication
- account compromise
- credential compromise
- unauthorized access
- MFA
- authentication anomalies
- unusual login locations
- unusual login devices

Do NOT return unrelated database connection-pool incidents
just because they contain words such as "incident",
"failure", or "resolved".


If the current incident concerns database connection-pool
exhaustion, prefer memories concerning:

- connection pools
- database exhaustion
- database connections
- long-running queries
- connection limits
- database performance
- similar database incidents


Historical memories are supporting evidence only.

Do not treat historical memories as proof of the current
root cause.

Return the most relevant historical organizational
experience for the current incident.
""".strip()


# =========================================================
# RECALL MEMORY
# =========================================================

async def recall_memory(
    incident: str,
):
    """
    Retrieve historical organizational memory relevant to
    the CURRENT incident.

    This function is dynamic and works across different
    incident types.

    Example:

        First incident:
            Suspicious login

        -> No previous suspicious-login memory
        -> Returns little/no relevant history


        After that incident is resolved and retained:

        Second suspicious login

        -> Hindsight can retrieve the previous
           suspicious-login incident
        -> Previous investigation/resolution becomes
           historical evidence


        Database incident

        -> Database-related history is retrieved
        -> Suspicious-login history should not be treated
           as relevant
    """

    if not incident or not incident.strip():
        raise ValueError(
            "Incident description cannot be empty."
        )

    query = build_recall_query(
        incident
    )

    print()
    print("=" * 70)
    print("[HINDSIGHT] DYNAMIC MEMORY RECALL")
    print("=" * 70)

    print(
        "[HINDSIGHT] Current incident:"
    )

    print(
        incident
    )

    print("-" * 70)

    print(
        "[HINDSIGHT] Retrieval query:"
    )

    print(
        query
    )

    print("=" * 70)

    try:

        result = await client.arecall(
            bank_id=HINDSIGHT_BANK_ID,
            query=query,
        )

    except Exception as exc:

        print(
            "[HINDSIGHT] Recall failed:"
        )

        print(
            str(exc)
        )

        raise

    # -----------------------------------------------------
    # Retrieval count
    # -----------------------------------------------------

    try:

        count = len(
            result.results
        )

        print(
            f"[HINDSIGHT] Raw memories retrieved: "
            f"{count}"
        )

    except Exception:

        print(
            "[HINDSIGHT] Memory retrieval completed."
        )

    print("=" * 70)
    print()

    return result


# =========================================================
# RECALL RELEVANT MEMORY TEXT
# =========================================================

async def recall_relevant_memories(
    incident: str,
):
    """
    Return only usable historical memory text.

    Removes:
        - empty records
        - whitespace
        - exact duplicates

    Does not invent or modify historical evidence.
    """

    result = await recall_memory(
        incident
    )

    memories = []

    for memory in getattr(
        result,
        "results",
        [],
    ):

        text = getattr(
            memory,
            "text",
            None,
        )

        if not text:
            continue

        text = text.strip()

        if not text:
            continue

        memories.append(
            text
        )

    # -----------------------------------------------------
    # Remove exact duplicates
    # -----------------------------------------------------

    unique_memories = list(
        dict.fromkeys(
            memories
        )
    )

    print(
        "[HINDSIGHT] Unique relevant memories: "
        f"{len(unique_memories)}"
    )

    return unique_memories


# =========================================================
# BUILD STRUCTURED INCIDENT MEMORY
# =========================================================

def build_incident_memory(
    incident: str,
    root_cause: str = "",
    successful_actions=None,
    failed_actions=None,
    recovery_time: str = "",
    outcome: str = "",
    lessons_learned: str = "",
):
    """
    Build a structured memory before storing an incident.

    This makes future Hindsight retrieval much more useful.

    IMPORTANT:

    Only provide facts that are actually known.

    Do not fabricate root causes, outcomes, recovery times,
    or actions.
    """

    if not incident or not incident.strip():
        raise ValueError(
            "Incident description cannot be empty."
        )

    if successful_actions is None:
        successful_actions = []

    if failed_actions is None:
        failed_actions = []

    successful_text = (
        "\n".join(
            f"- {action}"
            for action in successful_actions
            if action and action.strip()
        )
        or "None documented."
    )

    failed_text = (
        "\n".join(
            f"- {action}"
            for action in failed_actions
            if action and action.strip()
        )
        or "None documented."
    )

    memory = f"""
INCIDENT MEMORY

Incident:
{incident.strip()}

Root Cause:
{root_cause.strip() if root_cause else "Not confirmed."}

Successful Actions:
{successful_text}

Failed Actions:
{failed_text}

Recovery Time:
{recovery_time.strip() if recovery_time else "Not documented."}

Outcome:
{outcome.strip() if outcome else "Not documented."}

Lessons Learned:
{lessons_learned.strip() if lessons_learned else "Not documented."}
""".strip()

    return memory


# =========================================================
# RETAIN COMPLETED INCIDENT
# =========================================================

async def retain_incident_memory(
    incident: str,
    root_cause: str = "",
    successful_actions=None,
    failed_actions=None,
    recovery_time: str = "",
    outcome: str = "",
    lessons_learned: str = "",
):
    """
    Store a completed incident in structured form.

    This should normally be called AFTER the incident has
    enough information to provide useful historical learning.

    Example:

        First suspicious login:
            Analyze
            Investigate
            Resolve
            Then retain the final outcome

        Second suspicious login:
            Recall the first incident
            Compare evidence
            Learn from previous outcome
    """

    memory = build_incident_memory(
        incident=incident,
        root_cause=root_cause,
        successful_actions=successful_actions,
        failed_actions=failed_actions,
        recovery_time=recovery_time,
        outcome=outcome,
        lessons_learned=lessons_learned,
    )

    return await retain_memory(
        content=memory,
        context="completed incident response",
    )


# =========================================================
# CLOSE MEMORY
# =========================================================

def close_memory():
    """
    Close the Hindsight client safely.
    """

    try:

        client.close()

        print(
            "[HINDSIGHT] Client closed successfully."
        )

    except Exception as exc:

        print(
            f"[HINDSIGHT] Close warning: {exc}"
        )