import click


@click.command()
@click.option("--test-case", "-t", help="Specific test case ID to run")
@click.option("--provider", "-p", default="anthropic", help="LLM provider (anthropic, openai, local)")
@click.option("--model", "-m", help="Model name to use")
@click.option("--mcp/--no-mcp", default=False, help="Enable MCP server")
def run(test_case, provider, model, mcp):
    """Run FHIR query evaluations"""
    click.echo(f"Running evaluations...")
    click.echo(f"Provider: {provider}")
    if test_case:
        click.echo(f"Test case: {test_case}")
    if model:
        click.echo(f"Model: {model}")
    if mcp:
        click.echo("MCP: Enabled")

    # TODO: Implement evaluation logic
    click.echo("Not yet implemented")
