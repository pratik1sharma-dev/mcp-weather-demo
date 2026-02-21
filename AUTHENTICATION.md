# MCP Server Authentication Guide

This guide explains how to secure your MCP Weather Server with API key authentication.

## Overview

The MCP Weather Server supports **optional API key authentication** to control access. This is useful when:
- Deploying to shared environments
- Limiting access to specific clients
- Adding an extra security layer
- Demonstrating enterprise MCP patterns

## How It Works

```
┌─────────────────┐                          ┌──────────────────┐
│  MCP Client     │                          │   MCP Server     │
│                 │                          │                  │
│  1. Load API    │                          │  1. Load valid   │
│     key from    │                          │     keys from    │
│     .env        │                          │     .env         │
│                 │                          │                  │
│  2. Connect to  │   (stdio + env vars)     │                  │
│     server      ├─────────────────────────>│  2. Receive      │
│                 │                          │     client key   │
│                 │                          │                  │
│  3. Make tool   │   (tool call request)    │  3. Validate     │
│     call        ├─────────────────────────>│     API key      │
│                 │                          │                  │
│                 │   ✅ Result (if valid)   │  4. Process if   │
│  4. Get result  │<─────────────────────────│     authorized   │
│                 │   ❌ Error (if invalid)  │                  │
└─────────────────┘                          └──────────────────┘
```

## Setup

### Step 1: Generate API Keys

You can generate secure API keys using Python:

```bash
# Generate a single key
python -c "import secrets; print(secrets.token_urlsafe(32))"

# Output example: xvK8mN_sPqR2tUvWxYz3AbCdEfGhIjKl4mN5oPqR6sT
```

### Step 2: Configure Server (Server-Side)

Edit your `.env` file and add valid API keys:

```bash
# Allow multiple keys (comma-separated, no spaces)
MCP_SERVER_API_KEYS=xvK8mN_sPqR2tUvWxYz3AbCdEfGhIjKl4mN5oPqR6sT,anotherkey123

# Single key
MCP_SERVER_API_KEYS=xvK8mN_sPqR2tUvWxYz3AbCdEfGhIjKl4mN5oPqR6sT

# Disable authentication (leave empty)
MCP_SERVER_API_KEYS=
```

### Step 3: Configure Client (Client-Side)

The client needs ONE key that matches a server key:

```bash
# Must match one of the keys in MCP_SERVER_API_KEYS
MCP_CLIENT_API_KEY=xvK8mN_sPqR2tUvWxYz3AbCdEfGhIjKl4mN5oPqR6sT
```

### Step 4: Test Authentication

**Start the server** and look for authentication status:
```bash
python -m server.weather_server

# You should see:
# Starting MCP Weather Server...
# 🔒 Authentication: ENABLED (1 valid key(s))  ← Authentication is ON
# OR
# 🔓 Authentication: DISABLED                  ← No authentication
```

**Run the client**:
```bash
python -m client.weather_client

# If authentication succeeds:
# 🔒 Authenticating with MCP server...
# ✅ Connected to MCP Weather Server

# If authentication fails:
# ❌ Authentication Error: Invalid API key. Access denied.
```

## Authentication Modes

### Mode 1: Authentication Disabled (Default)

**Configuration:**
```bash
MCP_SERVER_API_KEYS=          # Empty = no auth
# MCP_CLIENT_API_KEY not needed
```

**Behavior:**
- ✅ All clients can connect
- ✅ No API key required
- ✅ Perfect for local development
- ⚠️ Not secure for production

**Use when:**
- Learning MCP
- Local development
- Testing

### Mode 2: Authentication Enabled

**Configuration:**
```bash
# Server side
MCP_SERVER_API_KEYS=your_secure_key_here

# Client side
MCP_CLIENT_API_KEY=your_secure_key_here
```

**Behavior:**
- ✅ Only authorized clients can connect
- ✅ Requests validated before processing
- ✅ Secure for shared environments
- ❌ Clients without valid keys are rejected

**Use when:**
- Production deployments
- Multi-tenant environments
- Public demos with restricted access
- Enterprise scenarios

## Security Best Practices

### 1. Key Generation
```bash
# ✅ GOOD: Use cryptographically secure random keys
python -c "import secrets; print(secrets.token_urlsafe(32))"

# ❌ BAD: Don't use weak keys
MCP_SERVER_API_KEYS=password123
MCP_SERVER_API_KEYS=test
```

### 2. Key Storage
```bash
# ✅ GOOD: Store in .env (ignored by git)
MCP_SERVER_API_KEYS=xvK8mN_sPqR...

# ❌ BAD: Don't commit keys to git
# ❌ BAD: Don't hardcode in source files
```

### 3. Key Rotation
```bash
# Support multiple keys for rotation
MCP_SERVER_API_KEYS=new_key,old_key

# Steps:
# 1. Add new key alongside old key
# 2. Update clients to use new key
# 3. Remove old key once all clients updated
```

### 4. Key Distribution
- ✅ Share keys securely (encrypted channels, password managers)
- ✅ Use different keys per environment (dev, staging, prod)
- ❌ Don't share keys in plain text emails
- ❌ Don't post keys in public forums/Slack

