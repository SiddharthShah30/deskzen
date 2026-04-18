# Groq API Setup for Denji AI

Denji now uses **Groq** for intelligent, real-time LLM responses. Groq is:
- **Ultra-fast**: Responses in milliseconds
- **Free tier**: Generous rate limits (no credit card needed)
- **No local setup**: No need to download large models

## Quick Setup (2 minutes)

### 1. Get a Free Groq API Key
1. Go to **https://console.groq.com** (or https://groq.com)
2. Click **Sign Up** and create a free account
3. Generate an API key from the dashboard
4. Copy the key

### 2. Set Environment Variable

#### On Windows (PowerShell)
```powershell
$env:GROQ_API_KEY = "your-api-key-here"
```

#### On Windows (Command Prompt)
```cmd
set GROQ_API_KEY=your-api-key-here
```

#### Persistent Setup (Recommended)
Add to your **system environment variables**:
- Press `Win + X` → **System**
- **Advanced system settings** → **Environment Variables**
- Click **New** under "User variables"
- Variable name: `GROQ_API_KEY`
- Variable value: `your-api-key-here`
- Click OK and restart your terminal/Denji

### 3. Test It
Open Denji and type `test` — you should see `[GROQ]` responses instead of `[TARS]`.

## What You Get

- **Groq Backend**: Real LLM responses with personality
- **Instant Responses**: No waiting for inference
- **TARS Personality**: Responses sound dry, witty, and concise
- **Fallback to TARS**: If Groq is unavailable, Denji falls back to offline TARS personality system

## Model Used
- **mixtral-8x7b-32768**: Fast, intelligent, 32k context window

## Free Tier Limits
- Groq free tier supports hundreds of requests per day
- Perfect for individual Denji use

## Troubleshooting

If you see `[TARS]` instead of `[GROQ]`:
- Check your API key is set correctly
- Verify the key is not expired in the Groq console
- Check internet connectivity
- Denji will automatically fall back to TARS if Groq is unavailable

Enjoy real AI-powered responses!
