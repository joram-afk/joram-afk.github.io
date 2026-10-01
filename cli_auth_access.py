from __future__ import annotations

import click

from auth import get_user_by_id, register_user, login_user
from auth_access import grant_mpesa_access, revoke_mpesa_access, validate_mpesa_access


@click.group()
def auth() -> None:
    """Authentication and access management."""
    pass


@auth.command()
@click.option("--user-id", type=int, required=True, help="User ID")
@click.option("--max-amount", type=int, required=True, help="Maximum amount per transaction")
@click.option("--daily-max", type=int, required=True, help="Maximum amount per day")
@click.option("--days", type=int, default=30, help="Access validity in days")
def grant_access(user_id: int, max_amount: int, daily_max: int, days: int) -> None:
    """Grant M-Pesa access token to the AI agent within configured limits."""
    user = get_user_by_id(user_id)
    if user is None:
        click.echo("❌ User not found", err=True)
        return

    token = grant_mpesa_access(user_id, max_amount, daily_max, valid_days=days)
    click.echo("✅ M-Pesa access granted")
    click.echo(f"   User: {user.email}")
    click.echo(f"   Token: {token}")
    click.echo(f"   Max per transaction: {max_amount} KES")
    click.echo(f"   Max daily total: {daily_max} KES")
    click.echo(f"   Valid for: {days} days")


@auth.command()
@click.option("--token", required=True, help="Access token to revoke")
def revoke_access(token: str) -> None:
    """Revoke a previously granted AI access token."""
    success = revoke_mpesa_access(token)
    if success:
        click.echo("✅ Access token revoked")
    else:
        click.echo("❌ Token not found or already revoked", err=True)


@auth.command()
@click.option("--token", required=True, help="Access token")
@click.option("--amount", type=int, required=True, help="Requested amount")
def check_access(token: str, amount: int) -> None:
    """Validate access token for a requested amount."""
    valid, reason, user_id = validate_mpesa_access(token, amount)
    if valid:
        click.echo("✅ Access token valid")
        click.echo(f"   User ID: {user_id}")
        click.echo(f"   Amount requested: {amount} KES")
    else:
        click.echo(f"❌ Access denied: {reason}", err=True)
