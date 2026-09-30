"""Tests for the album and artist filters on the tracks library_items()."""

from __future__ import annotations

from music_assistant_models.media_items import Album, Artist, ProviderMapping, Track, UniqueList

from music_assistant.mass import MusicAssistant


def _mapping(item_id: str) -> ProviderMapping:
    return ProviderMapping(
        item_id=item_id,
        provider_domain="local",
        provider_instance="local_1",
        in_library=True,
        available=True,
    )


async def _add_artist(mass: MusicAssistant, name: str) -> Artist:
    artist = Artist(item_id="0", provider="library", name=name, provider_mappings={_mapping(name)})
    return await mass.music.artists.add_item_to_library(artist)


async def _add_album(mass: MusicAssistant, name: str, artist: Artist) -> Album:
    album = Album(
        item_id="0",
        provider="library",
        name=name,
        provider_mappings={_mapping(name)},
        artists=UniqueList([artist]),
    )
    return await mass.music.albums.add_item_to_library(album)


async def _add_track(
    mass: MusicAssistant, name: str, artist: Artist, album: Album, track_number: int
) -> Track:
    track = Track(
        item_id="0",
        provider="library",
        name=name,
        provider_mappings={_mapping(name)},
        artists=UniqueList([artist]),
        album=album,
        disc_number=1,
        track_number=track_number,
    )
    return await mass.music.tracks.add_item_to_library(track)


async def test_album_filter_returns_whole_album_under_random_order(mass: MusicAssistant) -> None:
    """Every track of the album is returned even with a random order and many other tracks."""
    weird_al = await _add_artist(mass, "Weird Al")
    other = await _add_artist(mass, "Other Artist")
    bad_hair_day = await _add_album(mass, "Bad Hair Day", weird_al)
    other_album = await _add_album(mass, "Other Album", other)
    for number in range(1, 13):
        await _add_track(mass, f"BHD {number}", weird_al, bad_hair_day, number)
    for number in range(1, 31):
        await _add_track(mass, f"Other {number}", other, other_album, number)

    result = await mass.music.tracks.library_items(
        album_ids=[int(bad_hair_day.item_id)], order_by="random", limit=20, summary=False
    )

    assert {t.name for t in result} == {f"BHD {n}" for n in range(1, 13)}


async def test_artist_filter_only_returns_tracks_by_artist(mass: MusicAssistant) -> None:
    """The artist filter matches tracks through the track_artists table."""
    weird_al = await _add_artist(mass, "Weird Al")
    other = await _add_artist(mass, "Other Artist")
    album = await _add_album(mass, "Mixed", weird_al)
    await _add_track(mass, "Al Song", weird_al, album, 1)
    await _add_track(mass, "Other Song", other, album, 2)

    result = await mass.music.tracks.library_items(artist_ids=[int(weird_al.item_id)])

    assert {t.name for t in result} == {"Al Song"}
