# MCP client setup

The EBO server uses Streamable HTTP MCP and a bearer token.

## Before connecting

- Same-host client URL: `http://127.0.0.1:8100/mcp`
- LAN client URL: `http://SERVER_LAN_IP:8100/mcp`
- Cloud client URL: authenticated `https://YOUR_MCP_HOST/mcp`
- Header: `Authorization: Bearer YOUR_API_TOKEN`

Do not expose port 8100 directly to the public internet. Use an authenticated HTTPS reverse proxy, VPN, or secure tunnel. A hosted client cannot reach your server's `127.0.0.1`.

## Claude Code

Anthropic recommends remote HTTP for remote MCP servers:

```bash
claude mcp add --transport http ebo http://127.0.0.1:8100/mcp \
  --header "Authorization: Bearer YOUR_API_TOKEN"
```

Verify:

```bash
claude mcp list
```

Project-scoped `.mcp.json` alternative:

```json
{
  "mcpServers": {
    "ebo": {
      "type": "http",
      "url": "http://127.0.0.1:8100/mcp",
      "headers": {
        "Authorization": "Bearer YOUR_API_TOKEN"
      }
    }
  }
}
```

Do not commit a real token in `.mcp.json`.

Official reference: [Claude Code MCP documentation](https://docs.anthropic.com/en/docs/claude-code/mcp).

## Codex CLI, IDE, and ChatGPT desktop

Codex stores MCP settings in `~/.codex/config.toml`, or in a trusted project's `.codex/config.toml`. Keep the token in an environment variable:

```bash
export EBO_MCP_TOKEN='YOUR_API_TOKEN'
```

```toml
[mcp_servers.ebo]
url = "http://127.0.0.1:8100/mcp"
bearer_token_env_var = "EBO_MCP_TOKEN"
```

Verify with `codex mcp list`, or use `/mcp` inside the Codex TUI. The ChatGPT desktop app and Codex IDE extension can also add a Streamable HTTP server from their MCP server settings.

Official references:

- [Codex MCP guide](https://developers.openai.com/codex/mcp)
- [Codex configuration reference](https://developers.openai.com/codex/config-reference)

## OpenAI Responses API

The Responses API can call a remote MCP server, but the MCP URL must be reachable from OpenAI's hosted service. A loopback or private-LAN URL will not work.

Use an authenticated HTTPS endpoint and pass the bearer token through the API's remote MCP tool configuration. Keep both the OpenAI API key and EBO token in a server-side secret manager.

Official reference: [OpenAI remote MCP tools](https://developers.openai.com/api/docs/guides/tools-connectors-mcp).

## Recommended operating instructions

Give the agent durable safety rules:

```text
Before any EBO movement or Skill Action:
1. Call ebo_look.
2. Confirm the robot is awake, off the charging dock, and has clear floor space.
3. Use a conservative speed and duration.
4. Re-look before every later movement.
Never describe ebo_stop as a hardware emergency stop.
```

## Safe first test

Ask the client:

```text
List my EBO, report its state, wake it if needed, and look through its camera. Do not move it.
```

Only after the image is fresh and the floor is confirmed safe should you test a one-second movement.
