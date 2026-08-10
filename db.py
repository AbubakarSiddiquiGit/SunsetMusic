from sqlalchemy import create_engine, Column, String, DateTime, ForeignKey, Integer, Table
from sqlalchemy.orm import declarative_base, relationship, sessionmaker
from datetime import datetime

Base = declarative_base()

class Track(Base):
    __tablename__ = 'tracks'
    video_id = Column(String, primary_key=True)
    title = Column(String, nullable=False)
    artist = Column(String, nullable=False)
    thumbnail_url = Column(String)
    
class PlaylistTrack(Base):
    __tablename__ = 'playlist_track'
    playlist_id = Column(Integer, ForeignKey('playlists.id'), primary_key=True)
    track_id = Column(String, ForeignKey('tracks.video_id'), primary_key=True)
    added_at = Column(DateTime, default=datetime.utcnow)
    order_index = Column(Integer, default=0)

class Playlist(Base):
    __tablename__ = 'playlists'
    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String, nullable=False, unique=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    tracks = relationship("Track", secondary="playlist_track", order_by="PlaylistTrack.order_index", backref="playlists")

class ListeningHistory(Base):
    __tablename__ = 'listening_history'
    id = Column(Integer, primary_key=True, autoincrement=True)
    track_id = Column(String, ForeignKey('tracks.video_id'))
    played_at = Column(DateTime, default=datetime.utcnow)
    track = relationship("Track")

class SearchHistory(Base):
    __tablename__ = 'search_history'
    id = Column(Integer, primary_key=True, autoincrement=True)
    query = Column(String, nullable=False)
    searched_at = Column(DateTime, default=datetime.utcnow)

engine = create_engine("sqlite:///music_library.db", echo=False)
Base.metadata.create_all(engine)
SessionLocal = sessionmaker(bind=engine)

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
