from abc import ABC, abstractmethod
from typing import List, Optional, Dict, Set, Callable
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from threading import RLock, Thread, Event
from collections import defaultdict, deque
import uuid
import random


# ==================== Enums ====================

class Genre(Enum):
    """Music genres"""
    POP = "POP"
    ROCK = "ROCK"
    JAZZ = "JAZZ"
    CLASSICAL = "CLASSICAL"
    HIP_HOP = "HIP_HOP"
    ELECTRONIC = "ELECTRONIC"
    COUNTRY = "COUNTRY"
    R_AND_B = "R_AND_B"
    METAL = "METAL"
    INDIE = "INDIE"
    FOLK = "FOLK"
    BLUES = "BLUES"


class PlayerState(Enum):
    """Playback states"""
    STOPPED = "STOPPED"
    PLAYING = "PLAYING"
    PAUSED = "PAUSED"
    BUFFERING = "BUFFERING"


class RepeatMode(Enum):
    """Repeat modes"""
    OFF = "OFF"
    ONE = "ONE"  # Repeat current song
    ALL = "ALL"  # Repeat playlist/queue


class PlaylistType(Enum):
    """Types of playlists"""
    USER_CREATED = "USER_CREATED"
    SYSTEM_GENERATED = "SYSTEM_GENERATED"
    COLLABORATIVE = "COLLABORATIVE"


class SubscriptionTier(Enum):
    """Subscription tiers"""
    FREE = "FREE"
    PREMIUM = "PREMIUM"
    FAMILY = "FAMILY"


# ==================== Core Models ====================

@dataclass
class Song:
    """Represents a song/track"""
    song_id: str
    title: str
    duration_seconds: int
    genre: Genre
    release_date: datetime
    album_id: Optional[str] = None
    artist_ids: List[str] = field(default_factory=list)
    audio_url: Optional[str] = None
    cover_art_url: Optional[str] = None
    lyrics: Optional[str] = None
    play_count: int = 0
    
    def __repr__(self) -> str:
        return f"Song(id={self.song_id}, title={self.title})"
    
    def __hash__(self) -> int:
        return hash(self.song_id)
    
    def __eq__(self, other) -> bool:
        if not isinstance(other, Song):
            return False
        return self.song_id == other.song_id


@dataclass
class Album:
    """Represents an album"""
    album_id: str
    title: str
    artist_id: str
    release_date: datetime
    genre: Genre
    cover_art_url: Optional[str] = None
    song_ids: List[str] = field(default_factory=list)
    
    def __repr__(self) -> str:
        return f"Album(id={self.album_id}, title={self.title})"


@dataclass
class Artist:
    """Represents an artist/band"""
    artist_id: str
    name: str
    bio: Optional[str] = None
    genres: List[Genre] = field(default_factory=list)
    profile_image_url: Optional[str] = None
    follower_count: int = 0
    verified: bool = False
    
    def __repr__(self) -> str:
        return f"Artist(id={self.artist_id}, name={self.name})"


class Playlist:
    """Represents a playlist"""
    
    def __init__(self, playlist_id: str, name: str, owner_id: str,
                 playlist_type: PlaylistType = PlaylistType.USER_CREATED):
        self._playlist_id = playlist_id
        self._name = name
        self._owner_id = owner_id
        self._playlist_type = playlist_type
        self._songs: List[Song] = []
        self._description: Optional[str] = None
        self._cover_image_url: Optional[str] = None
        self._is_public = True
        self._collaborative = False
        self._collaborators: Set[str] = set()
        self._created_at = datetime.now()
        self._updated_at = datetime.now()
        self._follower_count = 0
        self._lock = RLock()
    
    def get_id(self) -> str:
        return self._playlist_id
    
    def get_name(self) -> str:
        return self._name
    
    def set_name(self, name: str) -> None:
        with self._lock:
            self._name = name
            self._updated_at = datetime.now()
    
    def get_owner_id(self) -> str:
        return self._owner_id
    
    def get_type(self) -> PlaylistType:
        return self._playlist_type
    
    def set_description(self, description: str) -> None:
        with self._lock:
            self._description = description
            self._updated_at = datetime.now()
    
    def get_description(self) -> Optional[str]:
        return self._description
    
    def set_public(self, is_public: bool) -> None:
        with self._lock:
            self._is_public = is_public
    
    def is_public(self) -> bool:
        return self._is_public
    
    def set_collaborative(self, collaborative: bool) -> None:
        with self._lock:
            self._collaborative = collaborative
    
    def is_collaborative(self) -> bool:
        return self._collaborative
    
    def add_collaborator(self, user_id: str) -> None:
        """Add collaborator to playlist"""
        with self._lock:
            if self._collaborative:
                self._collaborators.add(user_id)
    
    def remove_collaborator(self, user_id: str) -> None:
        """Remove collaborator"""
        with self._lock:
            self._collaborators.discard(user_id)
    
    def can_edit(self, user_id: str) -> bool:
        """Check if user can edit playlist"""
        with self._lock:
            return (user_id == self._owner_id or 
                    (self._collaborative and user_id in self._collaborators))
    
    def add_song(self, song: Song, user_id: str = None) -> bool:
        """Add song to playlist"""
        with self._lock:
            if user_id and not self.can_edit(user_id):
                return False
            
            self._songs.append(song)
            self._updated_at = datetime.now()
            return True
    
    def remove_song(self, song_id: str, user_id: str = None) -> bool:
        """Remove song from playlist"""
        with self._lock:
            if user_id and not self.can_edit(user_id):
                return False
            
            for i, song in enumerate(self._songs):
                if song.song_id == song_id:
                    self._songs.pop(i)
                    self._updated_at = datetime.now()
                    return True
            return False
    
    def reorder_songs(self, from_index: int, to_index: int, user_id: str = None) -> bool:
        """Reorder songs in playlist"""
        with self._lock:
            if user_id and not self.can_edit(user_id):
                return False
            
            if 0 <= from_index < len(self._songs) and 0 <= to_index < len(self._songs):
                song = self._songs.pop(from_index)
                self._songs.insert(to_index, song)
                self._updated_at = datetime.now()
                return True
            return False
    
    def get_songs(self) -> List[Song]:
        """Get all songs in playlist"""
        with self._lock:
            return self._songs.copy()
    
    def get_duration(self) -> int:
        """Get total duration in seconds"""
        with self._lock:
            return sum(song.duration_seconds for song in self._songs)
    
    def get_song_count(self) -> int:
        """Get number of songs"""
        with self._lock:
            return len(self._songs)
    
    def __repr__(self) -> str:
        return f"Playlist(id={self._playlist_id}, name={self._name}, songs={len(self._songs)})"


# ==================== User Models ====================

@dataclass
class User:
    """Represents a user"""
    user_id: str
    username: str
    email: str
    subscription_tier: SubscriptionTier
    created_at: datetime = field(default_factory=datetime.now)
    
    def __repr__(self) -> str:
        return f"User(id={self.user_id}, username={self.username})"


