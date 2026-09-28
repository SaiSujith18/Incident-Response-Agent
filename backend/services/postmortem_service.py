from backend.models.postmortem import Postmortem


class PostmortemService:

    def create_postmortem(
        self,
        incident_id: str,
        root_cause: str,
        resolution: str,
        outcome: str,
        recovery_time: str | None = None,
        what_worked: str | None = None,
        what_failed: str | None = None,
    ) -> Postmortem:

        return Postmortem(
            incident_id=incident_id,
            root_cause=root_cause,
            resolution=resolution,
            outcome=outcome,
            recovery_time=recovery_time,
            what_worked=what_worked,
            what_failed=what_failed,
        )

    def format_for_memory(self, postmortem: Postmortem) -> str:

        return f"""
POSTMORTEM

Incident ID:
{postmortem.incident_id}

Root Cause:
{postmortem.root_cause}

Resolution:
{postmortem.resolution}

Outcome:
{postmortem.outcome}

Recovery Time:
{postmortem.recovery_time or "Not specified"}

What Worked:
{postmortem.what_worked or "Not specified"}

What Failed:
{postmortem.what_failed or "Not specified"}

This postmortem represents organizational learning from a resolved
production incident. It may be used as historical evidence for
future incident investigation.
""".strip()