import os
import time
import gradio as gr
from google import genai

# =========================================================
# အရန် Model များ စာရင်း (ပထမတစ်ခု ကျပ်နေလျှင် နောက်တစ်ခု ပြောင်းသုံးမည်)
# =========================================================
MODELS_TO_TRY = [
    "gemini-2.5-flash",
    "gemini-2.5-flash-lite",
    "gemini-2.0-flash"
]

# =========================================================
# 1. Transcript ထုတ်သည့် Function (Auto-Retry + Fallback)
# =========================================================
def generate_transcript(api_key, audio_path, language, style):
    if not api_key.strip():
        yield "⚠️ ကျေးဇူးပြု၍ API Key ကို အရင်ထည့်ပေးပါ။"
        return
    if not audio_path:
        yield "⚠️ အသံဖိုင် တင်ပေးရန် သို့မဟုတ် အသံသွင်းပေးရန် လိုအပ်ပါသည်။"
        return

    client = genai.Client(api_key=api_key.strip())
    audio_file = None

    try:
        yield "⏳ အသံဖိုင်ကို တင်နေပါသည် (ခဏစောင့်ပေးပါ)..."
        audio_file = client.files.upload(file=audio_path)
        
        while getattr(audio_file.state, 'name', str(audio_file.state)) == 'PROCESSING':
            time.sleep(2)
            audio_file = client.files.get(name=audio_file.name)
            
        if getattr(audio_file.state, 'name', str(audio_file.state)) == 'FAILED':
            yield "❌ အသံဖိုင် လက်ခံရရှိမှု မအောင်မြင်ပါ။"
            return

        style_instructions = {
            "Keep original": "Provide an exact, word-for-word transcription of the audio.",
            "Bullet point": "Extract the main ideas and statements from the audio and list them clearly as bullet points.",
            "Polished fix": "Transcribe the audio accurately, but fix any grammatical errors, stutters, or awkward phrasing to make it highly professional and readable."
        }
        
        prompt = (
            "You are an expert transcriptionist and meeting assistant. Listen to the attached audio.\n"
            f"The target language for the output is {language}.\n\n"
            f"Instruction for style: {style_instructions[style]}\n\n"
            f"Please provide the final text clearly in {language}."
        )

        success = False
        last_error = ""

        # Model တစ်ခုချင်းစီကို စမ်းသပ်ခြင်း
        for model_name in MODELS_TO_TRY:
            for attempt in range(2):  # Model တစ်ခုကို ၂ ကြိမ်စီ ကြိုးစားမည်
                try:
                    yield f"⏳ ({model_name}) ဖြင့် Transcript စတင် ထုတ်ယူနေပါသည်..."
                    response_stream = client.models.generate_content_stream(
                        model=model_name,
                        contents=[audio_file, prompt]
                    )
                    
                    full_text = ""
                    for chunk in response_stream:
                        if chunk.text:
                            full_text += chunk.text
                            yield full_text
                    
                    success = True
                    break  # အောင်မြင်သွားရင် Retry Loop မှ ထွက်မည်

                except Exception as e:
                    last_error = str(e)
                    # 503 သို့မဟုတ် Overloaded ဖြစ်နေပါက ၃ စက္ကန့်စောင့်ပြီး ပြန်စမ်းမည်
                    if "503" in last_error or "UNAVAILABLE" in last_error or "overloaded" in last_error.lower():
                        yield f"⚠️ {model_name} လူသုံးများနေပါသည် (High Demand)။ ၃ စက္ကန့်စောင့်ပြီး ပြန်ကြိုးစားနေပါသည်..."
                        time.sleep(3)
                    else:
                        # API Key မှားတာမျိုးဆိုရင် ဆက်မစမ်းဘဲ တန်းရပ်မည်
                        raise e
            
            if success:
                break  # အောင်မြင်သွားရင် Model Loop မှ ထွက်မည်

        if not success:
            yield f"❌ Server များ အားလုံး အလုပ်များနေပါသည်။ ခဏနေမှ ပြန်စမ်းကြည့်ပါ။\nအသေးစိတ်: {last_error}"

    except Exception as e:
        yield f"❌ အမှားအယွင်းဖြစ်ပေါ်နေပါသည်: {str(e)}"
    
    finally:
        # အောင်မြင်သည်ဖြစ်စေ၊ မအောင်မြင်သည်ဖြစ်စေ တင်ထားသော Audio ဖိုင်ကို ပြန်ဖျက်မည်
        if audio_file:
            try:
                client.files.delete(name=audio_file.name)
            except:
                pass

