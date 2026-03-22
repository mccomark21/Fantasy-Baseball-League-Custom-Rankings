"""
Data caching utilities for Yahoo Fantasy and Baseball Savant data
Handles file-based caching with timestamps for staleness detection
"""
import json
import os
from datetime import datetime, timedelta
from typing import Optional, Dict, List, Any
import logging

logger = logging.getLogger(__name__)


class DataCache:
    """
    File-based cache manager for application data.
    Stores and retrieves data with timestamp tracking.
    """
    
    def __init__(self, cache_dir: str):
        """
        Initialize cache manager.
        
        Args:
            cache_dir: Directory to store cache files (typically data/)
        """
        self.cache_dir = cache_dir
        os.makedirs(cache_dir, exist_ok=True)
    
    def save(
        self,
        key: str,
        data: Any,
        metadata: Optional[Dict] = None
    ) -> bool:
        """
        Save data to cache file.
        
        Args:
            key: Cache key (becomes filename: key.json)
            data: Data to cache
            metadata: Optional dict with additional metadata
        
        Returns:
            True if successful, False otherwise
        """
        try:
            cache_entry = {
                "timestamp": datetime.now().isoformat(),
                "data": data,
                "metadata": metadata or {}
            }
            
            filepath = os.path.join(self.cache_dir, f"{key}.json")
            
            with open(filepath, "w") as f:
                json.dump(cache_entry, f, indent=2, default=str)
            
            logger.info(f"Cache saved: {key}")
            return True
        except Exception as e:
            logger.error(f"Error saving cache {key}: {e}")
            return False
    
    def load(self, key: str) -> Optional[Dict]:
        """
        Load data from cache file.
        
        Args:
            key: Cache key
        
        Returns:
            Dict with "data", "timestamp", "metadata" or None if not found
        """
        try:
            filepath = os.path.join(self.cache_dir, f"{key}.json")
            
            if not os.path.exists(filepath):
                logger.debug(f"Cache not found: {key}")
                return None
            
            with open(filepath, "r") as f:
                cache_entry = json.load(f)
            
            logger.debug(f"Cache loaded: {key}")
            return cache_entry
        except Exception as e:
            logger.error(f"Error loading cache {key}: {e}")
            return None
    
    def is_fresh(
        self,
        key: str,
        max_age_hours: int = 24
    ) -> bool:
        """
        Check if cached data is still fresh.
        
        Args:
            key: Cache key
            max_age_hours: Maximum age in hours (default 24)
        
        Returns:
            True if cache exists and is fresh, False otherwise
        """
        cache_entry = self.load(key)
        
        if cache_entry is None:
            return False
        
        try:
            timestamp_str = cache_entry.get("timestamp")
            if not timestamp_str:
                return False
            
            timestamp = datetime.fromisoformat(timestamp_str)
            age = datetime.now() - timestamp
            max_age = timedelta(hours=max_age_hours)
            
            is_fresh = age < max_age
            logger.debug(f"Cache {key} fresh check: {is_fresh} (age: {age})")
            return is_fresh
        except Exception as e:
            logger.error(f"Error checking freshness of {key}: {e}")
            return False
    
    def get_or_load(
        self,
        key: str,
        fetch_function,
        max_age_hours: int = 24,
        fetch_args: tuple = (),
        fetch_kwargs: dict = None
    ) -> Optional[Any]:
        """
        Get data from cache if fresh, otherwise fetch and cache.
        
        Args:
            key: Cache key
            fetch_function: Function to call if cache is stale
            max_age_hours: Maximum cache age in hours
            fetch_args: Positional arguments for fetch_function
            fetch_kwargs: Keyword arguments for fetch_function
        
        Returns:
            Cached or freshly fetched data, or None if error
        """
        # Check if cache is fresh
        if self.is_fresh(key, max_age_hours):
            cache_entry = self.load(key)
            if cache_entry:
                logger.info(f"Using cached data for {key}")
                return cache_entry["data"]
        
        # Fetch fresh data
        try:
            logger.info(f"Fetching fresh data for {key}")
            if fetch_kwargs is None:
                fetch_kwargs = {}
            
            data = fetch_function(*fetch_args, **fetch_kwargs)
            
            if data is not None:
                self.save(key, data)
                return data
            else:
                logger.warning(f"Fetch function returned None for {key}")
                # Try to return stale cache as fallback
                cache_entry = self.load(key)
                return cache_entry["data"] if cache_entry else None
        except Exception as e:
            logger.error(f"Error fetching data for {key}: {e}")
            # Try to return stale cache as fallback
            cache_entry = self.load(key)
            return cache_entry["data"] if cache_entry else None
    
    def delete(self, key: str) -> bool:
        """
        Delete cache file.
        
        Args:
            key: Cache key
        
        Returns:
            True if successful, False otherwise
        """
        try:
            filepath = os.path.join(self.cache_dir, f"{key}.json")
            
            if os.path.exists(filepath):
                os.remove(filepath)
                logger.info(f"Cache deleted: {key}")
                return True
            
            logger.debug(f"Cache file not found for deletion: {key}")
            return False
        except Exception as e:
            logger.error(f"Error deleting cache {key}: {e}")
            return False
    
    def clear_all(self) -> bool:
        """
        Delete all cache files.
        
        Returns:
            True if successful, False otherwise
        """
        try:
            for filename in os.listdir(self.cache_dir):
                if filename.endswith(".json"):
                    filepath = os.path.join(self.cache_dir, filename)
                    os.remove(filepath)
            
            logger.info("All cache files cleared")
            return True
        except Exception as e:
            logger.error(f"Error clearing all cache: {e}")
            return False
    
    def list_cached_keys(self) -> List[str]:
        """
        List all cached keys.
        
        Returns:
            List of cache keys (filenames without .json)
        """
        try:
            keys = []
            for filename in os.listdir(self.cache_dir):
                if filename.endswith(".json"):
                    keys.append(filename[:-5])  # Remove .json extension
            
            return sorted(keys)
        except Exception as e:
            logger.error(f"Error listing cache keys: {e}")
            return []
    
    def get_cache_info(self, key: str) -> Optional[Dict]:
        """
        Get cache metadata (timestamp, age, etc.).
        
        Args:
            key: Cache key
        
        Returns:
            Dict with metadata or None if not found
        """
        cache_entry = self.load(key)
        
        if cache_entry is None:
            return None
        
        try:
            timestamp_str = cache_entry.get("timestamp")
            timestamp = datetime.fromisoformat(timestamp_str)
            age = datetime.now() - timestamp
            
            return {
                "key": key,
                "timestamp": timestamp_str,
                "age_seconds": int(age.total_seconds()),
                "age_hours": round(age.total_seconds() / 3600, 2),
                "metadata": cache_entry.get("metadata", {})
            }
        except Exception as e:
            logger.error(f"Error getting cache info for {key}: {e}")
            return None


