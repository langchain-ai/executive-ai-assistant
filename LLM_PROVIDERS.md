# LLM Provider Guide

The Gmail AI Assistant supports multiple LLM providers. You can choose the one that best fits your needs.

## Supported Providers

### 🌟 Google Gemini (Recommended)

**Why Choose Gemini:**
- ✅ Generous free tier (15 requests/min, 1500/day)
- ✅ Excellent quality (Gemini 1.5 Pro rivals GPT-4)
- ✅ Fast response times
- ✅ Good at following complex instructions
- ✅ Multimodal capabilities (text, images, code)

**Setup:**
```bash
# Get API key from: https://aistudio.google.com/app/apikey
export LLM_PROVIDER=gemini
export GOOGLE_API_KEY=your_gemini_api_key
```

**Models Used:**
- Main tasks: `gemini-1.5-pro`
- Reasoning/Reflection: `gemini-1.5-pro`

**Cost (if exceeding free tier):**
- Gemini 1.5 Pro: $0.00125 per 1K input tokens, $0.005 per 1K output tokens
- Gemini 1.5 Flash: $0.000075 per 1K input tokens, $0.0003 per 1K output tokens

---

### OpenAI

**Why Choose OpenAI:**
- ✅ Industry-leading GPT-4 models
- ✅ Excellent for complex reasoning
- ✅ O1 model for advanced reflection
- ⚠️ More expensive than alternatives
- ⚠️ No free tier

**Setup:**
```bash
# Get API key from: https://platform.openai.com/api-keys
export LLM_PROVIDER=openai
export OPENAI_API_KEY=your_openai_key
```

**Models Used:**
- Main tasks: `gpt-4o`
- Reasoning/Reflection: `o1`

**Cost:**
- GPT-4o: $2.50 per 1M input tokens, $10 per 1M output tokens
- O1: $15 per 1M input tokens, $60 per 1M output tokens

---

### Anthropic Claude

**Why Choose Anthropic:**
- ✅ Excellent at instruction following
- ✅ Strong reasoning capabilities
- ✅ Good context understanding
- ⚠️ More expensive than Gemini
- ⚠️ No free tier

**Setup:**
```bash
# Get API key from: https://console.anthropic.com/settings/keys
export LLM_PROVIDER=anthropic
export ANTHROPIC_API_KEY=your_anthropic_key
```

**Models Used:**
- Main tasks: `claude-3-5-sonnet-latest`
- Reasoning/Reflection: `claude-3-5-sonnet-latest`

**Cost:**
- Claude 3.5 Sonnet: $3 per 1M input tokens, $15 per 1M output tokens

---

## Comparison Table

| Feature | Gemini | OpenAI | Anthropic |
|---------|--------|--------|-----------|
| Free Tier | ✅ Yes (1500/day) | ❌ No | ❌ No |
| Quality | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ |
| Speed | ⚡️ Fast | ⚡️ Fast | ⚡️ Fast |
| Cost (per email) | ~$0.001 | ~$0.005 | ~$0.003 |
| Best For | Personal use | Power users | Enterprises |

*Note: Costs are estimated for a typical email processing workflow (~2K tokens)*

---

## Switching Providers

You can easily switch between providers:

### Method 1: Environment Variables

```bash
# Switch to Gemini
export LLM_PROVIDER=gemini
export GOOGLE_API_KEY=your_key

# Switch to OpenAI
export LLM_PROVIDER=openai
export OPENAI_API_KEY=your_key

# Switch to Anthropic
export LLM_PROVIDER=anthropic
export ANTHROPIC_API_KEY=your_key
```

### Method 2: Edit .env file

```bash
# Edit .env file
LLM_PROVIDER=gemini
GOOGLE_API_KEY=your_gemini_api_key
```

---

## Model Mapping

The assistant automatically maps model names between providers:

| Original Model | Gemini Equivalent | Purpose |
|---------------|-------------------|---------|
| gpt-4o | gemini-1.5-pro | Main tasks |
| gpt-4 | gemini-1.5-pro | Main tasks |
| o1 | gemini-1.5-pro | Reasoning |
| claude-3-5-sonnet | gemini-1.5-pro | Main tasks |

---

## Recommendations

### For Personal Use (Free)
→ **Use Gemini** with free tier (1500 emails/day is more than enough)

### For Heavy Use (<$50/month)
→ **Use Gemini** - Best value for money

### For Maximum Quality (Unlimited budget)
→ **Use OpenAI GPT-4o** - Slight edge in reasoning
→ Or **Anthropic Claude** - Excellent instruction following

### For Production/Business
→ **Use OpenAI or Anthropic** - More established support and SLAs
→ Consider using Gemini for cost optimization on high-volume tasks

---

## Testing Different Providers

Want to test which provider works best for you? You can easily A/B test:

```bash
# Test Gemini for a day
export LLM_PROVIDER=gemini
python scripts/run_ingest.py --minutes-since 1440

# Compare with OpenAI
export LLM_PROVIDER=openai
python scripts/run_ingest.py --minutes-since 1440 --rerun 1

# Check LangSmith traces to compare quality and latency
```

---

## Getting API Keys

### Google Gemini (Easiest - No Credit Card)
1. Go to https://aistudio.google.com/app/apikey
2. Click "Create API Key"
3. Copy the key
4. No credit card required for free tier!

### OpenAI
1. Go to https://platform.openai.com/api-keys
2. Click "Create new secret key"
3. Add billing information
4. Set usage limits (recommended)

### Anthropic Claude
1. Go to https://console.anthropic.com/settings/keys
2. Click "Create Key"
3. Add billing information

---

## FAQ

**Q: Can I use multiple providers?**
A: Yes! Just set multiple API keys in `.env` and switch `LLM_PROVIDER` anytime.

**Q: Which provider do you recommend?**
A: For most users, **Gemini** is the best choice - excellent quality with a generous free tier.

**Q: Will my assistant's behavior change between providers?**
A: Slightly. Each model has different strengths, but they all perform well for email tasks.

**Q: Can I use different providers for different tasks?**
A: Currently, the provider is global, but you can modify `eaia/llm_factory.py` to customize this.

**Q: What if I exceed Gemini's free tier?**
A: You'll get rate limited. Either wait for the quota to reset (daily) or add billing to continue.

**Q: Is my data sent to these providers?**
A: Yes, email content is sent to the LLM provider you choose. Review their privacy policies.