# =========================================================
# 2. Summary အသေးစိတ် ထုတ်သည့် Function (Auto-Retry + Fallback)
# =========================================================
def summarize_note(api_key, transcript_text, language):
    if not api_key.strip():
        return "⚠️ API Key လိုအပ်ပါသည်။"
    if not transcript_text.strip() or "⚠️" in transcript_text or "❌" in transcript_text:
        return "⚠️ Summarize ပြုလုပ်ရန် Transcript စာသား မရှိသေးပါ။ အရင်ဆုံး Transcript ကို အရင်ထုတ်ပါ။"

    client = genai.Client(api_key=api_key.strip())
    prompt = (
        f"Analyze the following meeting transcript/notes and provide a detailed structured breakdown in {language}.\n\n"
        "Format strictly as follows:\n\n"
        "📝 Summary (အကျဉ်းချုပ်)\n"
        "[Provide a concise overview of the entire text]\n\n"
        "✅ To-Do List (လုပ်ဆောင်ရမည့်အရာများ)\n"
        "[List actionable items clearly]\n\n"
        "🎯 Decisions (ဆုံးဖြတ်ချက်များ)\n"
        "[List any key decisions or conclusions made]\n\n"
        "Transcript to analyze:\n"
        f"{transcript_text}"
    )

    last_error = ""
    for model_name in MODELS_TO_TRY:
        for attempt in range(2):
            try:
                print(f"{model_name} ဖြင့် Summary စတင်ထုတ်ယူနေပါသည်...")
                response = client.models.generate_content(
                    model=model_name,
                    contents=[prompt]
                )
                print("Summary ပြီးစီးပါပြီ။")
                return response.text

            except Exception as e:
                last_error = str(e)
                if "503" in last_error or "UNAVAILABLE" in last_error or "overloaded" in last_error.lower():
                    print(f"{model_name} High Demand ဖြစ်နေ၍ ၃ စက္ကန့်စောင့်နေပါသည်...")
                    time.sleep(3)
                else:
                    return f"❌ အမှားအယွင်းဖြစ်ပေါ်နေပါသည်: {last_error}"

    return f"❌ Server များ အားလုံး အလုပ်များနေပါသည်။ ခဏနေမှ ပြန်စမ်းကြည့်ပါ။\nအသေးစိတ်: {last_error}"

# =========================================================
# Dark Blue Theme Setup (Custom Colors)
# =========================================================
dark_blue_theme = gr.themes.Monochrome(
    font=[gr.themes.GoogleFont("Inter"), "system-ui", "sans-serif"],
    radius_size="lg"
).set(
    body_background_fill="#040D21",
    body_background_fill_dark="#040D21",
    block_background_fill="#0A1931",
    block_background_fill_dark="#0A1931",
    block_border_color="#1E3A5F",
    block_border_color_dark="#1E3A5F",
    block_title_text_color="#F8FAFC",
    body_text_color="#F1F5F9",
    body_text_color_dark="#F1F5F9",
    button_primary_background_fill="#2563EB",
    button_primary_background_fill_hover="#1D4ED8",
    button_primary_text_color="#FFFFFF",
    button_secondary_background_fill="#1E3A5F",
    button_secondary_background_fill_hover="#2C5282",
    button_secondary_text_color="#F1F5F9",
    input_background_fill="#0F2544",
    input_background_fill_dark="#0F2544",
)

# =========================================================
# CSS for Dropdown Menu & Form Tabs Visibility Fix
# =========================================================
custom_css = """
.options.svelte-1a86xos, .options.svelte-182teed, ul.options, [role="listbox"] {
    background-color: #0A1931 !important;
    border: 1px solid #1E3A5F !important;
}
.options.svelte-1a86xos .item, ul.options li, [role="option"] {
    color: #F1F5F9 !important;
    background-color: #0A1931 !important;
}
.options.svelte-1a86xos .item:hover, .options.svelte-1a86xos .item.selected, ul.options li:hover, [role="option"]:hover, [role="option"][aria-selected="true"] {
    background-color: #2563EB !important;
    color: #FFFFFF !important;
}
.tabs.svelte-1g805jl, .tab-nav, .tab-nav button, .tab-item, [role="tablist"], [role="tab"] {
    background-color: #0A1931 !important;
    color: #F1F5F9 !important;
    border-color: #1E3A5F !important;
}
.tab-nav button.selected, [role="tab"][aria-selected="true"] {
    background-color: #0F2544 !important;
    border-bottom: 2px solid #2563EB !important;
    color: #FFFFFF !important;
}
select, option, ul, li {
    background-color: #0A1931 !important;
    color: #F1F5F9 !important;
}
"""

# =========================================================
# UI Layout Build & Execution
# =========================================================
with gr.Blocks(theme=dark_blue_theme, css=custom_css, title="Meeting Minutes by Pyae Sone Oo") as demo:
    
    gr.HTML("""