class LeagueCacheManager:
    """
    Specialized cache manager for league and roster data.
    """
    
    def __init__(self, cache: DataCache):
        """
        Initialize league cache manager.
        
        Args:
            cache: DataCache instance
        """
        self.cache = cache
    
    def save_leagues(self, leagues: List[Dict]) -> bool:
        """Save leagues list to cache."""
        return self.cache.save(
            "leagues",
            leagues,
            metadata={"type": "leagues_list"}
        )
    
    def load_leagues(self) -> Optional[List[Dict]]:
        """Load leagues list from cache."""
        cache_entry = self.cache.load("leagues")
        return cache_entry["data"] if cache_entry else None
    
    def save_roster(self, league_id: str, roster: List[Dict]) -> bool:
        """Save roster for specific league."""
        return self.cache.save(
            f"roster_{league_id}",
            roster,
            metadata={
                "type": "league_roster",
                "league_id": league_id
            }
        )
    
    def load_roster(self, league_id: str) -> Optional[List[Dict]]:
        """Load roster for specific league."""
        cache_entry = self.cache.load(f"roster_{league_id}")
        return cache_entry["data"] if cache_entry else None
    
    def save_stats(
        self,
        league_id: str,
        stats: List[Dict],
        date_range: Dict = None
    ) -> bool:
        """Save player stats for league."""
        metadata = {
            "type": "league_stats",
            "league_id": league_id,
            "date_range": date_range or {}
        }
        return self.cache.save(f"stats_{league_id}", stats, metadata)
    
    def load_stats(self, league_id: str) -> Optional[List[Dict]]:
        """Load player stats for league."""
        cache_entry = self.cache.load(f"stats_{league_id}")
        return cache_entry["data"] if cache_entry else None
