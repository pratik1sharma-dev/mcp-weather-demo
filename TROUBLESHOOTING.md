# Troubleshooting Guide

Common issues and solutions for the MCP Weather Demo.

## Installation Issues

### Issue: `pip install` fails

**Solution 1**: Upgrade pip
```bash
pip install --upgrade pip
```

**Solution 2**: Use a virtual environment
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt
```

**Solution 3**: Check Python version
```bash
python --version  # Should be 3.10 or higher
```

### Issue: Package version conflicts

**Solution**: Install with exact versions
```bash
pip install anthropic==0.39.0 mcp==1.0.0 requests==2.31.0 python-dotenv==1.0.0
```

## API Key Issues

### Issue: "OPENWEATHER_API_KEY not set"

**Checklist:**
1. ✅ Created `.env` file in project root
2. ✅ Copied content from `.env.example`
3. ✅ Added actual API key (not placeholder text)
4. ✅ No spaces around the `=` sign
5. ✅ No quotes around the key

**Correct format:**
```
OPENWEATHER_API_KEY=abc123def456
GEMINI_API_KEY=AIzaSy...
```

**Incorrect formats:**
```
OPENWEATHER_API_KEY = abc123     # ❌ spaces
OPENWEATHER_API_KEY="abc123"     # ❌ quotes
OPENWEATHER_API_KEY=your_key_here  # ❌ placeholder
```

### Issue: "Invalid API key" from OpenWeatherMap

**Solutions:**
1. Verify key at https://home.openweathermap.org/api_keys
2. Wait 10 minutes after creating a new key (activation delay)
3. Check that you're using the correct key type (free tier works)
4. Ensure no extra characters were copied

### Issue: Gemini API errors

**Common causes:**
- Invalid API key
- Rate limiting (free tier: 15 requests/min, 1500/day)
- API not enabled

**Solution:**
1. Check key at https://makersuite.google.com/app/apikey
2. Verify API is enabled for your Google Cloud project
3. Check rate limits if getting 429 errors
4. Wait a minute and try again

## Runtime Issues

### Issue: Client can't connect to server

**Error message:**
```
Error: Failed to connect to MCP server
```

**Solutions:**

1. **Check server path**: Ensure the server module is accessible
```bash
# From project root
python -m server.weather_server  # Should start without errors
```

2. **Check environment**: Server needs `OPENWEATHER_API_KEY`
```bash
# Test server directly
python -c "from server.weather_server import OPENWEATHER_API_KEY; print(OPENWEATHER_API_KEY)"
```

3. **Check working directory**: Run client from project root
```bash
cd /path/to/mcp-weather-demo
python -m client.weather_client
```

### Issue: "Tool not found" error

**Possible causes:**
- Server didn't expose the tool correctly
- Client and server out of sync

**Solution:**
```bash
# Restart both client and server
# Check stderr output for "Available tools: ..."
```

### Issue: Weather data returns "city not found"

**Causes:**
- Typo in city name
- City requires country code (e.g., "Portland,US" vs "Portland")
- OpenWeatherMap doesn't have that city

**Solution:**
```python
# Use country codes for ambiguous cities
"London,UK"
"Paris,FR"
"Portland,US"
"Portland,OR,US"
```

### Issue: Slow responses

**Possible causes:**
1. OpenWeatherMap API latency
2. Claude API latency
3. Network issues

**Solutions:**
- Add caching for repeated queries
- Use timeout parameters
- Check network connection

## Gemini Integration Issues

### Issue: Gemini not using tools

**Symptoms:**
- Gemini responds without calling weather tools
- Response is generic or says "I don't have real-time data"

**Solutions:**

1. **Check tool definitions**: Ensure tools are properly formatted
```python
# Tools must be in Gemini function declaration format
function_declaration = genai.protos.FunctionDeclaration(
    name=tool.name,
    description=tool.description,
    parameters=genai.protos.Schema(...)
)
```

2. **Check model version**: Use Gemini 1.5
```python
model_name='gemini-1.5-flash'  # Good (free tier)
model_name='gemini-1.5-pro'    # Also good (paid)
model_name='gemini-1.0-pro'    # Older, may not work as well
```

3. **Improve prompts**: Be explicit
```
Bad:  "What's the weather?"
Good: "What's the current weather in Boston?"
```

### Issue: "Resource exhausted" or 429 errors

**Cause:** Exceeded free tier limits
- 15 requests per minute
- 1500 requests per day

**Solution:**
- Wait a minute between queries
- Add rate limiting to your code
- Consider upgrading to paid tier for higher limits

### Issue: Tool loop / infinite recursion

**Symptoms:**
- Client keeps calling same tool
- Never reaches `end_turn`

**Solutions:**

1. **Check response handling**: Ensure results are added to messages
```python
messages.append({"role": "assistant", "content": response.content})
messages.append({"role": "user", "content": tool_results})
```

2. **Add loop limit**: Prevent infinite loops
```python
max_iterations = 10
for i in range(max_iterations):
    # ... existing loop
