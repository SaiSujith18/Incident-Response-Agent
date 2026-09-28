from backend.agent.incident_agent import IncidentAgent
from backend.memory.hindsight_client import close_memory


def main():

    try:
        agent = IncidentAgent()

        incident = """
        The Payment API is experiencing HTTP 504 timeout errors in production.

        Database latency is currently normal.
        Database connections are well below the configured maximum.

        Redis memory usage has reached 98%.
        Redis cache operations are timing out.

        The issue started shortly after a large increase in cached session data.
        """

        print("\nAnalyzing incident...\n")

        result = agent.analyze(incident)

        print("=" * 70)
        print("AGENT ANALYSIS")
        print("=" * 70)

        print(result["analysis"])

        print("\n")
        print("=" * 70)
        print("HISTORICAL MEMORIES USED")
        print("=" * 70)

        for memory in result["memories"]:
            print(f"- {memory}")

    finally:
        close_memory()


if __name__ == "__main__":
    main()