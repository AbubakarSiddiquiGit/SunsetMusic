import asyncio
import yt_dlp

class AudioEngine:
    def __init__(self):
        self.ydl_opts = {
            'format': 'bestaudio[ext=m4a]/bestaudio/best',
            'quiet': True,
            'no_warnings': True,
            'noplaylist': True,
            'extract_flat': False,
        }

    async def extract_stream_url(self, video_id):
        url = f"https://youtube.com/watch?v={video_id}"
        loop = asyncio.get_running_loop()
        try:
            info = await loop.run_in_executor(None, self._extract_info, url)
            if info and 'url' in info:
                return info['url']
            return None
        except Exception as e:
            print(f"Error extracting audio stream: {e}")
            return None

    def _extract_info(self, url):
        # Try Android client first
        opts = self.ydl_opts.copy()
        opts['extractor_args'] = {'youtube': {'player_client': ['android']}}
        try:
            with yt_dlp.YoutubeDL(opts) as ydl:
                return ydl.extract_info(url, download=False)
        except Exception:
            # Fallback to iOS client
            opts['extractor_args'] = {'youtube': {'player_client': ['ios']}}
            try:
                with yt_dlp.YoutubeDL(opts) as ydl:
                    return ydl.extract_info(url, download=False)
            except Exception:
                # Fallback to web client
                opts['extractor_args'] = {'youtube': {'player_client': ['web']}}
                with yt_dlp.YoutubeDL(opts) as ydl:
                    return ydl.extract_info(url, download=False)

audio_engine = AudioEngine()
