from __future__ import annotations

import asyncio

import click

from ai_payment_agent import AIPaymentAgent
from ai import get_user_transactions, invoke_ai
from auth import get_user_by_email, login_user, register_user
from database import init_database
from payment import get_payment_status, initiate_stk_push


@click.group()
def cli() -> None:
    """M-Pesa AI Agent CLI with autonomous payments."""
    init_database()


@cli.group()
def auth() -> None:
    """Authentication commands."""
    pass


@auth.command()
@click.option("--email", prompt=True, help="Email address")
@click.option("--password", prompt=True, hide_input=True, help="Password")
@click.option("--name", prompt=True, help="Full name")
@click.option("--phone", default=None, help="Phone number (optional)")
def register(email: str, password: str, name: str, phone: str | None = None) -> None:
    """Register a new user."""
    try:
        user = register_user(email, password, name, phone)
        click.echo(f"✓ User registered: {user.email}")
    except Exception as e:
        click.echo(f"✗ Registration failed: {str(e)}", err=True)


@auth.command()
@click.option("--email", prompt=True, help="Email address")
@click.option("--password", prompt=True, hide_input=True, help="Password")
def login(email: str, password: str) -> None:
    """Login user."""
    try:
        user = login_user(email, password)
        click.echo(f"✓ Logged in as {user.email} (ID: {user.id})")
    except Exception as e:
        click.echo(f"✗ Login failed: {str(e)}", err=True)


@cli.group()
def payment() -> None:
    """Payment commands."""
    pass


@payment.command()
@click.option("--user-id", type=int, required=True, help="User ID")
@click.option("--phone", required=True, help="M-Pesa phone number (e.g., 254712345678)")
@click.option("--service", type=click.Choice(["basicQuery", "advancedAnalysis", "customReport", "premiumSupport"]), default="basicQuery", help="Service type")
def start(user_id: int, phone: str, service: str) -> None:
    """Start an M-Pesa payment."""
    async def run() -> None:
        try:
            payment = await initiate_stk_push(user_id, phone, service)
            click.echo(f"✓ STK push initiated")
            click.echo(f"  Checkout ID: {payment.checkout_request_id}")
            click.echo(f"  Amount: {payment.amount} KES")
            click.echo(f"  Status: {payment.status}")
        except Exception as e:
            click.echo(f"✗ Payment failed: {str(e)}", err=True)
    
    asyncio.run(run())


@payment.command()
@click.option("--checkout-id", required=True, help="Checkout request ID")
def status(checkout_id: str) -> None:
    """Check payment status."""
    payment = get_payment_status(checkout_id)
    if payment is None:
        click.echo("✗ Payment not found", err=True)
        return
    
    click.echo(f"Checkout ID: {payment.checkout_request_id}")
    click.echo(f"Amount: {payment.amount} KES")
    click.echo(f"Status: {payment.status}")
    click.echo(f"Service: {payment.service_type}")
    if payment.receipt:
        click.echo(f"Receipt: {payment.receipt}")


@cli.group()
def ai() -> None:
    """AI commands."""
    pass


@ai.command()
@click.option("--user-id", type=int, required=True, help="User ID")
@click.option("--checkout-id", required=True, help="Checkout request ID")
@click.option("--prompt", prompt=True, help="Your query")
@click.option("--service", type=click.Choice(["basicQuery", "advancedAnalysis", "customReport", "premiumSupport"]), default="basicQuery", help="Service type")
def invoke(user_id: int, checkout_id: str, prompt: str, service: str) -> None:
    """Invoke AI for a paid query."""
    async def run() -> None:
        try:
            transaction = await invoke_ai(user_id, checkout_id, prompt, service)
            click.echo(f"✓ Query processed")
            click.echo(f"\nAnswer:\n{transaction.answer}")
        except Exception as e:
            click.echo(f"✗ Query failed: {str(e)}", err=True)
    
    asyncio.run(run())


@ai.command()
@click.option("--user-id", type=int, required=True, help="User ID")
@click.option("--prompt", prompt=True, help="Your request")
@click.option("--service", type=click.Choice(["basicQuery", "advancedAnalysis", "customReport", "premiumSupport"]), default="basicQuery", help="Service type")
def autopay(user_id: int, prompt: str, service: str) -> None:
    """Let AI agent autonomously handle payment and query."""
    async def run() -> None:
        try:
            agent = AIPaymentAgent()
            result = await agent.analyze_and_pay(user_id, prompt, service)
            
            if result["success"]:
                click.echo(f"✓ AI Agent Payment Executed")
                click.echo(f"  Payment ID: {result['payment_id']}")
                click.echo(f"  Cost: {result['cost']} KES")
                click.echo(f"\n✓ AI Response:\n{result['response']}")
            else:
                click.echo(f"✗ AI Payment Failed: {result['error']}", err=True)
        except Exception as e:
            click.echo(f"✗ Error: {str(e)}", err=True)
    
    asyncio.run(run())


@cli.group()
def transactions() -> None:
    """Transaction commands."""
    pass


@transactions.command()
@click.option("--user-id", type=int, required=True, help="User ID")
def history(user_id: int) -> None:
    """View transaction history."""
    txns = get_user_transactions(user_id)
    if not txns:
        click.echo("No transactions found")
        return
    
    click.echo(f"\nTotal transactions: {len(txns)}")
    for i, txn in enumerate(txns, 1):
        click.echo(f"\n{i}. {txn.service_type} - {txn.amount} KES")
        click.echo(f"   Created: {txn.created_at}")
        click.echo(f"   Q: {txn.prompt[:50]}..." if len(txn.prompt) > 50 else f"   Q: {txn.prompt}")
        click.echo(f"   A: {txn.answer[:50]}..." if len(txn.answer) > 50 else f"   A: {txn.answer}")


if __name__ == "__main__":
    cli()
