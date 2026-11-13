"""Database tests for the smart playlist album and artist track lookup."""

from __future__ import annotations

from unittest.mock import MagicMock

from music_assistant_models.enums import AlbumType
from music_assistant_models.media_items import Album, Artist, ProviderMapping, Track
from music_assistant_models.media_items.metadata import MediaItemMetadata
from music_assistant_models.unique_list import UniqueList

from music_assistant.constants import DB_TABLE_ALBUM_TRACKS
from music_assistant.mass import MusicAssistant
from music_assistant.providers.smart_playlist import SmartPlaylistProvider


def _library_mapping() -> set[ProviderMapping]:
    """Return a provider mapping for an item added straight to the library."""
    return {
        ProviderMapping(
            item_id="0", provider_domain="library", provider_instance="library", available=True
        )
    }


async def _add_artist(mass: MusicAssistant, name: str) -> Artist:
    """Add a minimal artist to the library."""
    return await mass.music.artists.add_item_to_library(
        Artist(item_id="0", provider="library", name=name, provider_mappings=_library_mapping())
    )


async def _add_album(mass: MusicAssistant, name: str) -> Album:
    """Add a minimal album to the library."""
    return await mass.music.albums.add_item_to_library(
        Album(
            item_id="0",
            provider="library",
            name=name,
            provider_mappings=_library_mapping(),
            album_type=AlbumType.ALBUM,
        )
    )


async def _add_track(
    mass: MusicAssistant, name: str, artist: Artist, explicit: bool | None = None
) -> Track:
    """Add a minimal track by the given artist to the library."""
    track = Track(
        item_id="0",
        provider="library",
        name=name,
        provider_mappings=_library_mapping(),
        artists=UniqueList([artist]),
        metadata=MediaItemMetadata(explicit=explicit),
    )
    return await mass.music.tracks.add_item_to_library(track)


async def _link(mass: MusicAssistant, album: Album, track: Track, number: int) -> None:
    """Put a track on an album."""
    await mass.music.database.insert(
        DB_TABLE_ALBUM_TRACKS,
        {
            "album_id": int(album.item_id),
            "track_id": int(track.item_id),
            "disc_number": 1,
            "track_number": number,
        },
    )


async def test_linked_tracks_returns_every_album_and_artist_track(
    music_mass: MusicAssistant,
) -> None:
    """All tracks of an album or artist are found, however large the rest of the library is."""
    mass = music_mass
    manifest = MagicMock()
    manifest.domain = "smart_playlist"
    config = MagicMock()
    config.get_value.return_value = "GLOBAL"
    plugin = SmartPlaylistProvider(mass, manifest, config, set())
    weird_al = await _add_artist(mass, "Weird Al")
    other_artist = await _add_artist(mass, "Somebody Else")
    album = await _add_album(mass, "Bad Hair Day")
    compilation = await _add_album(mass, "Greatest Hits")
    album_tracks = [await _add_track(mass, f"Album Track {n}", weird_al) for n in range(17)]
    explicit_track = await _add_track(mass, "Explicit Album Track", weird_al, explicit=True)
    for number, track in enumerate([*album_tracks, explicit_track], start=1):
        await _link(mass, album, track, number)
    # also on a compilation, which may be the album a library listing reports for it
    await _link(mass, compilation, album_tracks[0], 1)
    other_al_track = await _add_track(mass, "Other Weird Al Track", weird_al)
    for n in range(300):
        await _add_track(mass, f"Unrelated Track {n}", other_artist)
    album_ids = {int(t.item_id) for t in [*album_tracks, explicit_track]}

    on_album = await plugin._get_linked_library_tracks([int(album.item_id)], [], match_all=True)
    assert {int(t.item_id) for t in on_album} == album_ids

    clean = await plugin._get_linked_library_tracks(
        [int(album.item_id)], [], match_all=True, explicit=False
    )
    assert {int(t.item_id) for t in clean} == album_ids - {int(explicit_track.item_id)}

    either = await plugin._get_linked_library_tracks(
        [int(album.item_id)], [int(weird_al.item_id)], match_all=False
    )
    assert {int(t.item_id) for t in either} == album_ids | {int(other_al_track.item_id)}

    both = await plugin._get_linked_library_tracks(
        [int(album.item_id)], [int(other_artist.item_id)], match_all=True
    )
    assert both == []
