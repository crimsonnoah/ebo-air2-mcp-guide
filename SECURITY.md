# Security policy

This project controls a physical robot and handles several credentials. Treat deployment configuration as sensitive infrastructure.

## Never publish

- Enabot account email or password
- EBO HOME payload/sign constants
- API or MCP bearer tokens
- Fish Audio API keys or voice IDs
- Telegram bot tokens or chat identifiers
- Robot serial number or MAC address
- Home SSID, public IP, VPN/tunnel credentials
- Production `options.json`, `.env`, logs, APKs, or proprietary libraries

## Network exposure

- Keep ports 8098 and 8100 bound to loopback by default.
- For remote MCP, use authenticated HTTPS through a VPN, reverse proxy, or secure tunnel.
- Do not remove bearer-token authentication.
- Use a long random token and rotate it after any suspected exposure.

## Physical safety

- Test on a flat, open floor away from stairs and edges.
- Require a fresh camera view before movement.
- Keep initial movements short and slow.
- Software stop travels through a network/cloud path and is not an emergency stop.

## Reporting a vulnerability

Open a GitHub issue only for non-sensitive reports. For a report that would expose credentials or a working unauthenticated-control path, contact the maintainer privately through the contact method on their GitHub profile. Do not include live secrets or private device data.
