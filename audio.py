import asyncio
import yt_dlp
import httpx
from pytubefix import YouTube

class AudioEngine:
    def __init__(self):
        self.ydl_opts = {
            'format': 'bestaudio[ext=m4a]/bestaudio/best',
            'quiet': True,
            'no_warnings': True,
            'noplaylist': True,
            'extract_flat': False,
            'cookiefile': 'cookies.txt', 
        }
        self.invidious_instances = [
            "https://invidious.jing.rocks",
            "https://vid.puffyan.us",
            "https://invidious.flokinet.to",
            "https://inv.tux.pizza"
        ]

    async def extract_stream_url(self, video_id):
        url = f"https://youtube.com/watch?v={video_id}"
        loop = asyncio.get_running_loop()
        
        # 1. Try pytubefix with ANDROID (bypasses po_token requirement)
        try:
            yt = YouTube(url, client='ANDROID')
            stream = yt.streams.get_audio_only()
            if stream and stream.url:
                return stream.url
        except Exception as e:
            print(f"pytubefix ANDROID failed: {e}")
            
        # 2. Try pytubefix with ANDROID_MUSIC
        try:
            yt = YouTube(url, client='ANDROID_MUSIC')
            stream = yt.streams.get_audio_only()
            if stream and stream.url:
                return stream.url
        except Exception as e:
            print(f"pytubefix ANDROID_MUSIC failed: {e}")

        # 3. Try Invidious API Proxy
        async with httpx.AsyncClient(timeout=10.0, follow_redirects=True) as client:
            for instance in self.invidious_instances:
                try:
                    res = await client.get(f"{instance}/api/v1/videos/{video_id}")
                    if res.status_code == 200:
                        data = res.json()
                        formats = data.get('adaptiveFormats', [])
                        audio_formats = [f for f in formats if f.get('type', '').startswith('audio/')]
                        if audio_formats:
                            return audio_formats[0]['url']
                except Exception as e:
                    print(f"Invidious {instance} failed: {e}")

        # 4. Try yt-dlp (last resort)
        try:
            info = await loop.run_in_executor(None, self._extract_info_yt_dlp, url)
            if info and 'url' in info:
                return info['url']
        except Exception as e:
            print(f"yt-dlp failed: {e}")

        return None

    def _extract_info_yt_dlp(self, url):
        import os
        opts = self.ydl_opts.copy()
        if not os.path.exists('cookies.txt'):
            del opts['cookiefile']
            
        with yt_dlp.YoutubeDL(opts) as ydl:
            return ydl.extract_info(url, download=False)

audio_engine = AudioEngine()
