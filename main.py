import os
import shutil
from fastapi import FastAPI, Query, HTTPException
from fastapi.responses import StreamingResponse
import httpx
import yt_dlp

app = FastAPI()

def get_direct_url(youtube_url: str):
    # Файл кук, который лежит в корне вашего GitHub репозитория
    repo_cookie_file = "youtube_session.txt"
    # Путь в оперативной памяти Vercel (тут разрешена запись!)
    tmp_cookie_path = "/tmp/active_session_cookies.txt"
    
    # Принудительно копируем файл в RAM перед каждым вызовом yt_dlp
    if os.path.exists(repo_cookie_file):
        try:
            shutil.copyfile(repo_cookie_file, tmp_cookie_path)
            os.chmod(tmp_cookie_path, 0o666)
        except Exception as e:
            print(f"Ошибка копирования кук в RAM: {e}")
            
    ydl_opts = {
        'format': 'b',
        'nocheckcertificate': True,
        'quiet': True
    }
    
    # Скармливаем yt_dlp путь к файлу из папки /tmp/
    if os.path.exists(tmp_cookie_path) and os.path.getsize(tmp_cookie_path) > 0:
        ydl_opts['cookiefile'] = tmp_cookie_path
        
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(youtube_url, download=False)
        return info.get('url')

@app.get("/api/stream")
async def stream_video_api(url: str = Query(...)):
    return await handle_streaming(url)

@app.get("/stream")
@app.get("/")
async def stream_video_root(url: str = Query(...)):
    return await handle_streaming(url)

async def handle_streaming(url: str):
    try:
        direct_url = get_direct_url(url)
        if not direct_url:
            raise HTTPException(status_code=400, detail="Не удалось извлечь ссылку на поток")
            
        async def video_chunk_generator():
            async with httpx.AsyncClient(timeout=60.0) as client:
                async with client.stream("GET", direct_url) as response:
                    async for chunk in response.aiter_bytes(chunk_size=1024 * 64):
                        yield chunk

        return StreamingResponse(video_chunk_generator(), media_type="video/mp4")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