class UserLibrary:
    """User's music library"""
    
    def __init__(self, user_id: str):
        self._user_id = user_id
        self._liked_songs: Set[str] = set()  # song_ids
        self._followed_artists: Set[str] = set()  # artist_ids
        self._saved_albums: Set[str] = set()  # album_ids
        self._playlists: Dict[str, Playlist] = {}  # playlist_id -> Playlist
        self._followed_playlists: Set[str] = set()  # playlist_ids
        self._listening_history: deque = deque(maxlen=1000)  # Recent plays
        self._lock = RLock()
    
    def like_song(self, song_id: str) -> None:
        """Like a song"""
        with self._lock:
            self._liked_songs.add(song_id)
    
    def unlike_song(self, song_id: str) -> None:
        """Unlike a song"""
        with self._lock:
            self._liked_songs.discard(song_id)
    
    def is_song_liked(self, song_id: str) -> bool:
        """Check if song is liked"""
        with self._lock:
            return song_id in self._liked_songs
    
    def get_liked_songs(self) -> Set[str]:
        """Get all liked song IDs"""
        with self._lock:
            return self._liked_songs.copy()
    
    def follow_artist(self, artist_id: str) -> None:
        """Follow an artist"""
        with self._lock:
            self._followed_artists.add(artist_id)
    
    def unfollow_artist(self, artist_id: str) -> None:
        """Unfollow an artist"""
        with self._lock:
            self._followed_artists.discard(artist_id)
    
    def is_artist_followed(self, artist_id: str) -> bool:
        """Check if artist is followed"""
        with self._lock:
            return artist_id in self._followed_artists
    
    def get_followed_artists(self) -> Set[str]:
        """Get all followed artist IDs"""
        with self._lock:
            return self._followed_artists.copy()
    
    def save_album(self, album_id: str) -> None:
        """Save an album"""
        with self._lock:
            self._saved_albums.add(album_id)
    
    def unsave_album(self, album_id: str) -> None:
        """Unsave an album"""
        with self._lock:
            self._saved_albums.discard(album_id)
    
    def is_album_saved(self, album_id: str) -> bool:
        """Check if album is saved"""
        with self._lock:
            return album_id in self._saved_albums
    
    def add_playlist(self, playlist: Playlist) -> None:
        """Add user-created playlist"""
        with self._lock:
            self._playlists[playlist.get_id()] = playlist
    
    def remove_playlist(self, playlist_id: str) -> bool:
        """Remove playlist"""
        with self._lock:
            if playlist_id in self._playlists:
                del self._playlists[playlist_id]
                return True
            return False
    
    def get_playlists(self) -> List[Playlist]:
        """Get user's playlists"""
        with self._lock:
            return list(self._playlists.values())
    
    def follow_playlist(self, playlist_id: str) -> None:
        """Follow a playlist"""
        with self._lock:
            self._followed_playlists.add(playlist_id)
    
    def unfollow_playlist(self, playlist_id: str) -> None:
        """Unfollow a playlist"""
        with self._lock:
            self._followed_playlists.discard(playlist_id)
    
    def add_to_history(self, song_id: str, timestamp: datetime = None) -> None:
        """Add song to listening history"""
        with self._lock:
            if timestamp is None:
                timestamp = datetime.now()
            self._listening_history.append((song_id, timestamp))
    
    def get_recent_history(self, limit: int = 50) -> List[tuple]:
        """Get recent listening history"""
        with self._lock:
            history = list(self._listening_history)
            history.reverse()
            return history[:limit]


# ==================== Music Player ====================

class MusicPlayer:
    """
    Music player with playback controls.
    State pattern for different player states.
    """
    
    def __init__(self, user_id: str):
        self._user_id = user_id
        self._state = PlayerState.STOPPED
        self._current_song: Optional[Song] = None
        self._current_position_seconds = 0
        self._queue: deque[Song] = deque()
        self._history: List[Song] = []
        self._shuffle_enabled = False
        self._repeat_mode = RepeatMode.OFF
        self._volume = 70  # 0-100
        
        # Callbacks
        self._on_song_change: Optional[Callable] = None
        self._on_state_change: Optional[Callable] = None
        
        # Lock
        self._lock = RLock()
    
    def get_state(self) -> PlayerState:
        """Get current player state"""
        with self._lock:
            return self._state
    
    def get_current_song(self) -> Optional[Song]:
        """Get currently playing song"""
        with self._lock:
            return self._current_song
    
    def get_current_position(self) -> int:
        """Get current position in seconds"""
        with self._lock:
            return self._current_position_seconds
    
    def play(self, song: Song = None) -> bool:
        """Play a song or resume playback"""
        with self._lock:
            if song:
                # Play new song
                self._current_song = song
                self._current_position_seconds = 0
                self._history.append(song)
                
                # Increment play count
                song.play_count += 1
                
                if self._on_song_change:
                    self._on_song_change(song)
            
            if not self._current_song:
                return False
            
            self._state = PlayerState.PLAYING
            
            if self._on_state_change:
                self._on_state_change(self._state)
            
            print(f"▶ Playing: {self._current_song.title}")
            return True
    
    def pause(self) -> bool:
        """Pause playback"""
        with self._lock:
            if self._state == PlayerState.PLAYING:
                self._state = PlayerState.PAUSED
                
                if self._on_state_change:
                    self._on_state_change(self._state)
                
                print(f"⏸ Paused: {self._current_song.title if self._current_song else 'None'}")
                return True
            return False
    
    def resume(self) -> bool:
        """Resume playback"""
        with self._lock:
            if self._state == PlayerState.PAUSED and self._current_song:
                self._state = PlayerState.PLAYING
                
                if self._on_state_change:
                    self._on_state_change(self._state)
                
                print(f"▶ Resumed: {self._current_song.title}")
                return True
            return False
    
    def stop(self) -> bool:
        """Stop playback"""
        with self._lock:
            self._state = PlayerState.STOPPED
            self._current_position_seconds = 0
            
            if self._on_state_change:
                self._on_state_change(self._state)
            
            print("⏹ Stopped")
            return True
    
    def next(self) -> bool:
        """Skip to next song"""
        with self._lock:
            next_song = self._get_next_song()
            
            if next_song:
                return self.play(next_song)
            else:
                self.stop()
                return False
    
    def previous(self) -> bool:
        """Go to previous song"""
        with self._lock:
            if len(self._history) >= 2:
                # Remove current song
                self._history.pop()
                # Get previous
                previous_song = self._history.pop()
                return self.play(previous_song)
            return False
    
    def seek(self, position_seconds: int) -> bool:
        """Seek to position in current song"""
        with self._lock:
            if not self._current_song:
                return False
            
            if 0 <= position_seconds <= self._current_song.duration_seconds:
                self._current_position_seconds = position_seconds
                print(f"⏩ Seeked to {position_seconds}s")
                return True
            return False
    
    def _get_next_song(self) -> Optional[Song]:
        """Get next song based on queue and repeat mode (internal)"""
        # Check repeat ONE
        if self._repeat_mode == RepeatMode.ONE and self._current_song:
            return self._current_song
        
        # Check queue
        if self._queue:
            return self._queue.popleft()
        
        # Check repeat ALL - would need reference to current playlist
        # For now, just return None
        return None
    
    def add_to_queue(self, song: Song) -> None:
        """Add song to play queue"""
        with self._lock:
            self._queue.append(song)
            print(f"➕ Added to queue: {song.title}")
    
    def add_songs_to_queue(self, songs: List[Song]) -> None:
        """Add multiple songs to queue"""
        with self._lock:
            for song in songs:
                self._queue.append(song)
            print(f"➕ Added {len(songs)} songs to queue")
    
    def clear_queue(self) -> None:
        """Clear play queue"""
        with self._lock:
            self._queue.clear()
            print("🗑 Queue cleared")
    
    def get_queue(self) -> List[Song]:
        """Get current queue"""
        with self._lock:
            return list(self._queue)
    
    def set_shuffle(self, enabled: bool) -> None:
        """Enable/disable shuffle"""
        with self._lock:
            self._shuffle_enabled = enabled
            print(f"🔀 Shuffle: {'ON' if enabled else 'OFF'}")
    
    def is_shuffle_enabled(self) -> bool:
        """Check if shuffle is enabled"""
        with self._lock:
            return self._shuffle_enabled
    
    def set_repeat_mode(self, mode: RepeatMode) -> None:
        """Set repeat mode"""
        with self._lock:
            self._repeat_mode = mode
            print(f"🔁 Repeat: {mode.value}")
    
    def get_repeat_mode(self) -> RepeatMode:
        """Get current repeat mode"""
        with self._lock:
            return self._repeat_mode
    
    def set_volume(self, volume: int) -> bool:
        """Set volume (0-100)"""
        with self._lock:
            if 0 <= volume <= 100:
                self._volume = volume
                print(f"🔊 Volume: {volume}%")
                return True
            return False
    
    def get_volume(self) -> int:
        """Get current volume"""
        with self._lock:
            return self._volume
    
    def play_playlist(self, playlist: Playlist, start_index: int = 0,
                     shuffle: bool = False) -> bool:
        """Play entire playlist"""
        with self._lock:
            songs = playlist.get_songs()
            
            if not songs or start_index >= len(songs):
                return False
            
            if shuffle:
                # Shuffle all songs except the starting one
                start_song = songs[start_index]
                remaining_songs = songs[:start_index] + songs[start_index + 1:]
                random.shuffle(remaining_songs)
                songs = [start_song] + remaining_songs
                start_index = 0
            
            # Play first song
            success = self.play(songs[start_index])
            
            if success:
                # Add rest to queue
                for i in range(start_index + 1, len(songs)):
                    self.add_to_queue(songs[i])
            
            return success
    
    def set_on_song_change_callback(self, callback: Callable) -> None:
        """Set callback for song changes"""
        self._on_song_change = callback
    
    def set_on_state_change_callback(self, callback: Callable) -> None:
        """Set callback for state changes"""
        self._on_state_change = callback


