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
    Uses the asynchronous Hindsight API.
    """

    try:
        await client.acreate_bank(
            bank_id=HINDSIGHT_BANK_ID,
            name="MemoryOps Organizational Memory",
        )

        print(f"Created Hindsight bank: {HINDSIGHT_BANK_ID}")

    except Exception as exc:
        print(f"Hindsight bank initialization: {exc}")


# =========================================================
# RETAIN MEMORY
# =========================================================

async def retain_memory(
    content: str,
    context: str = "incident response",
):
    """
    Store organizational memory asynchronously.

    IMPORTANT:
    FastAPI is already running an event loop, so we must
    use Hindsight's aretain() instead of retain().
    """

    return await client.aretain(
        bank_id=HINDSIGHT_BANK_ID,
        content=content,
        context=context,
    )


# =========================================================
# RECALL MEMORY
# =========================================================

async def recall_memory(query: str):
    """
    Recall relevant organizational memories asynchronously.

    IMPORTANT:
    Use arecall() instead of recall() inside FastAPI.
    """

    return await client.arecall(
        bank_id=HINDSIGHT_BANK_ID,
        query=query,
    )


# =========================================================
# CLOSE MEMORY
# =========================================================

def close_memory():
    """
    Close Hindsight client.
    """

    try:
        client.close()
    except Exception as exc:
        print(f"Hindsight close warning: {exc}")