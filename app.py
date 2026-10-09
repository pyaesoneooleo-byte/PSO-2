import gradio as gr
import whisper
import os
import datetime
from google import genai
from github import Github

# Model လေးလံမှုကို သက်သာစေရန် 'base' သို့မဟုတ် 'small' ကို သုံးရန် အကြံပြုပါသည် (Cloud Free Tier အတွက်)
print("Whisper Model ကို Load လုပ်နေပါသည်...")
whisper_model = whisper.load_model("base") 

def upload_to_github(github_token, repo_name, file_content, file_name):
    try:
        g = Github(github_token)
        repo = g.get_repo(repo_name)
        commit_message = f"Add new meeting note: {file_name}"
        repo.create_file(file_name, commit_message, file_content, branch="main")
        return f"အောင်မြင်စွာ တင်ပြီးပါပြီ။ ဖိုင်အမည်: {file_name}"
    except Exception as e:
        return f"GitHub သို့ တင်ရာတွင် အမှားအယွင်းဖြစ်နေပါသည်: {str(e)}"

def process_audio(gemini_api_key, github_token, repo_name, audio_file):
    if not gemini_api_key:
        return "Error: Gemini API Key ကို ထည့်ပေးပါ။", ""
    if not audio_file:
        return "Error: အသံဖိုင် တင်ပေးပါ။", ""

    try:
        result = whisper_model.transcribe(audio_file)
        transcript = result["text"]

        prompt = f"""
        အောက်ပါ စာသားများသည် အစည်းအဝေး (သို့မဟုတ်) စာသင်ခန်းမှ အသံဖိုင်ကို စာသားအဖြစ် ပြောင်းထားခြင်း ဖြစ်ပါသည်။ 
        ယင်းစာသားများကို အခြေခံ၍ သပ်ရပ်သော မှတ်တမ်း (Structured Notes) အဖြစ် ပြန်လည်ရေးသားပေးပါ။ 
        မှတ်တမ်းတွင် အောက်ပါအချက်များ ပါဝင်ရမည် -
        ၁။ အကျဉ်းချုပ် (Summary)
        ၂။ အဓိက အချက်အလက်များ (Key Points)
        ၃။ ဆက်လက်လုပ်ဆောင်ရမည့် အချက်များ (Action Items) (ရှိပါက)
        
        မှတ်ချက်။ ။ စာသားသည် မြန်မာဘာသာဖြစ်ပါက မြန်မာဘာသာဖြင့်ပင် သပ်ရပ်စွာ ထုတ်ပေးပါ။ Markdown format ဖြင့်သာ ရေးပေးပါ။

        Transcript:
        {transcript}
        """
        
        client = genai.Client(api_key=gemini_api_key)
        response = client.models.generate_content(
            model='gemini-2.5-flash',
            contents=prompt,
        )
        notes = response.text
        
        github_status = "GitHub သို့ မတင်ပါ။ (Token သို့မဟုတ် Repo အမည် မပါဝင်ပါ)"
        if github_token and repo_name:
            date_str = datetime.datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
            file_name = f"Notes/Meeting_Note_{date_str}.md" 
            github_status = upload_to_github(github_token, repo_name, notes, file_name)

        final_output = f"**GitHub Status:** {github_status}\n\n---\n\n{notes}"
        return transcript, final_output

    except Exception as e:
        return f"အမှားအယွင်းဖြစ်နေပါသည်: {str(e)}", ""

with gr.Blocks(title="Audio to Notes & GitHub") as app:
    gr.Markdown("# 🎙️ Audio to Notes (with GitHub Auto-Upload)")
    
    with gr.Row():
        gemini_input = gr.Textbox(label="🔑 Gemini API Key", type="password")
        github_input = gr.Textbox(label="🐙 GitHub Personal Access Token (Optional)", type="password")
        repo_input = gr.Textbox(label="📂 GitHub Repo (e.g. username/repo-name)", placeholder="yourusername/your-repo-name")
        
    with gr.Row():
        with gr.Column():
            audio_input = gr.Audio(type="filepath", label="အသံဖိုင် တင်ရန် (သို့) အသံသွင်းရန်")
            submit_btn = gr.Button("📝 Notes ထုတ်လုပ်ပြီး GitHub သို့တင်မည်", variant="primary")
        
        with gr.Column():
            notes_output = gr.Markdown(label="ထွက်ပေါ်လာသော Notes များ")
            with gr.Accordion("Transcript (မူရင်းစာသား) ကြည့်ရန်", open=False):
                transcript_output = gr.Textbox(show_label=False, lines=10)

    submit_btn.click(
        fn=process_audio,
        inputs=[gemini_input, github_input, repo_input, audio_input],
        outputs=[transcript_output, notes_output]
    )

app.launch()
