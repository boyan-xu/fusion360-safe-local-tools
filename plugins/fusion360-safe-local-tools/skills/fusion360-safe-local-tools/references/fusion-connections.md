# Fusion connection references

Reviewed documentation: 2026-09-17. These are original summaries and source links, not vendored code or dependencies. Community capabilities below are author claims, not audited or locally tested implementations.

## Official desktop MCP — first option to evaluate

[Autodesk overview](https://help.autodesk.com/view/fusion360/ENU/?guid=FMCP-OVERVIEW) distinguishes the local desktop MCP (live modeling and active-document inspection) from the cloud Data MCP (projects, folders and manufacturing data). Live CAD work needs the desktop endpoint.

[Autodesk's add-in development tutorial](https://www.autodesk.com/products/fusion-360/blog/build-your-own-fusion-add-ins-with-the-fusion-mcp/) describes Preferences > General > API > Fusion MCP Server, usually on local port 27182, and tools for documentation lookup, Python execution and inspecting errors. Verify the actual endpoint and available tools rather than assuming the default. Availability depends on the installed Fusion version and entitlement.

For a future connection request, inspect whether the installed Fusion exposes the official option before implementing another bridge. Any additional local service requires a separately reviewed integration. Keep the no-autostart, minimum-permission and no-system-level-change constraints. Do not enable the endpoint merely to inspect its availability. Do not promise client compatibility before checking its transport support and available tools.

[Current official troubleshooting](https://help.autodesk.com/view/fusion360/ENU/?guid=ADSKMCP_FusionDesktopMcp_troubleshooting_html) specifies `http://127.0.0.1:27182/mcp`, including the `/mcp` path. Prefer this explicit endpoint over the root URL shown in the older tutorial, and verify against the installed release.

## Community alternatives

| Project | Documented approach | Potential value |
| --- | --- | --- |
| [faust-machines/fusion360-mcp-server](https://github.com/faust-machines/fusion360-mcp-server) | Python MCP server, TCP bridge, Fusion Add-In, main-thread CustomEvent dispatch; macOS instructions; beta | Reference for dispatching work onto Fusion's main thread if a custom bridge becomes necessary |
| [ignaciomolini/mcp-fusion360](https://github.com/ignaciomolini/mcp-fusion360) | Python Add-In and TypeScript server; local HTTP; parameter snapshots/rollback; startup disabled by default | Reference for bounded parameter changes and recovery; rollback is not a substitute for checking scope and results |
| [dterracino/f360mcp](https://github.com/dterracino/f360mcp) | File-based communication; geometry tools and general Python/API execution | Alternative transport to evaluate, but file communication still requires active processing and general execution is broad access |
| [ndoo/fusion360-mcp-bridge](https://github.com/ndoo/fusion360-mcp-bridge) | macOS quickstart; Python MCP server and Fusion Add-In; README describes loopback HTTP with shared bearer token, arbitrary Python execution and screenshots | Candidate for a small bridge; inspect actual authentication behavior, especially when the secret file is missing, before adopting |

The faust-machines README explicitly states that its TCP socket has no authentication. Keep this limitation in the comparison; loopback binding does not authenticate other local processes. The ndoo quickstart installs dependencies and edits Claude configuration, so it should not be blindly run for a different client. These findings are documentation-level checks, not a source audit or a successful installation.

Before incorporating code, inspect a pinned revision, its license and required notices, dependencies, binding addresses, authentication, command queue limits, timeouts and cleanup. Import only a needed component with compatible licensing; avoid wholesale repository copies. None of these projects has been security-audited here.

## Useful official API references

- [Scripts.addExisting](https://help.autodesk.com/cloudhelp/ENU/Fusion-360-API/files/Scripts_addExisting.htm): register an existing folder without copying it into AddIns.
- [Script.stop](https://help.autodesk.com/cloudhelp/ENU/Fusion-360-API/files/Script_stop.htm) and [Script.unlink](https://help.autodesk.com/cloudhelp/ENU/Fusion-360-API/files/Script_unlink.htm): stop execution and remove external registration separately.
- [Application.registerCustomEvent](https://help.autodesk.com/cloudhelp/ENU/Fusion-360-API/files/Application_registerCustomEvent.htm): relevant if future authorized work introduces a worker; current add-in needs no worker or custom event.

Use the installed API definitions to verify signatures against the user's Fusion version. Exercise run, command invocation, stop and partial-start failure inside Fusion; Python syntax checks alone cannot establish runtime correctness.
