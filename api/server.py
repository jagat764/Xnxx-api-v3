from fastapi import FastAPI, Query
from fastapi.responses import JSONResponse, PlainTextResponse
from fastapi.middleware.cors import CORSMiddleware
import httpx
from bs4 import BeautifulSoup
import re

app = FastAPI(
    title="XNXX Scraper API V3",
    version="3.0"
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"
}


@app.get("/")
async def home():
    return PlainTextResponse("API Running ✅")


# =========================
# 🔍 SEARCH API
# =========================
@app.get("/api/search")
async def search(
    q: str = Query(...),
    page: int = Query(1)
):
    try:
        base_url = "https://www.txnhh.com"
        search_url = f"{base_url}/search/{q.replace(' ', '+')}/{page}"

        async with httpx.AsyncClient(timeout=30) as client:
            r = await client.get(search_url, headers=HEADERS)

        soup = BeautifulSoup(r.text, "html.parser")

        videos = []

        blocks = soup.select("div.mozaique div.thumb-block")

        for block in blocks:
            try:
                a_tag = block.select_one("a[href]")
                img_tag = block.select_one("img")

                # Title
                title = "Untitled"
                if img_tag:
                    title = img_tag.get("alt") or "Untitled"

                # URL
                link = None
                if a_tag and a_tag.get("href"):
                    link = base_url + a_tag.get("href")

                # Thumbnail
                thumb = None
                if img_tag:
                    thumb = img_tag.get("data-src") or img_tag.get("src")

                # Duration
                duration_tag = block.select_one(".duration")
                duration = duration_tag.get_text(strip=True) if duration_tag else None

                # Full text for parsing
                text = block.get_text(" ", strip=True)

                # Views
                views_match = re.search(r"([\d\.]+[MK]?)\s*views", text, re.I)
                views = views_match.group(1) if views_match else None

                # Rating
                rating_match = re.search(r"(\d{1,3}%)", text)
                rating = rating_match.group(1) if rating_match else None

                if link:
                    videos.append({
                        "title": title.strip(),
                        "url": link,
                        "thumbnail": thumb,
                        "views": views,
                        "rating": rating,
                        "duration": duration
                    })

            except Exception:
                continue  # skip broken blocks safely

        return JSONResponse(videos)

    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=500)


# =========================
# 🎬 VIDEO DETAILS API
# =========================
@app.get("/api/video")
async def get_video_details(
    url: str = Query(...)
):
    try:
        async with httpx.AsyncClient(timeout=30) as client:
            r = await client.get(url, headers=HEADERS)

        soup = BeautifulSoup(r.text, "html.parser")

        title = soup.title.string.strip() if soup.title else "Unknown Title"

        video_hd = None
        video_sd = None

        scripts = soup.find_all("script")

        for script in scripts:
            if not script.string:
                continue

            text = script.string

            hd_match = re.search(r"setVideoUrlHigh\('(.*?)'\)", text)
            sd_match = re.search(r"setVideoUrlLow\('(.*?)'\)", text)

            if hd_match:
                video_hd = hd_match.group(1)

            if sd_match:
                video_sd = sd_match.group(1)

        # Duration
        duration_tag = soup.select_one(".duration")
        duration = duration_tag.get_text(strip=True) if duration_tag else None

        if not video_hd and not video_sd:
            return JSONResponse({"error": "Video not found"}, status_code=404)

        return JSONResponse({
            "title": title,
            "duration": duration,
            "video_hd": video_hd,
            "video_sd": video_sd,
            "source": url
        })

    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=500)
