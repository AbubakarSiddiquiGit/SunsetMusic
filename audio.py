import asyncio
from pytubefix import YouTube

class AudioEngine:
    async def extract_stream_url(self, video_id):
        url = f"https://youtube.com/watch?v={video_id}"
        loop = asyncio.get_running_loop()
        try:
            stream_url = await loop.run_in_executor(None, self._extract_info, url)
            return stream_url
        except Exception as e:
            print(f"Error extracting audio stream: {e}")
            return None

    def _extract_info(self, url):
        try:
            yt = YouTube(url, use_po_token=True)
            stream = yt.streams.get_audio_only()
            if stream:
                return stream.url
            return None
        except Exception as e:
            print(f"PyTubeFix Error: {e}")
            return None

audio_engine = AudioEngine()
