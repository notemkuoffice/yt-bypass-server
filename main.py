import os
import io
from fastapi import FastAPI, Query, HTTPException
from fastapi.responses import StreamingResponse
import httpx
import yt_dlp

app = FastAPI()

def get_direct_url(youtube_url: str):
    # Прямой массив строк из вашего файла youtube_session.txt
    # (Мы упаковываем структуру Netscape HTTP Cookie прямо в код)
    cookie_data = """# Netscape HTTP Cookie File
.youtube.com\tTRUE\t/\tTRUE\t0\t__Secure-3PSID\tAI96-F0G... (ВАШ ТОКЕН ИЗ ФАЙЛА)
.youtube.com\tTRUE\t/\tTRUE\t0\tLOGIN_INFO\t... (ВАШ ТОКЕН ИЗ ФАЙЛА)
"""
    # Если в коде пока оставим чтение файла, но добавим строгую очистку переносов строки:
    repo_cookie_file = "youtube_session.txt"
    tmp_cookie_path = "/tmp/clean_cookies.txt"
    
    if os.path.exists(repo_cookie_file):
        with open(repo_cookie_file, "r", encoding="utf-8") as rf:
            content = rf.read()
        # Очищаем от Windows-переносов \r\n, которые ломают парсер в Linux на Vercel
        clean_content = content.replace("\r\n", "\n")
        with open(tmp_cookie_path, "w", encoding="utf-8", newline="\n") as wf:
            wf.write(clean_content)

    ydl_opts = {
        'format': 'b',
        'nocheckcertificate': True,
        'quiet': True,
        'no_cookies_to_disk': True
    }
    
    if os.path.exists(tmp_cookie_path):
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