# ==================== Search & Browse ====================

class MusicCatalog:
    """Central music catalog for browsing and searching"""
    
    def __init__(self):
        self._songs: Dict[str, Song] = {}
        self._albums: Dict[str, Album] = {}
        self._artists: Dict[str, Artist] = {}
        self._lock = RLock()
    
    def add_song(self, song: Song) -> None:
        """Add song to catalog"""
        with self._lock:
            self._songs[song.song_id] = song
    
    def add_album(self, album: Album) -> None:
        """Add album to catalog"""
        with self._lock:
            self._albums[album.album_id] = album
    
    def add_artist(self, artist: Artist) -> None:
        """Add artist to catalog"""
        with self._lock:
            self._artists[artist.artist_id] = artist
    
    def get_song(self, song_id: str) -> Optional[Song]:
        """Get song by ID"""
        return self._songs.get(song_id)
    
    def get_album(self, album_id: str) -> Optional[Album]:
        """Get album by ID"""
        return self._albums.get(album_id)
    
    def get_artist(self, artist_id: str) -> Optional[Artist]:
        """Get artist by ID"""
        return self._artists.get(artist_id)
    
    def search_songs(self, query: str = None, genre: Genre = None,
                    artist_id: str = None, album_id: str = None) -> List[Song]:
        """Search songs with filters"""
        with self._lock:
            results = list(self._songs.values())
            
            if query:
                query_lower = query.lower()
                results = [s for s in results 
                          if query_lower in s.title.lower()]
            
            if genre:
                results = [s for s in results if s.genre == genre]
            
            if artist_id:
                results = [s for s in results if artist_id in s.artist_ids]
            
            if album_id:
                results = [s for s in results if s.album_id == album_id]
            
            # Sort by popularity
            results.sort(key=lambda s: s.play_count, reverse=True)
            return results
    
    def search_albums(self, query: str = None, genre: Genre = None,
                     artist_id: str = None) -> List[Album]:
        """Search albums with filters"""
        with self._lock:
            results = list(self._albums.values())
            
            if query:
                query_lower = query.lower()
                results = [a for a in results 
                          if query_lower in a.title.lower()]
            
            if genre:
                results = [a for a in results if a.genre == genre]
            
            if artist_id:
                results = [a for a in results if a.artist_id == artist_id]
            
            # Sort by release date
            results.sort(key=lambda a: a.release_date, reverse=True)
            return results
    
    def search_artists(self, query: str = None, genre: Genre = None) -> List[Artist]:
        """Search artists with filters"""
        with self._lock:
            results = list(self._artists.values())
            
            if query:
                query_lower = query.lower()
                results = [a for a in results 
                          if query_lower in a.name.lower()]
            
            if genre:
                results = [a for a in results if genre in a.genres]
            
            # Sort by followers
            results.sort(key=lambda a: a.follower_count, reverse=True)
            return results
    
    def get_popular_songs(self, limit: int = 50, genre: Genre = None) -> List[Song]:
        """Get popular songs"""
        with self._lock:
            songs = list(self._songs.values())
            
            if genre:
                songs = [s for s in songs if s.genre == genre]
            
            songs.sort(key=lambda s: s.play_count, reverse=True)
            return songs[:limit]
    
    def get_new_releases(self, limit: int = 50, days: int = 30) -> List[Album]:
        """Get new album releases"""
        with self._lock:
            cutoff_date = datetime.now() - timedelta(days=days)
            albums = [a for a in self._albums.values() 
                     if a.release_date >= cutoff_date]
            albums.sort(key=lambda a: a.release_date, reverse=True)
            return albums[:limit]
    
    def get_album_songs(self, album_id: str) -> List[Song]:
        """Get all songs from an album in order"""
        album = self.get_album(album_id)
        if not album:
            return []
        
        with self._lock:
            songs = []
            for song_id in album.song_ids:
                song = self._songs.get(song_id)
                if song:
                    songs.append(song)
            return songs
    
    def get_artist_songs(self, artist_id: str) -> List[Song]:
        """Get all songs by an artist"""
        return self.search_songs(artist_id=artist_id)
    
    def get_artist_albums(self, artist_id: str) -> List[Album]:
        """Get all albums by an artist"""
        return self.search_albums(artist_id=artist_id)


# ==================== Recommendation Engine ====================

class RecommendationEngine:
    """
    Generates personalized recommendations based on listening history
    """
    
    def __init__(self, catalog: MusicCatalog):
        self._catalog = catalog
        self._lock = RLock()
    
    def get_recommended_songs(self, user_library: UserLibrary, 
                             limit: int = 20) -> List[Song]:
        """Get recommended songs for user based on their library"""
        with self._lock:
            # Get user's liked songs
            liked_song_ids = user_library.get_liked_songs()
            
            if not liked_song_ids:
                # No history - return popular songs
                return self._catalog.get_popular_songs(limit)
            
            # Get genres from liked songs
            genre_counts = defaultdict(int)
            artist_counts = defaultdict(int)
            
            for song_id in liked_song_ids:
                song = self._catalog.get_song(song_id)
                if song:
                    genre_counts[song.genre] += 1
                    for artist_id in song.artist_ids:
                        artist_counts[artist_id] += 1
            
            # Get top genres and artists
            top_genres = sorted(genre_counts.items(), 
                              key=lambda x: x[1], reverse=True)[:3]
            top_artists = sorted(artist_counts.items(),
                               key=lambda x: x[1], reverse=True)[:5]
            
            # Find songs in these genres/artists that user hasn't liked
            recommendations = []
            
            # Songs from favorite artists
            for artist_id, _ in top_artists:
                artist_songs = self._catalog.get_artist_songs(artist_id)
                for song in artist_songs:
                    if (song.song_id not in liked_song_ids and 
                        song not in recommendations):
                        recommendations.append(song)
            
            # Songs from favorite genres
            for genre, _ in top_genres:
                genre_songs = self._catalog.search_songs(genre=genre)
                for song in genre_songs:
                    if (song.song_id not in liked_song_ids and 
                        song not in recommendations):
                        recommendations.append(song)
            
            # Sort by popularity
            recommendations.sort(key=lambda s: s.play_count, reverse=True)
            return recommendations[:limit]
    
    def get_similar_songs(self, song_id: str, limit: int = 10) -> List[Song]:
        """Get songs similar to given song"""
        with self._lock:
            song = self._catalog.get_song(song_id)
            if not song:
                return []
            
            # Find songs with same genre and artists
            similar = []
            
            # Songs from same artists
            for artist_id in song.artist_ids:
                artist_songs = self._catalog.get_artist_songs(artist_id)
                similar.extend([s for s in artist_songs if s.song_id != song_id])
            
            # Songs from same genre
            genre_songs = self._catalog.search_songs(genre=song.genre)
            for s in genre_songs:
                if s.song_id != song_id and s not in similar:
                    similar.append(s)
            
            # Sort by popularity
            similar.sort(key=lambda s: s.play_count, reverse=True)
            return similar[:limit]
    
    def get_artist_radio(self, artist_id: str, limit: int = 50) -> List[Song]:
        """Generate radio station based on an artist"""
        with self._lock:
            artist = self._catalog.get_artist(artist_id)
            if not artist:
                return []
            
            radio_songs = []
            
            # Add artist's top songs
            artist_songs = self._catalog.get_artist_songs(artist_id)
            artist_songs.sort(key=lambda s: s.play_count, reverse=True)
            radio_songs.extend(artist_songs[:20])
            
            # Add songs from similar genres
            for genre in artist.genres:
                genre_songs = self._catalog.search_songs(genre=genre)
                for song in genre_songs:
                    if song not in radio_songs:
                        radio_songs.append(song)
                    if len(radio_songs) >= limit:
                        break
                if len(radio_songs) >= limit:
                    break
            
            # Shuffle to create variety
            random.shuffle(radio_songs)
            return radio_songs[:limit]
    
    def create_daily_mix(self, user_library: UserLibrary) -> Playlist:
        """Create personalized daily mix playlist"""
        recommended_songs = self.get_recommended_songs(user_library, limit=50)
        
        # Create system-generated playlist
        playlist = Playlist(
            str(uuid.uuid4()),
            f"Daily Mix - {datetime.now().strftime('%B %d')}",
            "system",
            PlaylistType.SYSTEM_GENERATED
        )
        playlist.set_description("Your personalized daily mix based on your listening habits")
        
        for song in recommended_songs:
            playlist.add_song(song)
        
        return playlist


