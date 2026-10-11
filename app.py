import os
import time
import gradio as gr
from google import genai

# =========================================================
# 1. Transcript ထုတ်သည့် Function (Streaming ဖြင့် အမြန်ထုတ်ရန်)
# =========================================================
def generate_transcript(api_key, audio_path, language, style):
    if not api_key.strip():
        yield "⚠️ ကျေးဇူးပြု၍ API Key ကို အရင်ထည့်ပေးပါ။"
        return
    if not audio_path:
        yield "⚠️ အသံဖိုင် တင်ပေးရန် သို့မဟုတ် အသံသွင်းပေးရန် လိုအပ်ပါသည်။"
        return

    try:
        client = genai.Client(api_key=api_key.strip())
        
        yield "⏳ အသံဖိုင်ကို တင်နေပါသည် (ခဏစောင့်ပေးပါ)..."
        audio_file = client.files.upload(file=audio_path)
        
        while getattr(audio_file.state, 'name', str(audio_file.state)) == 'PROCESSING':
            time.sleep(2)
            audio_file = client.files.get(name=audio_file.name)
            
        if getattr(audio_file.state, 'name', str(audio_file.state)) == 'FAILED':
            yield "❌ အသံဖိုင် လက်ခံရရှိမှု မအောင်မြင်ပါ။"
            return

        yield "⏳ Transcript စတင် ထုတ်ယူနေပါသည်..."
        
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
        
        response_stream = client.models.generate_content_stream(
            model='gemini-2.5-flash',
            contents=[audio_file, prompt]
        )
        
        full_text = ""
        for chunk in response_stream:
            full_text += chunk.text
            yield full_text
        
        client.files.delete(name=audio_file.name)

    except Exception as e:
        yield f"❌ အမှားအယွင်းဖြစ်ပေါ်နေပါသည်: {str(e)}"

# =========================================================
# 2. Summary အသေးစိတ် ထုတ်သည့် Function
# =========================================================
def summarize_note(api_key, transcript_text, language):
    if not api_key.strip():
        return "⚠️ API Key လိုအပ်ပါသည်။"
    if not transcript_text.strip() or "⚠️" in transcript_text or "❌" in transcript_text:
        return "⚠️ Summarize ပြုလုပ်ရန် Transcript စာသား မရှိသေးပါ။ အရင်ဆုံး Transcript ကို အရင်ထုတ်ပါ။"

    try:
        client = genai.Client(api_key=api_key.strip())
        print("Summary စတင်ထုတ်ယူနေပါသည်...")
        
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
        
        response = client.models.generate_content(
            model='gemini-2.5-flash',
            contents=[prompt]
        )
        
        print("Summary ပြီးစီးပါပြီ။")
        return response.text

    except Exception as e:
        return f"❌ အမှားအယွင်းဖြစ်ပေါ်နေပါသည်: {str(e)}"

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
with gr.Blocks(theme=dark_blue_theme, css=custom_css, title="AI Meeting Notes (Midnight Blue)") as demo:
    
    gr.HTML("""
    <div style="text-align: center; padding: 20px 0 10px 0;">
        <h1 style="color: #FFFFFF; font-weight: 800; font-size: 32px; margin: 0;">
            🎙️ Pro Meeting Assistant
        </h1>
        <p style="color: #94A3B8; font-size: 15px; margin-top: 5px;">
            Offline Record • Smart Transcript • Advanced Summary
        </p>
    </div>
    """)
    
    with gr.Row():
        with gr.Column(scale=4):
            with gr.Group():
                api_key_input = gr.Textbox(
                    label="🔑 API Key",
                    placeholder="AQ.Ab8...",
                    type="password",
                    show_label=True
                )
            
            with gr.Row():
                lang_dropdown = gr.Dropdown(
                    choices=["Myanmar", "English", "Chinese", "Korean", "Japanese", "Malay", "Russian"],
                    value="Myanmar",
                    label="🌐 Language (ဘာသာစကား)",
                    interactive=True
                )
                
                style_dropdown = gr.Dropdown(
                    choices=["Keep original", "Bullet point", "Polished fix"],
                    value="Keep original",
                    label="📝 Format Style",
                    interactive=True
                )
            
            gr.HTML("""
            <div style="color: #94A3B8; font-size: 12px; margin-top: 10px; margin-bottom: 5px;">
                💡 <b>Offline Record:</b> အင်တာနက်မရှိချိန် အသံသွင်းလိုပါက Record နှိပ်ပါ။ ပြီးလျှင် ညာဘက်အပေါ်ရှိ <b>Download (↓)</b> icon ကိုနှိပ်၍ စက်ထဲသိမ်းထားနိုင်ပါသည်။ အင်တာနက်ရမှ ပြန်တင်၍ သုံးနိုင်ပါသည်။
            </div>
            """)
            
            audio_input = gr.Audio(
                label="🎤 Record (or) Upload Audio",
                type="filepath",
                sources=["microphone", "upload"]
            )
            
            transcript_btn = gr.Button("Transcript ထုတ်မည် ⚡", variant="primary", size="lg")
            
        with gr.Column(scale=5):
            gr.Markdown("### 📄 Transcript (မူရင်းစာသား)")
            transcript_output = gr.Textbox(
                label="",
                lines=8,
                placeholder="Transcript ထုတ်မည် ကိုနှိပ်ပါ..."
            )
            
            summarize_btn = gr.Button("✨ Summarize this note", variant="secondary")
            
            gr.Markdown("### 📊 Summary & Action Items")
            summary_output = gr.Textbox(
                label="",
                lines=10,
                placeholder="Summarize နှိပ်ပါက အသေးစိတ်အချက်အလက်များ ဤနေရာတွင် ပေါ်လာပါမည်..."
            )

    transcript_btn.click(
        fn=generate_transcript,
        inputs=[api_key_input, audio_input, lang_dropdown, style_dropdown],
        outputs=transcript_output
    )
    
    summarize_btn.click(
        fn=summarize_note,
        inputs=[api_key_input, transcript_output, lang_dropdown],
        outputs=summary_output
    )

if __name__ == "__main__":
    print("=" * 70)
    print("Starting Pro Meeting Assistant (Midnight Blue Theme)...")
    print("=" * 70)
    
    demo.launch(
        server_name="0.0.0.0", 
        server_port=7860
