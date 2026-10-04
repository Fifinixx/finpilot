"""Write-side business logic for portfolio data."""

import logging

from django.db import connection, transaction
from django.db.models import IntegerField, Max
from django.db.models.functions import Cast, Substr

from .models import Goal

logger = logging.getLogger("finpilot.goals")

# Arbitrary app-wide key for pg_advisory_xact_lock; serialises goal ID allocation.
GOAL_ID_LOCK = 4_812_001


def _next_goal_id() -> str:
    """G + 5 digits, continuing after the highest existing ID (imported or created)."""
    with connection.cursor() as cursor:
        cursor.execute("SELECT pg_advisory_xact_lock(%s)", [GOAL_ID_LOCK])
    highest = (
        Goal.objects.filter(id__regex=r"^G[0-9]+$")
        .annotate(n=Cast(Substr("id", 2), IntegerField()))
        .aggregate(m=Max("n"))["m"]
    ) or 0
    return f"G{highest + 1:05d}"


@transaction.atomic
def create_goal(customer_id: str, user, **fields) -> Goal:
    goal = Goal.objects.create(id=_next_goal_id(), customer_id=customer_id, **fields)
    logger.info("goal created goal=%s customer=%s user=%s", goal.id, customer_id, user.email)
    return goal


@transaction.atomic
def update_goal(goal: Goal, user, **fields) -> Goal:
    changed = {k: v for k, v in fields.items() if getattr(goal, k) != v}
    for key, value in changed.items():
        setattr(goal, key, value)
    if changed:
        goal.save(update_fields=list(changed))
        logger.info("goal updated goal=%s customer=%s user=%s fields=%s",
                    goal.id, goal.customer_id, user.email, ",".join(sorted(changed)))
    return goal
