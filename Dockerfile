FROM python:3.10-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Render အတွက် Port ဖွင့်ပေးခြင်း
EXPOSE 10000

# App ကို စတင် Run ခြင်း
CMD ["python", "app.py"]
