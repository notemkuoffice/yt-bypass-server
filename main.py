import os
import io
from fastapi import FastAPI, Query, HTTPException
from fastapi.responses import StreamingResponse
import httpx
import yt_dlp

app = FastAPI()

def get_direct_url(youtube_url: str):
    # Для ТВ-клиента куки не требуются, так как SmartTV API отдает 'best' форматы без nsig
    ydl_opts = {
        'format': 'best',
        'nocheckcertificate': True,
        'verbose': True,
        'no_cookies_to_disk': True,
        # Оставляем строго один SmartTV клиент
        'extractor_args': {
            'youtube': {
                'player_client': ['tv'],
                'skip': ['webpage']
            }
        }
    }
        
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