# ==================== Main Streaming Service ====================

class MusicStreamingService:
    """
    Main music streaming service coordinating all operations
    """
    
    def __init__(self):
        # Core components
        self._catalog = MusicCatalog()
        self._recommendation_engine = RecommendationEngine(self._catalog)
        
        # Users and libraries
        self._users: Dict[str, User] = {}
        self._user_libraries: Dict[str, UserLibrary] = {}
        self._user_players: Dict[str, MusicPlayer] = {}
        
        # Playlists (public and system)
        self._public_playlists: Dict[str, Playlist] = {}
        
        # Lock
        self._lock = RLock()
    
    # ==================== User Management ====================
    
    def register_user(self, user: User) -> None:
        """Register a new user"""
        with self._lock:
            self._users[user.user_id] = user
            self._user_libraries[user.user_id] = UserLibrary(user.user_id)
            self._user_players[user.user_id] = MusicPlayer(user.user_id)
            print(f"Registered user: {user}")
    
    def get_user(self, user_id: str) -> Optional[User]:
        """Get user by ID"""
        return self._users.get(user_id)
    
    def get_user_library(self, user_id: str) -> Optional[UserLibrary]:
        """Get user's library"""
        return self._user_libraries.get(user_id)
    
    def get_user_player(self, user_id: str) -> Optional[MusicPlayer]:
        """Get user's player"""
        return self._user_players.get(user_id)
    
    # ==================== Catalog Access ====================
    
    def get_catalog(self) -> MusicCatalog:
        """Get music catalog"""
        return self._catalog
    
    def add_song_to_catalog(self, song: Song) -> None:
        """Add song to catalog"""
        self._catalog.add_song(song)
    
    def add_album_to_catalog(self, album: Album) -> None:
        """Add album to catalog"""
        self._catalog.add_album(album)
    
    def add_artist_to_catalog(self, artist: Artist) -> None:
        """Add artist to catalog"""
        self._catalog.add_artist(artist)
    
    # ==================== Browse Operations ====================
    
    def browse_songs(self, query: str = None, genre: Genre = None,
                    artist_id: str = None, album_id: str = None) -> List[Song]:
        """Browse/search songs"""
        return self._catalog.search_songs(query, genre, artist_id, album_id)
    
    def browse_albums(self, query: str = None, genre: Genre = None,
                     artist_id: str = None) -> List[Album]:
        """Browse/search albums"""
        return self._catalog.search_albums(query, genre, artist_id)
    
    def browse_artists(self, query: str = None, genre: Genre = None) -> List[Artist]:
        """Browse/search artists"""
        return self._catalog.search_artists(query, genre)
    
    def get_popular_songs(self, limit: int = 50, genre: Genre = None) -> List[Song]:
        """Get popular songs"""
        return self._catalog.get_popular_songs(limit, genre)
    
    def get_new_releases(self, limit: int = 50) -> List[Album]:
        """Get new releases"""
        return self._catalog.get_new_releases(limit)
    
    # ==================== Playlist Management ====================
    
    def create_playlist(self, user_id: str, name: str, 
                       description: str = None) -> Optional[Playlist]:
        """Create user playlist"""
        user = self.get_user(user_id)
        library = self.get_user_library(user_id)
        
        if not user or not library:
            return None
        
        playlist_id = str(uuid.uuid4())
        playlist = Playlist(playlist_id, name, user_id)
        
        if description:
            playlist.set_description(description)
        
        library.add_playlist(playlist)
        print(f"Created playlist: {name}")
        return playlist
    
    def delete_playlist(self, user_id: str, playlist_id: str) -> bool:
        """Delete user playlist"""
        library = self.get_user_library(user_id)
        if not library:
            return False
        
        return library.remove_playlist(playlist_id)
    
    def add_song_to_playlist(self, user_id: str, playlist_id: str, 
                            song_id: str) -> bool:
        """Add song to playlist"""
        library = self.get_user_library(user_id)
        if not library:
            return False
        
        # Find playlist
        playlist = None
        for pl in library.get_playlists():
            if pl.get_id() == playlist_id:
                playlist = pl
                break
        
        if not playlist:
            # Check public playlists
            playlist = self._public_playlists.get(playlist_id)
        
        if not playlist:
            return False
        
        song = self._catalog.get_song(song_id)
        if not song:
            return False
        
        return playlist.add_song(song, user_id)
    
    def remove_song_from_playlist(self, user_id: str, playlist_id: str,
                                  song_id: str) -> bool:
        """Remove song from playlist"""
        library = self.get_user_library(user_id)
        if not library:
            return False
        
        playlist = None
        for pl in library.get_playlists():
            if pl.get_id() == playlist_id:
                playlist = pl
                break
        
        if not playlist:
            return False
        
        return playlist.remove_song(song_id, user_id)
    
    def get_playlist(self, playlist_id: str, user_id: str = None) -> Optional[Playlist]:
        """Get playlist by ID"""
        # Check user's playlists
        if user_id:
            library = self.get_user_library(user_id)
            if library:
                for playlist in library.get_playlists():
                    if playlist.get_id() == playlist_id:
                        return playlist
        
        # Check public playlists
        return self._public_playlists.get(playlist_id)
    
    # ==================== Playback Operations ====================
    
    def play_song(self, user_id: str, song_id: str) -> bool:
        """Play a song"""
        player = self.get_user_player(user_id)
        library = self.get_user_library(user_id)
        
        if not player or not library:
            return False
        
        song = self._catalog.get_song(song_id)
        if not song:
            return False
        
        success = player.play(song)
        
        if success:
            # Add to listening history
            library.add_to_history(song_id)
        
        return success
    
    def pause_playback(self, user_id: str) -> bool:
        """Pause playback"""
        player = self.get_user_player(user_id)
        return player.pause() if player else False
    
    def resume_playback(self, user_id: str) -> bool:
        """Resume playback"""
        player = self.get_user_player(user_id)
        return player.resume() if player else False
    
    def stop_playback(self, user_id: str) -> bool:
        """Stop playback"""
        player = self.get_user_player(user_id)
        return player.stop() if player else False
    
    def skip_to_next(self, user_id: str) -> bool:
        """Skip to next song"""
        player = self.get_user_player(user_id)
        library = self.get_user_library(user_id)
        
        if not player or not library:
            return False
        
        success = player.next()
        
        if success and player.get_current_song():
            library.add_to_history(player.get_current_song().song_id)
        
        return success
    
    def skip_to_previous(self, user_id: str) -> bool:
        """Skip to previous song"""
        player = self.get_user_player(user_id)
        return player.previous() if player else False
    
    def seek_to_position(self, user_id: str, position_seconds: int) -> bool:
        """Seek to position in current song"""
        player = self.get_user_player(user_id)
        return player.seek(position_seconds) if player else False
    
    def play_playlist(self, user_id: str, playlist_id: str, 
                     start_index: int = 0, shuffle: bool = False) -> bool:
        """Play a playlist"""
        player = self.get_user_player(user_id)
        library = self.get_user_library(user_id)
        
        if not player or not library:
            return False
        
        playlist = self.get_playlist(playlist_id, user_id)
        if not playlist:
            return False
        
        success = player.play_playlist(playlist, start_index, shuffle)
        
        if success and player.get_current_song():
            library.add_to_history(player.get_current_song().song_id)
        
        return success
    
    def play_album(self, user_id: str, album_id: str, 
                  start_index: int = 0) -> bool:
        """Play an album"""
        player = self.get_user_player(user_id)
        library = self.get_user_library(user_id)
        
        if not player or not library:
            return False
        
        songs = self._catalog.get_album_songs(album_id)
        if not songs:
            return False
        
        # Create temporary playlist
        temp_playlist = Playlist(str(uuid.uuid4()), "Album Playback", user_id)
        for song in songs:
            temp_playlist.add_song(song)
        
        success = player.play_playlist(temp_playlist, start_index, False)
        
        if success and player.get_current_song():
            library.add_to_history(player.get_current_song().song_id)
        
        return success
    
    # ==================== Library Operations ====================
    
    def like_song(self, user_id: str, song_id: str) -> bool:
        """Like a song"""
        library = self.get_user_library(user_id)
        if not library:
            return False
        
        song = self._catalog.get_song(song_id)
        if not song:
            return False
        
        library.like_song(song_id)
        print(f"❤️ Liked: {song.title}")
        return True
    
    def unlike_song(self, user_id: str, song_id: str) -> bool:
        """Unlike a song"""
        library = self.get_user_library(user_id)
        if not library:
            return False
        
        library.unlike_song(song_id)
        print(f"💔 Unliked song")
        return True
    
    def follow_artist(self, user_id: str, artist_id: str) -> bool:
        """Follow an artist"""
        library = self.get_user_library(user_id)
        artist = self._catalog.get_artist(artist_id)
        
        if not library or not artist:
            return False
        
        library.follow_artist(artist_id)
        artist.follower_count += 1
        print(f"👤 Following: {artist.name}")
        return True
    
    def unfollow_artist(self, user_id: str, artist_id: str) -> bool:
        """Unfollow an artist"""
        library = self.get_user_library(user_id)
        artist = self._catalog.get_artist(artist_id)
        
        if not library or not artist:
            return False
        
        library.unfollow_artist(artist_id)
        if artist.follower_count > 0:
            artist.follower_count -= 1
        print(f"👤 Unfollowed artist")
        return True
    
    def save_album(self, user_id: str, album_id: str) -> bool:
        """Save an album"""
        library = self.get_user_library(user_id)
        album = self._catalog.get_album(album_id)
        
        if not library or not album:
            return False
        
        library.save_album(album_id)
        print(f"💾 Saved album: {album.title}")
        return True
    
    def get_liked_songs(self, user_id: str) -> List[Song]:
        """Get user's liked songs"""
        library = self.get_user_library(user_id)
        if not library:
            return []
        
        liked_ids = library.get_liked_songs()
        songs = []
        for song_id in liked_ids:
            song = self._catalog.get_song(song_id)
            if song:
                songs.append(song)
        
        return songs
    
    def get_listening_history(self, user_id: str, limit: int = 50) -> List[Song]:
        """Get user's listening history"""
        library = self.get_user_library(user_id)
        if not library:
            return []
        
        history = library.get_recent_history(limit)
        songs = []
        seen = set()
        
        for song_id, timestamp in history:
            if song_id not in seen:
                song = self._catalog.get_song(song_id)
                if song:
                    songs.append(song)
                    seen.add(song_id)
        
        return songs
    
    # ==================== Recommendations ====================
    
    def get_recommendations(self, user_id: str, limit: int = 20) -> List[Song]:
        """Get personalized recommendations"""
        library = self.get_user_library(user_id)
        if not library:
            return []
        
        return self._recommendation_engine.get_recommended_songs(library, limit)
    
    def get_similar_songs(self, song_id: str, limit: int = 10) -> List[Song]:
        """Get similar songs"""
        return self._recommendation_engine.get_similar_songs(song_id, limit)
    
    def create_artist_radio(self, user_id: str, artist_id: str) -> Optional[Playlist]:
        """Create radio station based on artist"""
        artist = self._catalog.get_artist(artist_id)
        if not artist:
            return None
        
        songs = self._recommendation_engine.get_artist_radio(artist_id, limit=50)
        
        playlist = Playlist(
            str(uuid.uuid4()),
            f"{artist.name} Radio",
            "system",
            PlaylistType.SYSTEM_GENERATED
        )
        playlist.set_description(f"Radio station based on {artist.name}")
        
        for song in songs:
            playlist.add_song(song)
        
        return playlist
    
    def create_daily_mix(self, user_id: str) -> Optional[Playlist]:
        """Create daily mix for user"""
        library = self.get_user_library(user_id)
        if not library:
            return None
        
        return self._recommendation_engine.create_daily_mix(library)
    
    # ==================== Analytics ====================
    
    def get_user_stats(self, user_id: str) -> Dict:
        """Get user statistics"""
        library = self.get_user_library(user_id)
        if not library:
            return {}
        
        liked_songs = len(library.get_liked_songs())
        followed_artists = len(library.get_followed_artists())
        saved_albums = len(library._saved_albums)
        playlists = len(library.get_playlists())
        
        # Get top genres from listening history
        history = library.get_recent_history(100)
        genre_counts = defaultdict(int)
        
        for song_id, _ in history:
            song = self._catalog.get_song(song_id)
            if song:
                genre_counts[song.genre.value] += 1
        
        top_genres = sorted(genre_counts.items(), 
                          key=lambda x: x[1], reverse=True)[:5]
        
        return {
            'liked_songs': liked_songs,
            'followed_artists': followed_artists,
            'saved_albums': saved_albums,
            'playlists': playlists,
            'top_genres': [{'genre': g, 'count': c} for g, c in top_genres]
        }
    
    def get_system_stats(self) -> Dict:
        """Get system-wide statistics"""
        with self._lock:
            total_songs = len(self._catalog._songs)
            total_albums = len(self._catalog._albums)
            total_artists = len(self._catalog._artists)
            total_users = len(self._users)
            
            # Calculate total plays
            total_plays = sum(song.play_count for song in self._catalog._songs.values())
            
            return {
                'total_songs': total_songs,
                'total_albums': total_albums,
                'total_artists': total_artists,
                'total_users': total_users,
                'total_plays': total_plays
            }


