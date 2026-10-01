from __future__ import annotations

import asyncio
from typing import Any

import click

from ai_request_handler import AIRequestHandler
from auth import get_user_by_id
from database import init_database


@click.group()
def cli() -> None:
    """M-Pesa AI Agent CLI - User approval required for all payments."""
    init_database()


@cli.group()
def ai() -> None:
    """AI query commands with M-Pesa payments."""
    pass


@ai.command()
@click.option("--user-id", type=int, required=True, help="User ID")
@click.option("--prompt", prompt="Your query", help="What would you like to ask?")
@click.option(
    "--service",
    type=click.Choice(["basicQuery", "advancedAnalysis", "customReport", "premiumSupport"]),
    default="basicQuery",
    help="Service type",
)
def request(user_id: int, prompt: str, service: str) -> None:
    """Request AI query with M-Pesa payment approval."""
    async def run() -> None:
        # Verify user exists
        user = get_user_by_id(user_id)
        if not user:
            click.echo("❌ User not found", err=True)
            return

        if not user.phone_number:
            click.echo("❌ No phone number on file. Please update your profile.", err=True)
            return

        # Create request handler
        handler = AIRequestHandler()

        # Process request with user approval
        click.echo("\n" + "=" * 50)
        click.echo("AI QUERY REQUEST WITH PAYMENT")
        click.echo("=" * 50)

        result = await handler.process_with_approval(
            user_id=user_id,
            prompt=prompt,
            service_type=service,
            phone_number=user.phone_number,
        )

        if result["success"]:
            click.echo(f"\n✅ Query processed successfully")
            click.echo(f"   Payment ID: {result['payment_id']}")
            click.echo(f"   Cost: {result['cost']} KES")
            click.echo(f"\n📋 Answer:\n\n{result['response']}")
        else:
            click.echo(f"\n❌ Request failed: {result['error']}", err=True)

    asyncio.run(run())


if __name__ == "__main__":
    cli()
