FROM python:3.9-slim

# FFmpeg install လုပ်ရန်
RUN apt-get update && apt-get install -y ffmpeg

WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY app.py .

# 7860 Port ကို ဖွင့်ပေးရန်
EXPOSE 7860
ENV GRADIO_SERVER_NAME="0.0.0.0"

CMD ["python", "app.py"] 
