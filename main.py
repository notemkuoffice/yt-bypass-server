import os
from fastapi import FastAPI, Query, HTTPException
from fastapi.responses import StreamingResponse
import httpx
import yt_dlp

app = FastAPI()

def get_direct_url(youtube_url: str):
    cookie_path = "youtube_session.txt"
    ydl_opts = {
        'format': 'b',
        'nocheckcertificate': True,
        'quiet': True
    }
    if os.path.exists(cookie_path):
        ydl_opts['cookiefile'] = cookie_path
        
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(youtube_url, download=False)
        return info.get('url')

# Вариант 1: Если Vercel передает префикс /api
@app.get("/api/stream")
async def stream_video_api(url: str = Query(...)):
    return await handle_streaming(url)

# Вариант 2: Если Vercel срезает префикс и передает как корень
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