## Troubleshooting

### Error: "Missing API key"

**Problem:** Client didn't provide an API key, but server requires one.

**Solution:**
```bash
# Add to client .env:
MCP_CLIENT_API_KEY=your_key_here
```

### Error: "Invalid API key. Access denied"

**Problem:** Client provided a key, but it doesn't match any valid server keys.

**Solutions:**
1. **Check for typos** in client or server keys
2. **Verify keys match exactly** (no extra spaces)
3. **Regenerate and sync keys** if needed

```bash
# Server .env
MCP_SERVER_API_KEYS=abc123

# Client .env (must match!)
MCP_CLIENT_API_KEY=abc123
```

### Server says "Authentication disabled" but you want it enabled

**Problem:** `MCP_SERVER_API_KEYS` is empty or not set.

**Solution:**
```bash
# Generate and add a key
python -c "import secrets; print(secrets.token_urlsafe(32))"

# Add to .env
MCP_SERVER_API_KEYS=generated_key_here
```

### Error: "ImportError: cannot import name 'AuthManager'"

**Problem:** The auth module isn't being found.

**Solution:**
Make sure you're running from the project root:
```bash
cd /path/to/mcp-weather-demo
python -m client.weather_client
```

## Advanced: Multiple Keys for Multiple Clients

You can issue different keys to different clients:

```bash
# Server configuration
MCP_SERVER_API_KEYS=client1_key,client2_key,client3_key

# Client 1's .env
MCP_CLIENT_API_KEY=client1_key

# Client 2's .env
MCP_CLIENT_API_KEY=client2_key

# Client 3's .env
MCP_CLIENT_API_KEY=client3_key
```

Benefits:
- Track which client is making requests (with logging)
- Revoke individual clients without affecting others
- Different permission levels (future enhancement)

## Key Management Script

Here's a helper script to manage keys:

```bash
#!/bin/bash
# generate_key.sh

echo "🔐 MCP API Key Generator"
echo "======================="
echo ""

KEY=$(python -c "import secrets; print(secrets.token_urlsafe(32))")

echo "Generated API Key:"
echo ""
echo "  $KEY"
echo ""
echo "Add this to your .env file:"
echo ""
echo "  Server: MCP_SERVER_API_KEYS=$KEY"
echo "  Client: MCP_CLIENT_API_KEY=$KEY"
echo ""
```

Save as `generate_key.sh`, make executable, and run:
```bash
chmod +x generate_key.sh
./generate_key.sh
```

## Testing Authentication

### Test 1: Verify Auth Disabled
```bash
# Ensure .env has empty server keys
MCP_SERVER_API_KEYS=

# Run client - should work without API key
python -m client.weather_client --demo
```

### Test 2: Verify Auth Enabled (Valid Key)
```bash
# Generate a key
KEY=$(python -c "import secrets; print(secrets.token_urlsafe(32))")

# Set in .env
MCP_SERVER_API_KEYS=$KEY
MCP_CLIENT_API_KEY=$KEY

# Run client - should authenticate successfully
python -m client.weather_client --demo
```

### Test 3: Verify Auth Blocks Invalid Key
```bash
# Server has one key
MCP_SERVER_API_KEYS=valid_key

# Client has wrong key
MCP_CLIENT_API_KEY=wrong_key

# Run client - should see authentication error
python -m client.weather_client
# Expected: "❌ Authentication Error: Invalid API key"
```

## Production Deployment Checklist

- [ ] Generate strong API keys using `secrets.token_urlsafe(32)`
- [ ] Configure `MCP_SERVER_API_KEYS` on server
- [ ] Distribute `MCP_CLIENT_API_KEY` to authorized clients
- [ ] Store keys in secure secrets management (Vault, AWS Secrets Manager, etc.)
- [ ] Test authentication works before going live
- [ ] Document key rotation process
- [ ] Set up monitoring for failed auth attempts
- [ ] Plan for key revocation if compromised

## FAQ

**Q: Is authentication required?**
A: No, it's optional. Leave `MCP_SERVER_API_KEYS` empty to disable.

**Q: Can I use the same key for multiple clients?**
A: Yes, but using different keys per client is more secure.

**Q: How long should keys be?**
A: The default (32 characters from `token_urlsafe(32)`) is secure.

**Q: Can I change keys without downtime?**
A: Yes! Add new key, keep old key, update clients, then remove old key.

**Q: Are keys encrypted?**
A: Keys are hashed (SHA256) in memory. Store them securely in `.env`.

**Q: Does this work over network?**
A: This demo uses stdio (local). For network, use TLS/HTTPS + auth headers.

## Next Steps

- Implement **role-based access control** (RBAC)
- Add **JWT tokens** for time-limited access
- Integrate with **OAuth 2.0** for enterprise auth
- Add **audit logging** for security compliance
- Implement **rate limiting** per API key

## Resources

- [Python secrets module](https://docs.python.org/3/library/secrets.html)
- [MCP Specification - Security](https://spec.modelcontextprotocol.io/)
- [OWASP API Security](https://owasp.org/www-project-api-security/)
