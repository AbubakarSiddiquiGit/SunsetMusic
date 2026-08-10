from ytmusicapi import YTMusic

class MetadataEngine:
    def __init__(self):
        self.ytmusic = YTMusic()

    def get_search_suggestions(self, query):
        if not query:
            return []
        try:
            suggestions = self.ytmusic.get_search_suggestions(query)
            result = []
            for s in suggestions:
                if isinstance(s, dict) and 'title' in s:
                    result.append(s['title'])
                elif isinstance(s, str):
                    result.append(s)
            return result
        except Exception as e:
            print(f"Error getting suggestions: {e}")
            return []

    def _parse_item(self, item):
        video_id = item.get('videoId')
        title = item.get('title')
        
        artists_list = item.get('artists', [])
        if isinstance(artists_list, list):
            artist_names = [a.get('name') for a in artists_list if a.get('name')]
            artist = ", ".join(artist_names) if artist_names else "Unknown Artist"
        else:
            artist = "Unknown Artist"
            
        thumbnail_url = f"https://i.ytimg.com/vi/{video_id}/hqdefault.jpg" if video_id else None
        
        if video_id and title:
            return {
                'video_id': video_id,
                'title': title,
                'artist': artist,
                'thumbnail_url': thumbnail_url
            }
        return None

    def search(self, query):
        if not query:
            return []
        try:
            results = self.ytmusic.search(query, filter="songs")
            parsed_results = []
            for item in results:
                parsed = self._parse_item(item)
                if parsed:
                    parsed_results.append(parsed)
            return parsed_results
        except Exception as e:
            print(f"Error performing search: {e}")
            return []
            
    def get_related_songs(self, video_id):
        try:
            # get_watch_playlist returns songs related to the video_id (autoplay queue)
            watch_playlist = self.ytmusic.get_watch_playlist(videoId=video_id)
            tracks = watch_playlist.get('tracks', [])
            parsed_results = []
            # Skip the first track as it's the current one
            for item in tracks[1:]:
                parsed = self._parse_item(item)
                if parsed:
                    parsed_results.append(parsed)
            return parsed_results
        except Exception as e:
            print(f"Error fetching related songs: {e}")
            return []

metadata_engine = MetadataEngine()
