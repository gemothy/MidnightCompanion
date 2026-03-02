# View Star Office from another machine (e.g. your Mac)

Star Office runs on the **server** (port 19791). To open it in a browser on your Mac, use one of these.

## Option 1: SSH port forward (recommended)

On your **Mac**, run:

```bash
ssh -L 19791:localhost:19791 YOUR_USER@YOUR_SERVER
```

Leave that session open. Then on the Mac open **http://localhost:19791** — traffic is forwarded to the server.

## Option 2: Cloudflare quick tunnel

On the **server** (where Star Office is running):

```bash
# Install once: https://developers.cloudflare.com/cloudflare-one/connections/connect-apps/install-and-setup/tunnel-guide/
cloudflared tunnel --url http://127.0.0.1:19791
```

Use the `https://xxx.trycloudflare.com` URL in your Mac browser. The URL can change each time you run the tunnel.
