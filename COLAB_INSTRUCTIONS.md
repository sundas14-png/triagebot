# 🎓 Running TriageBot in Google Colab

Perfect for recording your demo without installing anything locally!

---

## 🚀 Quick Start (2 Minutes)

### Option 1: Direct Link (Easiest)

**Click this link to open in Colab:**

👉 **https://colab.research.google.com/github/sundas14-png/triagebot/blob/main/TriageBot_Demo.ipynb**

### Option 2: Manual Upload

1. Go to https://colab.research.google.com/
2. Click **File** → **Open notebook**
3. Select **GitHub** tab
4. Paste: `sundas14-png/triagebot`
5. Select `TriageBot_Demo.ipynb`

---

## 📝 How to Use the Notebook

### Step-by-Step:

1. **Run Cell 1** - Installs dependencies (takes ~30 seconds)
   ```
   !pip install -q langchain langgraph...
   ```

2. **Run Cell 2** - Set your OpenAI API key
   ```python
   os.environ["OPENAI_API_KEY"] = "sk-..."  # ⬅️ EDIT THIS!
   ```
   ⚠️ **IMPORTANT:** Replace `your-openai-api-key-here` with your actual key!

3. **Run Cell 3** - Clones the repository (takes ~5 seconds)
   ```
   !git clone https://github.com/sundas14-png/triagebot.git
   ```

4. **Run Cell 4** - Initializes TriageBot
   ```python
   bot = build_triagebot()
   ```

5. **Run Cell 5 repeatedly** - Chat with TriageBot!
   - Each time you run it, you can send a new message
   - Use the demo messages provided

---

## 🎬 Demo Recording in Colab

### Recommended Messages (in order):

Run Cell 5 four times with these messages:

1. **Message 1:** `Why was I charged a $2 fee?`
   - ✅ Shows: FAQ branch, tool call, review pass

2. **Message 2:** `What's the balance on account 4821?`
   - ✅ Shows: Tool branch, account lookup

3. **Message 3:** `And what was my last transaction?`
   - ✅ Shows: **Session memory** (bonus #2)

4. **Message 4:** `I want a $120 refund on this account.`
   - ✅ Shows: Escalation, ticket creation (bonus #1)

### What to Point Out:

After each response, the notebook shows:
- 📊 **Branch taken** (faq/tool/escalate)
- 🛠️ **Tools called** (with names)
- 🔄 **Redo attempts** (self-review loop)
- ✅ **Review passed** (LLM judge - bonus #3)
- ⚠️ **Escalation** (if applicable)
- 🧠 **Remembered account** (session memory - bonus #2)

---

## 💡 Tips for a Great Demo

### Before Recording:
1. ✅ **Test run first** - Make sure your API key works
2. ✅ **Clear all outputs** - Run → Clear all outputs
3. ✅ **Restart runtime** - Runtime → Restart runtime
4. ✅ **Run cells 1-4** to set up

### During Recording:
1. **Run Cell 5 four times** with the demo messages above
2. **Pause briefly** after each response to let viewers see the trace
3. **Point at the trace details** with your cursor
4. **Narrate what's happening** (see DEMO_SCRIPT.md for exact words)

### Narration Example:
> "This is a general FAQ question, so TriageBot's router chose the **FAQ branch**. 
> You can see it called the `faq_lookup` tool, and the LLM judge **passed** the draft 
> on the first attempt with zero redos."

---

## 🔄 Resetting Between Takes

If you need to re-record, run the **reset cell** to clear session memory:

```python
bot.reset()
```

Or just restart the runtime:
- **Runtime** → **Restart runtime**
- Then run cells 1-4 again

---

## 🎯 What This Demonstrates

### ✅ Core Requirements:
- **Branching** - Router decides path
- **3+ Tools** - FAQ, Account, Refund, Ticket (4 total!)
- **Self-Review Loop** - LLM judge reviews every draft
- **Escalation** - Over-cap refunds never auto-execute

### ✅ All 4 Bonus Points:
1. **4th tool** - `open_ticket`
2. **Session memory** - Remembers last account
3. **LLM judge** - Not hard-coded rules
4. **Streaming** - (shown in Streamlit version, mentioned here)

### ✅ All Notes:
- API keys from environment variables
- Synthetic data only
- Never auto-execute over-cap refunds
- Redo loop capped at 2 attempts

---

## 🐛 Troubleshooting

### "ModuleNotFoundError"
→ Make sure you ran Cell 1 (install dependencies)

### "OPENAI_API_KEY not set"
→ Edit Cell 2 and add your actual API key

### "Repository not found"
→ Make sure you ran Cell 3 (clone repo)

### "TriageBot not found"
→ Make sure you ran Cell 4 (initialize bot)

### Responses are slow
→ Normal! GPT-4o-mini takes 2-5 seconds per response

---

## 📚 Additional Resources

- **GitHub Repo:** https://github.com/sundas14-png/triagebot
- **Demo Script:** See `DEMO_SCRIPT.md` for Section 6 talking points
- **README:** See `README.md` for technical details
- **Deployment:** See `DEPLOYMENT_OPTIONS.md` for Streamlit Cloud setup

---

## 🎬 Alternative: Streamlit Version

For the **full visual experience** with token-by-token streaming (bonus #4):

1. Download the project from GitHub
2. Run locally: `streamlit run streamlit_app.py`
3. Record the web interface

See `DEPLOYMENT_OPTIONS.md` for details.

---

**Your TriageBot is ready to demo! Good luck! 🚀**