```

## Data Format Issues

### Issue: Temperature units wrong

**Note:** This demo uses metric (Celsius) by default.

**To change to Fahrenheit:**
```python
# In server/weather_server.py
params["units"] = "imperial"  # Instead of "metric"
```

### Issue: Timestamp format unclear

**Solution:** Format timestamps in tool responses
```python
from datetime import datetime

dt = datetime.fromtimestamp(data['dt'])
formatted = dt.strftime("%Y-%m-%d %H:%M:%S")
```

## Debug Mode

### Enable verbose output

**In server:**
```python
# At top of weather_server.py
import logging
logging.basicConfig(level=logging.DEBUG)
```

**In client:**
```python
# At top of weather_client.py
import logging
logging.basicConfig(level=logging.DEBUG)
```

### Check MCP messages

**Add message logging:**
```python
# In client
print(f"📤 Sending to Claude: {messages}", file=sys.stderr)
print(f"📥 Received from Claude: {response}", file=sys.stderr)
```

### Test server independently

**Direct server test:**
```bash
# Send a tools/list request
echo '{"jsonrpc":"2.0","id":1,"method":"tools/list"}' | python -m server.weather_server
```

## Environment-Specific Issues

### macOS Issues

**Issue:** Permission denied
```bash
chmod +x server/weather_server.py
chmod +x client/weather_client.py
```

**Issue:** Python version mismatch
```bash
python3 --version  # Use python3 instead of python
python3 -m client.weather_client
```

### Windows Issues

**Issue:** Module not found
```bash
# Use full Python path
python -m client.weather_client

# Or add to PYTHONPATH
set PYTHONPATH=%CD%
python -m client.weather_client
```

**Issue:** Encoding errors
```python
# Add to top of Python files
# -*- coding: utf-8 -*-
```

### Linux Issues

**Issue:** SSL certificate errors
```bash
pip install --upgrade certifi
```

## Getting Help

If you're still stuck:

1. **Check logs**: Look at stderr output for clues
2. **Minimal reproduction**: Try with a simple query
3. **Version check**: Ensure all packages are up to date
```bash
pip list | grep -E "anthropic|mcp|requests"
```

4. **File an issue**: Include:
   - Python version
   - OS
   - Full error message
   - Steps to reproduce

## Common Error Messages

### "Connection refused"
→ Server not running or wrong port

### "Module not found"
→ Wrong directory or missing package

### "Invalid API key"
→ Check .env file and API key

### "Rate limit exceeded"
→ Too many requests, wait or upgrade API plan

### "Timeout"
→ Network issue or slow API response

### "Tool call failed"
→ Check tool arguments and server logs

## Quick Health Check

Run this to verify setup:

```bash
# 1. Check Python version
python --version

# 2. Check packages
pip list | grep -E "google-generativeai|mcp|requests"

# 3. Check environment
python -c "from dotenv import load_dotenv; import os; load_dotenv(); print('Weather API:', 'OK' if os.getenv('OPENWEATHER_API_KEY') else 'MISSING'); print('Gemini API:', 'OK' if os.getenv('GEMINI_API_KEY') else 'MISSING')"

# 4. Test server
python -c "from server.weather_server import OPENWEATHER_API_KEY; print('Server can load')"

# 5. Test client
python -c "from client.weather_client import ANTHROPIC_API_KEY; print('Client can load')"
```

If all checks pass, you're good to go! 🎉