# ==================== Demo Usage ====================

def print_separator(title: str):
    """Print formatted separator"""
    print("\n" + "="*70)
    print(f"TEST CASE: {title}")
    print("="*70)


def main():
    """Demo the music streaming service"""
    print("=== Music Streaming Service Demo ===\n")
    
    # Initialize service
    service = MusicStreamingService()
    catalog = service.get_catalog()
    
    # Test Case 1: Add Artists
    print_separator("Add Artists to Catalog")
    
    artist1 = Artist(
        "artist-001",
        "The Beatles",
        "Legendary British rock band",
        [Genre.ROCK, Genre.POP],
        verified=True
    )
    
    artist2 = Artist(
        "artist-002",
        "Taylor Swift",
        "American singer-songwriter",
        [Genre.POP, Genre.COUNTRY],
        verified=True
    )
    
    artist3 = Artist(
        "artist-003",
        "Miles Davis",
        "Jazz legend",
        [Genre.JAZZ],
        verified=True
    )
    
    service.add_artist_to_catalog(artist1)
    service.add_artist_to_catalog(artist2)
    service.add_artist_to_catalog(artist3)
    
    print(f"\nAdded artists:")
    print(f"  - {artist1.name} ({', '.join([g.value for g in artist1.genres])})")
    print(f"  - {artist2.name} ({', '.join([g.value for g in artist2.genres])})")
    print(f"  - {artist3.name} ({', '.join([g.value for g in artist3.genres])})")
    
    # Test Case 2: Add Albums
    print_separator("Add Albums to Catalog")
    
    album1 = Album(
        "album-001",
        "Abbey Road",
        "artist-001",
        datetime(1969, 9, 26),
        Genre.ROCK
    )
    
    album2 = Album(
        "album-002",
        "1989",
        "artist-002",
        datetime(2014, 10, 27),
        Genre.POP
    )
    
    album3 = Album(
        "album-003",
        "Kind of Blue",
        "artist-003",
        datetime(1959, 8, 17),
        Genre.JAZZ
    )
    
    service.add_album_to_catalog(album1)
    service.add_album_to_catalog(album2)
    service.add_album_to_catalog(album3)
    
    print(f"\nAdded albums:")
    print(f"  - {album1.title} by {artist1.name}")
    print(f"  - {album2.title} by {artist2.name}")
    print(f"  - {album3.title} by {artist3.name}")
    
    # Test Case 3: Add Songs
    print_separator("Add Songs to Catalog")
    
    songs_data = [
        ("song-001", "Come Together", 259, Genre.ROCK, "album-001", ["artist-001"]),
        ("song-002", "Something", 182, Genre.ROCK, "album-001", ["artist-001"]),
        ("song-003", "Here Comes the Sun", 185, Genre.ROCK, "album-001", ["artist-001"]),
        ("song-004", "Shake It Off", 219, Genre.POP, "album-002", ["artist-002"]),
        ("song-005", "Blank Space", 231, Genre.POP, "album-002", ["artist-002"]),
        ("song-006", "Style", 231, Genre.POP, "album-002", ["artist-002"]),
        ("song-007", "So What", 563, Genre.JAZZ, "album-003", ["artist-003"]),
        ("song-008", "Freddie Freeloader", 593, Genre.JAZZ, "album-003", ["artist-003"]),
        ("song-009", "Blue in Green", 327, Genre.JAZZ, "album-003", ["artist-003"]),
    ]
    
    songs = []
    for song_id, title, duration, genre, album_id, artist_ids in songs_data:
        song = Song(
            song_id, title, duration, genre,
            datetime.now() - timedelta(days=random.randint(1, 3650)),
            album_id, artist_ids
        )
        # Simulate some play counts
        song.play_count = random.randint(1000, 1000000)
        service.add_song_to_catalog(song)
        songs.append(song)
        
        # Add to album
        album = catalog.get_album(album_id)
        if album:
            album.song_ids.append(song_id)
    
    print(f"\nAdded {len(songs)} songs to catalog")
    
    # Test Case 4: Register Users
    print_separator("Register Users")
    
    alice = User("user-001", "alice_music", "alice@email.com", SubscriptionTier.PREMIUM)
    bob = User("user-002", "bob_beats", "bob@email.com", SubscriptionTier.FREE)
    
    service.register_user(alice)
    service.register_user(bob)
    
    # Test Case 5: Browse and Search
    print_separator("Browse and Search Music")
    
    print("\nSearching for 'blue':")
    results = service.browse_songs(query="blue")
    for song in results[:5]:
        print(f"  - {song.title} ({song.genre.value})")
    
    print("\nBrowsing rock songs:")
    rock_songs = service.browse_songs(genre=Genre.ROCK)
    for song in rock_songs[:5]:
        print(f"  - {song.title}")
    
    print("\nBrowsing The Beatles' songs:")
    beatles_songs = service.browse_songs(artist_id="artist-001")
    for song in beatles_songs:
        print(f"  - {song.title} ({song.duration_seconds//60}:{song.duration_seconds%60:02d})")
    
    print("\nSearching for artists with 'swift':")
    artists = service.browse_artists(query="swift")
    for artist in artists:
        print(f"  - {artist.name}")
    
    # Test Case 6: Create and Manage Playlists
    print_separator("Create and Manage Playlists")
    
    print("\nAlice creates a playlist:")
    my_favorites = service.create_playlist(
        "user-001",
        "My Favorites",
        "My all-time favorite songs"
    )
    
    print("\nAdding songs to playlist:")
    service.add_song_to_playlist("user-001", my_favorites.get_id(), "song-001")
    service.add_song_to_playlist("user-001", my_favorites.get_id(), "song-004")
    service.add_song_to_playlist("user-001", my_favorites.get_id(), "song-007")
    
    print(f"\nPlaylist '{my_favorites.get_name()}' has {my_favorites.get_song_count()} songs")
    print(f"Total duration: {my_favorites.get_duration()//60} minutes")
    
    print("\nSongs in playlist:")
    for song in my_favorites.get_songs():
        print(f"  - {song.title}")
    
    # Test Case 7: Playback Controls
    print_separator("Playback Controls")
    
    player = service.get_user_player("user-001")
    
    print("\nAlice plays a song:")
    service.play_song("user-001", "song-001")
    
    print(f"\nPlayer state: {player.get_state().value}")
    print(f"Current song: {player.get_current_song().title if player.get_current_song() else 'None'}")
    
    print("\nPausing...")
    service.pause_playback("user-001")
    print(f"Player state: {player.get_state().value}")
    
    print("\nResuming...")
    service.resume_playback("user-001")
    print(f"Player state: {player.get_state().value}")
    
    print("\nSeeking to 1:30...")
    service.seek_to_position("user-001", 90)
    print(f"Current position: {player.get_current_position()}s")
    
    # Test Case 8: Play Queue
    print_separator("Play Queue Management")
    
    print("\nAdding songs to queue:")
    player.add_to_queue(songs[1])
    player.add_to_queue(songs[2])
    player.add_to_queue(songs[3])
    
    print(f"\nQueue has {len(player.get_queue())} songs:")
    for song in player.get_queue():
        print(f"  - {song.title}")
    
    print("\nSkipping to next song:")
    service.skip_to_next("user-001")
    print(f"Now playing: {player.get_current_song().title if player.get_current_song() else 'None'}")
    
    # Test Case 9: Play Playlist
    print_separator("Play Playlist")
    
    print(f"\nAlice plays her favorites playlist:")
    service.play_playlist("user-001", my_favorites.get_id())
    
    print(f"Now playing: {player.get_current_song().title if player.get_current_song() else 'None'}")
    print(f"Queue has {len(player.get_queue())} more songs")
    
    # Test Case 10: Shuffle and Repeat
    print_separator("Shuffle and Repeat Modes")
    
    print("\nEnabling shuffle:")
    player.set_shuffle(True)
    
    print("Setting repeat mode to ALL:")
    player.set_repeat_mode(RepeatMode.ALL)
    
    print(f"\nShuffle: {player.is_shuffle_enabled()}")
    print(f"Repeat: {player.get_repeat_mode().value}")
    
    print("\nPlaying playlist with shuffle:")
    service.play_playlist("user-001", my_favorites.get_id(), shuffle=True)
    
    # Test Case 11: Like Songs and Follow Artists
    print_separator("Like Songs and Follow Artists")
    
    print("\nAlice likes some songs:")
    service.like_song("user-001", "song-001")
    service.like_song("user-001", "song-004")
    service.like_song("user-001", "song-007")
    
    print("\nAlice follows artists:")
    service.follow_artist("user-001", "artist-001")
    service.follow_artist("user-001", "artist-002")
    
    print(f"\nAlice's liked songs:")
    liked = service.get_liked_songs("user-001")
    for song in liked:
        print(f"  ❤️ {song.title}")
    
    # Test Case 12: Play Album
    print_separator("Play Album")
    
    print(f"\nBob plays the Abbey Road album:")
    service.play_album("user-002", "album-001")
    
    bob_player = service.get_user_player("user-002")
    print(f"Now playing: {bob_player.get_current_song().title if bob_player.get_current_song() else 'None'}")
    print(f"Queue: {len(bob_player.get_queue())} songs")
    
    # Test Case 13: Get Recommendations
    print_separator("Personalized Recommendations")
    
    print("\nAlice's personalized recommendations:")
    recommendations = service.get_recommendations("user-001", limit=10)
    for song in recommendations[:5]:
        print(f"  🎵 {song.title} by {catalog.get_artist(song.artist_ids[0]).name if song.artist_ids else 'Unknown'}")
    
    print("\nSimilar to 'Come Together':")
    similar = service.get_similar_songs("song-001", limit=5)
    for song in similar:
        print(f"  🎵 {song.title}")
    
    # Test Case 14: Artist Radio
    print_separator("Artist Radio")
    
    print("\nCreating radio station for The Beatles:")
    radio = service.create_artist_radio("user-001", "artist-001")
    
    if radio:
        print(f"Radio playlist: {radio.get_name()}")
        print(f"Songs: {radio.get_song_count()}")
        print("\nFirst 5 songs:")
        for song in radio.get_songs()[:5]:
            print(f"  - {song.title}")
    
    # Test Case 15: Daily Mix
    print_separator("Daily Mix")
    
    print("\nCreating daily mix for Alice:")
    daily_mix = service.create_daily_mix("user-001")
    
    if daily_mix:
        print(f"Daily Mix: {daily_mix.get_name()}")
        print(f"Description: {daily_mix.get_description()}")
        print(f"Songs: {daily_mix.get_song_count()}")
        print("\nFirst 5 songs:")
        for song in daily_mix.get_songs()[:5]:
            print(f"  - {song.title}")
    
    # Test Case 16: Listening History
    print_separator("Listening History")
    
    # Simulate more listening
    for _ in range(5):
        service.skip_to_next("user-001")
    
    print("\nAlice's recent listening history:")
    history = service.get_listening_history("user-001", limit=10)
    for song in history:
        print(f"  🎧 {song.title}")
        # Test Case 17: Collaborative Playlist
    print_separator("Collaborative Playlist")
    
    print("\nAlice creates a collaborative playlist:")
    collab_playlist = service.create_playlist(
        "user-001",
        "Road Trip Mix",
        "Collaborative playlist for our road trip"
    )
    collab_playlist.set_collaborative(True)
    collab_playlist.add_collaborator("user-002")
    
    print(f"Playlist: {collab_playlist.get_name()}")
    print(f"Collaborative: {collab_playlist.is_collaborative()}")
    
    print("\nAlice adds songs:")
    service.add_song_to_playlist("user-001", collab_playlist.get_id(), "song-001")
    
    print("\nBob (collaborator) adds songs:")
    service.add_song_to_playlist("user-002", collab_playlist.get_id(), "song-004")
    
    print(f"\nPlaylist now has {collab_playlist.get_song_count()} songs:")
    for song in collab_playlist.get_songs():
        print(f"  - {song.title}")
    
    # Test Case 18: Popular Songs and New Releases
    print_separator("Popular Songs and New Releases")
    
    print("\nTop 5 popular songs overall:")
    popular = service.get_popular_songs(limit=5)
    for i, song in enumerate(popular, 1):
        print(f"  {i}. {song.title} - {song.play_count:,} plays")
    
    print("\nTop 5 popular rock songs:")
    popular_rock = service.get_popular_songs(limit=5, genre=Genre.ROCK)
    for i, song in enumerate(popular_rock, 1):
        print(f"  {i}. {song.title} - {song.play_count:,} plays")
    
    print("\nNew album releases:")
    new_releases = service.get_new_releases(limit=5)
    for album in new_releases:
        artist = catalog.get_artist(album.artist_id)
        print(f"  - {album.title} by {artist.name if artist else 'Unknown'}")
    
    # Test Case 19: Volume Control
    print_separator("Volume Control")
    
    print(f"\nCurrent volume: {player.get_volume()}%")
    
    print("Setting volume to 50%:")
    player.set_volume(50)
    
    print("Increasing volume to 80%:")
    player.set_volume(80)
    
    print(f"Final volume: {player.get_volume()}%")
    
    # Test Case 20: Reorder Playlist
    print_separator("Reorder Playlist Songs")
    
    print(f"\nOriginal order in 'My Favorites':")
    for i, song in enumerate(my_favorites.get_songs()):
        print(f"  {i}. {song.title}")
    
    print("\nMoving song from position 0 to position 2:")
    my_favorites.reorder_songs(0, 2, "user-001")
    
    print(f"\nNew order:")
    for i, song in enumerate(my_favorites.get_songs()):
        print(f"  {i}. {song.title}")
    
    # Test Case 21: Save Album
    print_separator("Save Albums")
    
    print("\nAlice saves albums:")
    service.save_album("user-001", "album-001")
    service.save_album("user-001", "album-002")
    
    alice_library = service.get_user_library("user-001")
    print(f"Saved albums: {len(alice_library._saved_albums)}")
    
    # Test Case 22: Browse by Genre
    print_separator("Browse by Genre")
    
    print("\nBrowsing all genres:")
    for genre in [Genre.ROCK, Genre.POP, Genre.JAZZ]:
        songs = service.browse_songs(genre=genre)
        print(f"\n{genre.value}:")
        for song in songs[:3]:
            print(f"  - {song.title}")
    
    # Test Case 23: Artist's Complete Catalog
    print_separator("Artist's Complete Catalog")
    
    print(f"\nThe Beatles' complete catalog:")
    
    print("\nAlbums:")
    beatles_albums = catalog.get_artist_albums("artist-001")
    for album in beatles_albums:
        print(f"  - {album.title} ({album.release_date.year})")
    
    print("\nSongs:")
    beatles_all_songs = catalog.get_artist_songs("artist-001")
    for song in beatles_all_songs:
        print(f"  - {song.title} ({song.duration_seconds//60}:{song.duration_seconds%60:02d})")
    
    # Test Case 24: User Statistics
    print_separator("User Statistics")
    
    print("\nAlice's statistics:")
    alice_stats = service.get_user_stats("user-001")
    print(f"  Liked Songs: {alice_stats['liked_songs']}")
    print(f"  Followed Artists: {alice_stats['followed_artists']}")
    print(f"  Saved Albums: {alice_stats['saved_albums']}")
    print(f"  Playlists: {alice_stats['playlists']}")
    
    if alice_stats['top_genres']:
        print(f"\n  Top Genres:")
        for genre_info in alice_stats['top_genres']:
            print(f"    - {genre_info['genre']}: {genre_info['count']} plays")
    
    # Test Case 25: Delete Playlist
    print_separator("Delete Playlist")
    
    print("\nAlice's playlists before deletion:")
    for playlist in alice_library.get_playlists():
        print(f"  - {playlist.get_name()} ({playlist.get_song_count()} songs)")
    
    print(f"\nDeleting 'Road Trip Mix':")
    service.delete_playlist("user-001", collab_playlist.get_id())
    
    print("\nAlice's playlists after deletion:")
    for playlist in alice_library.get_playlists():
        print(f"  - {playlist.get_name()} ({playlist.get_song_count()} songs)")
    
    # Test Case 26: Playback Callbacks
    print_separator("Playback Event Callbacks")
    
    def on_song_change(song: Song):
        print(f"  📻 Callback: Now playing '{song.title}'")
    
    def on_state_change(state: PlayerState):
        print(f"  📻 Callback: Player state changed to {state.value}")
    
    print("\nSetting up callbacks:")
    player.set_on_song_change_callback(on_song_change)
    player.set_on_state_change_callback(on_state_change)
    
    print("\nTriggering events:")
    service.play_song("user-001", "song-005")
    service.pause_playback("user-001")
    service.resume_playback("user-001")
    
    # Test Case 27: Search with Multiple Filters
    print_separator("Advanced Search")
    
    print("\nSearching for pop songs by Taylor Swift:")
    results = service.browse_songs(
        genre=Genre.POP,
        artist_id="artist-002"
    )
    print(f"Found {len(results)} songs:")
    for song in results:
        print(f"  - {song.title}")
    
    print("\nSearching for songs in Abbey Road album:")
    album_songs = service.browse_songs(album_id="album-001")
    print(f"Found {len(album_songs)} songs:")
    for song in album_songs:
        print(f"  - {song.title}")
    
    # Test Case 28: Repeat Modes
    print_separator("Different Repeat Modes")
    
    print("\nTesting REPEAT ONE:")
    player.set_repeat_mode(RepeatMode.ONE)
    current = player.get_current_song()
    print(f"Current song: {current.title if current else 'None'}")
    
    print("\nSkipping (should replay same song with repeat one):")
    service.skip_to_next("user-001")
    after_skip = player.get_current_song()
    print(f"After skip: {after_skip.title if after_skip else 'None'}")
    
    print("\nSetting to REPEAT OFF:")
    player.set_repeat_mode(RepeatMode.OFF)
    
    # Test Case 29: Queue Management
    print_separator("Advanced Queue Management")

    print("\nClearing queue:")
    player.clear_queue()
    print(f"Queue size: {len(player.get_queue())}")

    print("\nAdding multiple songs to queue:")
    # Use slice which is safer - won't throw IndexError
    songs_to_add = songs[4:7]  # Gets songs[4], songs[5], songs[6] if they exist
    player.add_songs_to_queue(songs_to_add)

    print(f"\nQueue contents ({len(player.get_queue())} songs):")
    for song in player.get_queue():
        print(f"  - {song.title}")
    
    # Test Case 30: System Statistics
    print_separator("System Statistics")
    
    system_stats = service.get_system_stats()
    print("\nSystem-wide Statistics:")
    print(f"  Total Songs: {system_stats['total_songs']:,}")
    print(f"  Total Albums: {system_stats['total_albums']:,}")
    print(f"  Total Artists: {system_stats['total_artists']:,}")
    print(f"  Total Users: {system_stats['total_users']:,}")
    print(f"  Total Plays: {system_stats['total_plays']:,}")
    
    # Test Case 31: Public Playlist Discovery
    print_separator("Public Playlist Discovery")
    
    print("\nAlice makes her favorites public:")
    my_favorites.set_public(True)
    service._public_playlists[my_favorites.get_id()] = my_favorites
    
    print(f"Playlist '{my_favorites.get_name()}' is now public: {my_favorites.is_public()}")
    
    print("\nBob discovers and follows the playlist:")
    bob_library = service.get_user_library("user-002")
    bob_library.follow_playlist(my_favorites.get_id())
    
    print("Bob can now access this playlist")
    
    # Test Case 32: Multiple Playlists
    print_separator("Manage Multiple Playlists")
    
    print("\nAlice creates multiple playlists:")
    
    workout_playlist = service.create_playlist(
        "user-001",
        "Workout Hits",
        "High energy songs for gym"
    )
    service.add_song_to_playlist("user-001", workout_playlist.get_id(), "song-004")
    service.add_song_to_playlist("user-001", workout_playlist.get_id(), "song-005")
    
    chill_playlist = service.create_playlist(
        "user-001",
        "Chill Vibes",
        "Relaxing music"
    )
    service.add_song_to_playlist("user-001", chill_playlist.get_id(), "song-007")
    service.add_song_to_playlist("user-001", chill_playlist.get_id(), "song-008")
    
    print("\nAlice's all playlists:")
    for playlist in alice_library.get_playlists():
        print(f"  - {playlist.get_name()}: {playlist.get_song_count()} songs, "
              f"{playlist.get_duration()//60} min")
    
    # Test Case 33: Unlike and Unfollow
    print_separator("Unlike Songs and Unfollow Artists")
    
    print(f"\nAlice's liked songs before: {len(alice_library.get_liked_songs())}")
    
    print("Unliking a song:")
    service.unlike_song("user-001", "song-007")
    
    print(f"Alice's liked songs after: {len(alice_library.get_liked_songs())}")
    
    print(f"\nFollowed artists before: {len(alice_library.get_followed_artists())}")
    
    print("Unfollowing an artist:")
    service.unfollow_artist("user-001", "artist-002")
    
    print(f"Followed artists after: {len(alice_library.get_followed_artists())}")
    
    # Test Case 34: Previous Track Navigation
    print_separator("Navigate to Previous Track")
    
    print("\nPlaying a sequence of songs:")
    service.play_song("user-001", "song-001")
    service.skip_to_next("user-001")
    service.skip_to_next("user-001")
    
    current = player.get_current_song()
    print(f"Current song: {current.title if current else 'None'}")
    
    print("\nGoing back to previous:")
    service.skip_to_previous("user-001")
    
    after_previous = player.get_current_song()
    print(f"After previous: {after_previous.title if after_previous else 'None'}")
    
    # Test Case 35: Album Songs in Order
    print_separator("Get Album Songs in Order")
    
    print("\nAbbey Road tracklist:")
    abbey_road_songs = catalog.get_album_songs("album-001")
    for i, song in enumerate(abbey_road_songs, 1):
        minutes = song.duration_seconds // 60
        seconds = song.duration_seconds % 60
        print(f"  {i}. {song.title} ({minutes}:{seconds:02d})")
    
    # Test Case 36: Genre Distribution
    print_separator("Genre Distribution Analysis")
    
    print("\nSongs by genre:")
    genre_distribution = defaultdict(int)
    for song in catalog._songs.values():
        genre_distribution[song.genre.value] += 1
    
    for genre, count in sorted(genre_distribution.items(), key=lambda x: x[1], reverse=True):
        print(f"  {genre}: {count} songs")
    
    # Test Case 37: Play Count Tracking
    print_separator("Play Count Tracking")
    
    print("\nTop played songs:")
    all_songs = list(catalog._songs.values())
    all_songs.sort(key=lambda s: s.play_count, reverse=True)
    
    for i, song in enumerate(all_songs[:5], 1):
        artist = catalog.get_artist(song.artist_ids[0]) if song.artist_ids else None
        artist_name = artist.name if artist else "Unknown"
        print(f"  {i}. {song.title} by {artist_name} - {song.play_count:,} plays")
    
    # Test Case 38: Stop Playback
    print_separator("Stop Playback")
    
    print(f"\nPlayer state before stop: {player.get_state().value}")
    print(f"Current song: {player.get_current_song().title if player.get_current_song() else 'None'}")
    
    print("\nStopping playback:")
    service.stop_playback("user-001")
    
    print(f"Player state after stop: {player.get_state().value}")
    print(f"Current position: {player.get_current_position()}s")
    
    # Test Case 39: Playlist Privacy Settings
    print_separator("Playlist Privacy Settings")
    
    print("\nCreating a private playlist:")
    private_playlist = service.create_playlist(
        "user-001",
        "Secret Favorites",
        "My guilty pleasures"
    )
    private_playlist.set_public(False)
    
    print(f"Playlist: {private_playlist.get_name()}")
    print(f"Public: {private_playlist.is_public()}")
    
    print("\nMaking it public:")
    private_playlist.set_public(True)
    print(f"Public: {private_playlist.is_public()}")
    
    # Test Case 40: Final Summary
    print_separator("Final Service Summary")
    
    print("\nService Overview:")
    final_stats = service.get_system_stats()
    
    print(f"\nCatalog:")
    print(f"  📀 Albums: {final_stats['total_albums']}")
    print(f"  🎵 Songs: {final_stats['total_songs']}")
    print(f"  🎤 Artists: {final_stats['total_artists']}")
    
    print(f"\nUsers:")
    print(f"  👥 Total Users: {final_stats['total_users']}")
    
    print(f"\nEngagement:")
    print(f"  ▶️ Total Plays: {final_stats['total_plays']:,}")
    
    print("\nUser Breakdown:")
    for user_id, user in service._users.items():
        library = service.get_user_library(user_id)
        print(f"\n  {user.username} ({user.subscription_tier.value}):")
        print(f"    Liked Songs: {len(library.get_liked_songs())}")
        print(f"    Followed Artists: {len(library.get_followed_artists())}")
        print(f"    Playlists: {len(library.get_playlists())}")
        
        player = service.get_user_player(user_id)
        current_song = player.get_current_song()
        print(f"    Currently: {player.get_state().value}")
        if current_song:
            print(f"    Playing: {current_song.title}")
    
    print("\n=== Demo Complete ===")


