import os
from flask import Flask, render_template_string, request, redirect, send_file
from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload, MediaIoBaseDownload
import io

app = Flask(__name__)

# Настройка подключения к Google Drive
SCOPES = ['https://www.googleapis.com/auth/drive']
SERVICE_ACCOUNT_FILE = 'credentials.json'

# Вставь сюда ID папки на Google Диске (из ссылки на папку в браузере)
FOLDER_ID = 'ТВОЙ_ID_ПАПКИ_С_ГУГЛ_ДИСКА'

creds = Credentials.from_service_account_file(SERVICE_ACCOUNT_FILE, scopes=SCOPES)
drive_service = build('drive', 'v3', credentials=creds)

HTML = '''
<!DOCTYPE html>
<html>
<head>
    <title>Мой Диск</title>
    <style>
        body { font-family: sans-serif; background: #121212; color: white; padding: 20px; }
        .card { background: #1e1e1e; padding: 20px; border-radius: 12px; max-width: 600px; margin: auto; }
        ul { list-style: none; padding: 0; }
        li { background: #2a2a2a; margin: 8px 0; padding: 10px; border-radius: 8px; display: flex; justify-content: space-between; }
        a { color: #4da6ff; text-decoration: none; }
        button { background: #007bff; color: white; border: none; padding: 10px 15px; border-radius: 6px; cursor: pointer; }
    </style>
</head>
<body>
    <div class="card">
        <h2>📁 Файлообменник</h2>
        <form action="/upload" method="post" enctype="multipart/form-data">
            <input type="file" name="file" required>
            <button type="submit">Загрузить</button>
        </form>
        <h3>Файлы:</h3>
        <ul>
            {% for file in files %}
            <li>
                <span>{{ file.name }}</span>
                <a href="/download/{{ file.id }}/{{ file.name }}">Скачать</a>
            </li>
            {% endfor %}
        </ul>
    </div>
</body>
</html>
'''

@app.route('/')
def index():
    # Получаем список файлов из папки
    results = drive_service.files().list(
        q=f"'{FOLDER_ID}' in parents and trashed = false",
        fields="files(id, name)"
    ).execute()
    files = results.get('files', [])
    return render_template_string(HTML, files=files)

@app.route('/upload', methods=['POST'])
def upload():
    file = request.files['file']
    if file:
        temp_path = os.path.join('/tmp', file.filename)
        file.save(temp_path)
        
        file_metadata = {'name': file.filename, 'parents': [FOLDER_ID]}
        media = MediaFileUpload(temp_path, resumable=True)
        drive_service.files().create(body=file_metadata, media_body=media, fields='id').execute()
        
        os.remove(temp_path)
    return redirect('/')

@app.route('/download/<file_id>/<filename>')
def download(file_id, filename):
    request_drive = drive_service.files().get_media(fileId=file_id)
    fh = io.BytesIO()
    downloader = MediaIoBaseDownload(fh, request_drive)
    done = False
    while not done:
        _, done = downloader.next_chunk()
    fh.seek(0)
    return send_file(fh, download_name=filename, as_attachment=True)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)