from fastapi import FastAPI, Depends, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from sqlalchemy import desc
from typing import List, Optional
from pydantic import BaseModel
from datetime import datetime

from db import get_db, Track, Playlist, PlaylistTrack, ListeningHistory, SearchHistory
from metadata import metadata_engine
from audio import audio_engine

app = FastAPI(title="Music API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class TrackModel(BaseModel):
    video_id: str
    title: str
    artist: str
    thumbnail_url: Optional[str] = None

class StreamResponse(BaseModel):
    stream_url: str

def get_or_create_track(db: Session, track: dict):
    db_track = db.query(Track).filter(Track.video_id == track['video_id']).first()
    if not db_track:
        db_track = Track(
            video_id=track['video_id'],
            title=track['title'],
            artist=track['artist'],
            thumbnail_url=track.get('thumbnail_url')
        )
        db.add(db_track)
        db.commit()
    return db_track

@app.get("/api/suggestions")
def get_suggestions(q: str):
    return {"suggestions": metadata_engine.get_search_suggestions(q)}

@app.get("/api/search", response_model=List[TrackModel])
def search_tracks(q: str, db: Session = Depends(get_db)):
    if q:
        # Save to search history
        db_search = SearchHistory(query=q)
        db.add(db_search)
        db.commit()
    return metadata_engine.search(q)

@app.get("/api/stream/{video_id}", response_model=StreamResponse)
async def get_stream_url(video_id: str):
    stream_url = await audio_engine.extract_stream_url(video_id)
    if not stream_url:
        raise HTTPException(status_code=404, detail="Could not extract audio stream")
    return {"stream_url": stream_url}

from fastapi import Request
from fastapi.responses import StreamingResponse
from starlette.background import BackgroundTask
import httpx

@app.get("/api/proxy-stream")
async def proxy_stream(url: str, request: Request):
    headers = {}
    range_header = request.headers.get("range")
    if range_header:
        headers["Range"] = range_header

    client = httpx.AsyncClient()
    req = client.build_request("GET", url, headers=headers)
    response = await client.send(req, stream=True)
    
    resp_headers = {}
    for k in ("content-type", "content-length", "content-range", "accept-ranges"):
        if k in response.headers:
            resp_headers[k] = response.headers[k]

    return StreamingResponse(
        response.aiter_bytes(),
        status_code=response.status_code,
        headers=resp_headers,
        background=BackgroundTask(response.aclose)
    )

@app.get("/api/related/{video_id}", response_model=List[TrackModel])
def get_related(video_id: str):
    return metadata_engine.get_related_songs(video_id)

@app.post("/api/history")
def add_to_history(track: TrackModel, db: Session = Depends(get_db)):
    get_or_create_track(db, track.dict())
    history = ListeningHistory(track_id=track.video_id)
    db.add(history)
    db.commit()
    return {"status": "ok"}

@app.get("/api/history", response_model=List[TrackModel])
def get_history(db: Session = Depends(get_db)):
    histories = db.query(ListeningHistory).order_by(desc(ListeningHistory.played_at)).limit(50).all()
    # Deduplicate while preserving order
    seen = set()
    result = []
    for h in histories:
        if h.track_id not in seen and h.track:
            seen.add(h.track_id)
            result.append(h.track)
    return result

@app.get("/api/search-history")
def get_search_history(db: Session = Depends(get_db)):
    history = db.query(SearchHistory).order_by(desc(SearchHistory.searched_at)).limit(10).all()
    return [h.query for h in history]

# Playlists CRUD
@app.get("/api/playlists")
def get_playlists(db: Session = Depends(get_db)):
    playlists = db.query(Playlist).all()
    return [{"id": p.id, "name": p.name} for p in playlists]

@app.post("/api/playlists")
def create_playlist(name: str, db: Session = Depends(get_db)):
    playlist = Playlist(name=name)
    db.add(playlist)
    db.commit()
    return {"id": playlist.id, "name": playlist.name}

@app.get("/api/liked")
def get_liked_playlist(db: Session = Depends(get_db)):
    playlist = db.query(Playlist).filter(Playlist.name == "Liked Songs").first()
    if not playlist:
        playlist = Playlist(name="Liked Songs")
        db.add(playlist)
        db.commit()
    return {"id": playlist.id, "name": playlist.name}

@app.delete("/api/playlists/{playlist_id}")
def delete_playlist(playlist_id: int, db: Session = Depends(get_db)):
    playlist = db.query(Playlist).filter(Playlist.id == playlist_id).first()
    if playlist:
        db.query(PlaylistTrack).filter(PlaylistTrack.playlist_id == playlist_id).delete()
        db.delete(playlist)
        db.commit()
    return {"status": "ok"}

@app.post("/api/playlists/{playlist_id}/tracks")
def add_track_to_playlist(playlist_id: int, track: TrackModel, db: Session = Depends(get_db)):
    get_or_create_track(db, track.dict())
    
    from sqlalchemy import func
    max_order = db.query(func.max(PlaylistTrack.order_index)).filter_by(playlist_id=playlist_id).scalar()
    new_order = (max_order or 0) + 1
    
    pt = PlaylistTrack(playlist_id=playlist_id, track_id=track.video_id, order_index=new_order)
    db.merge(pt)
    db.commit()
    return {"status": "ok"}

@app.put("/api/playlists/{playlist_id}/tracks/reorder")
def reorder_playlist_tracks(playlist_id: int, track_ids: List[str], db: Session = Depends(get_db)):
    for index, track_id in enumerate(track_ids):
        pt = db.query(PlaylistTrack).filter_by(playlist_id=playlist_id, track_id=track_id).first()
        if pt:
            pt.order_index = index
    db.commit()
    return {"status": "ok"}

@app.get("/api/playlists/{playlist_id}/tracks", response_model=List[TrackModel])
def get_playlist_tracks(playlist_id: int, db: Session = Depends(get_db)):
    playlist = db.query(Playlist).filter(Playlist.id == playlist_id).first()
    if not playlist:
        raise HTTPException(status_code=404, detail="Playlist not found")
    return playlist.tracks

@app.delete("/api/playlists/{playlist_id}/tracks/{video_id}")
def remove_track_from_playlist(playlist_id: int, video_id: str, db: Session = Depends(get_db)):
    pt = db.query(PlaylistTrack).filter_by(playlist_id=playlist_id, track_id=video_id).first()
    if pt:
        db.delete(pt)
        db.commit()
    return {"status": "ok"}