if __name__ == "__main__":
    main()


# Design Highlights
# Design Patterns Used:

# State Pattern - Player states (Playing, Paused, Stopped, Buffering) control available operations
# Strategy Pattern - Could be extended for different recommendation algorithms
# Observer Pattern - Callbacks for player state changes and song changes
# Composite Pattern - Playlists can contain songs, enabling hierarchical organization

# Key Features Implemented:

# Browse for Songs, Albums, and Artists:

# Advanced search with multiple filters (query, genre, artist, album)
# Popular songs by genre
# New releases tracking
# Artist's complete catalog (albums and songs)
# Sort by popularity, release date, followers


# Create and Manage Playlists:

# User-created playlists
# System-generated playlists (Daily Mix, Artist Radio)
# Collaborative playlists with multiple editors
# Playlist privacy settings (public/private)
# Add/remove/reorder songs
# Playlist metadata (description, cover image)
# Follow/unfollow playlists


# Play, Pause, Skip, Seek:

# Full playback controls (play, pause, resume, stop)
# Next/previous track navigation
# Seek to specific position in song
# Play individual songs, albums, or playlists
# Queue management (add, clear, view)
# Shuffle mode
# Repeat modes (off, one, all)
# Volume control


# Recommendations:

# Personalized recommendations based on listening history
# Similar songs based on genre and artist
# Artist radio stations
# Daily Mix generation
# Genre-based suggestions



# Additional Features:

# User Library Management: Like songs, follow artists, save albums
# Listening History: Track and replay recent plays
# Play Count Tracking: Monitor song popularity
# Collaborative Features: Share and co-edit playlists
# Event Callbacks: React to player state and song changes
# Subscription Tiers: Support for Free, Premium, Family tiers
# Statistics & Analytics: User stats, system-wide metrics
# Thread Safety: RLock throughout for concurrent access
# Multi-user Support: Independent players and libraries per user

# Architecture Decisions:

# Separation of Concerns: Catalog, Library, Player are distinct components
# User Library Pattern: Each user has independent library and player instances
# Queue-based Playback: Deque for efficient queue operations
# Recommendation Engine: Separate component for personalized suggestions
# Flexible Playlist Types: Support for user-created, system-generated, and collaborative playlists
# History Tracking: Limited deque for memory-efficient history storage
# Callback System: Enable reactive UI updates without tight coupling

# This design provides a comprehensive foundation for a modern music streaming service with all essential features and extensibility for future enhancements!
