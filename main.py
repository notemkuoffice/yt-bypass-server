import shutil
import os
import asyncio
from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
import yt_dlp
import requests

app = FastAPI()

# Разрешаем вашей веб-форме делать запросы (CORS)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], 
    allow_methods=["*"],
    allow_headers=["*"],
)

import os
import shutil
import yt_dlp

def get_direct_url(youtube_url: str):
    # Берем загруженный нами на GitHub текстовый файл кук
    repo_cookie_file = "youtube_session.txt"
    # Путь в оперативной памяти Vercel (разрешен на запись)
    tmp_cookie_path = "/tmp/active_session_cookies.txt"
    
    # Принудительно копируем файл в RAM перед вызовом yt_dlp
    if os.path.exists(repo_cookie_file):
        try:
            shutil.copyfile(repo_cookie_file, tmp_cookie_path)
            os.chmod(tmp_cookie_path, 0o666)
        except Exception as e:
            print(f"Ошибка копирования кук: {e}")
            
    ydl_opts = {
        'format': 'b',
        'nocheckcertificate': True,
        'quiet': True
    }
    
    # Скармливаем библиотеке путь из папки /tmp/
    if os.path.exists(tmp_cookie_path) and os.path.getsize(tmp_cookie_path) > 0:
        ydl_opts['cookiefile'] = tmp_cookie_path
        
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(youtube_url, download=False)
        return info.get('url'), info.get('title', 'Video')

@app.get("/api/video-info")
async def video_info(url: str = Query(..., description="YouTube URL")):
    try:
        loop = asyncio.get_event_loop()
        _, title = await loop.run_in_executor(None, get_direct_url, url)
        return {"title": title}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.get("/api/stream")
async def stream_video(url: str = Query(..., description="YouTube URL")):
    try:
        loop = asyncio.get_event_loop()
        direct_url, _ = await loop.run_in_executor(None, get_direct_url, url)
        
        if not direct_url:
            raise HTTPException(status_code=404, detail="Не удалось получить поток")

        def video_generator():
            headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'}
            with requests.get(direct_url, headers=headers, stream=True) as r:
                r.raise_for_status()
                for chunk in r.iter_content(chunk_size=1024 * 64):
                    if chunk:
                        yield chunk

        return StreamingResponse(video_generator(), media_type="video/mp4")

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    import uvicorn
    # Render передает порт в переменных окружения $PORT
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)
