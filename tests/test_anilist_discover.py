from trackma.lib.libanilist import libanilist


def make_api(media_type="anime"):
    api = object.__new__(libanilist)
    api.mediatype = media_type
    api.total_str = "episodes" if media_type == "anime" else "chapters"
    api._discover_options_cache = {}
    api.check_credentials = lambda: True
    api._emit_signal = lambda *_args: None
    return api


def media_payload(media_id=1, title="Frieren"):
    return {
        "id": media_id,
        "title": {
            "userPreferred": title,
            "romaji": title,
            "english": title,
            "native": "",
        },
        "coverImage": {"large": "cover-small", "extraLarge": "cover-large", "color": "#89aacc"},
        "format": "TV",
        "averageScore": 88,
        "meanScore": 87,
        "popularity": 1000,
        "favourites": 500,
        "chapters": None,
        "episodes": 28,
        "duration": 24,
        "status": "FINISHED",
        "source": "MANGA",
        "countryOfOrigin": "JP",
        "startDate": {"year": 2023, "month": 9, "day": 29},
        "endDate": {"year": 2024, "month": 3, "day": 22},
        "siteUrl": "https://anilist.co/anime/1",
        "description": "A journey after the adventure.",
        "genres": ["Adventure", "Fantasy"],
        "synonyms": [],
        "studios": {"nodes": [{"name": "Madhouse"}]},
        "seasonYear": 2023,
        "season": "FALL",
        "nextAiringEpisode": None,
        "tags": [{"name": "Elf", "rank": 92, "isMediaSpoiler": False}],
        "externalLinks": [{"site": "Crunchyroll", "url": "https://example.com", "type": "STREAMING"}],
    }


def test_anilist_browse_maps_all_filter_groups_to_graphql_variables():
    api = make_api()
    captured = {}

    def request(query, variables):
        captured["query"] = query
        captured["variables"] = variables
        return {
            "data": {
                "Page": {
                    "pageInfo": {"currentPage": 3, "lastPage": 8, "total": 180, "hasNextPage": True},
                    "media": [media_payload()],
                }
            }
        }

    api._request = request

    result = api.discover_browse(
        {
            "search": "frieren",
            "genres": ["Adventure"],
            "tags": ["Elf"],
            "year": 2023,
            "season": "FALL",
            "formats": ["TV"],
            "statuses": ["FINISHED"],
            "country": "JP",
            "source": "MANGA",
            "streaming": "Crunchyroll",
            "sort": "score",
        },
        page=3,
        per_page=24,
    )

    assert captured["variables"] == {
        "page": 3,
        "perPage": 24,
        "type": "ANIME",
        "search": "frieren",
        "genres": ["Adventure"],
        "tags": ["Elf"],
        "startDate": "2023%",
        "season": "FALL",
        "formats": ["TV"],
        "statuses": ["FINISHED"],
        "country": "JP",
        "sources": ["MANGA"],
        "licensedBy": ["Crunchyroll"],
        "sort": ["SCORE_DESC"],
    }
    assert "genre_in: $genres" in captured["query"]
    assert "licensedBy_in: $licensedBy" in captured["query"]
    assert result["pageInfo"]["lastPage"] == 8
    assert result["items"][0]["_catalog"]["averageScore"] == 88


def test_anilist_home_uses_media_specific_sections():
    anime = make_api("anime")
    manga = make_api("manga")

    def request(_query, _variables):
        page = {
            "pageInfo": {"currentPage": 1, "lastPage": 1, "total": 1, "hasNextPage": False},
            "media": [media_payload()],
        }
        return {
            "data": {
                "trending": page,
                "popularSeason": page,
                "upcomingSeason": page,
                "popular": page,
                "top": page,
                "popularManhwa": page,
            }
        }

    anime._request = request
    manga._request = request

    assert [section["id"] for section in anime.discover_home()["sections"]] == [
        "trending",
        "popular-season",
        "upcoming-season",
        "popular",
        "top",
    ]
    assert [section["id"] for section in manga.discover_home()["sections"]] == [
        "trending",
        "popular",
        "popular-manhwa",
        "top",
    ]


def test_anilist_browse_uses_popularity_when_relevance_has_no_query():
    api = make_api()
    captured = {}

    def request(_query, variables):
        captured["variables"] = variables
        return {
            "data": {
                "Page": {
                    "pageInfo": {"currentPage": 1, "lastPage": 1, "total": 0, "hasNextPage": False},
                    "media": [],
                }
            }
        }

    api._request = request

    api.discover_browse({"sort": "relevance"})

    assert captured["variables"]["sort"] == ["POPULARITY_DESC"]


def test_anilist_options_exclude_adult_and_spoiler_tags():
    api = make_api()
    api._request = lambda _query: {
        "data": {
            "GenreCollection": ["Adventure", "Fantasy"],
            "MediaTagCollection": [
                {"name": "Elf", "category": "Cast-Traits", "isAdult": False},
                {"name": "Plot twist", "category": "Themes", "isAdult": False},
                {"name": "Adult tag", "category": "Sexual Content", "isAdult": True},
            ],
        }
    }

    options = api.discover_options()

    assert options["genres"] == [
        {"value": "Adventure", "label": "Adventure"},
        {"value": "Fantasy", "label": "Fantasy"},
    ]
    assert [item["value"] for item in options["tags"]] == ["Elf", "Plot twist"]
    assert options["streaming"][0]["value"] == "Crunchyroll"


def test_anilist_requested_details_keep_catalog_metadata():
    api = make_api()
    captured = {}

    def request(query, variables):
        captured["query"] = query
        captured["variables"] = variables
        return {"data": {"Media": media_payload()}}

    api._request = request

    details = api.request_info([{"id": 1}])[0]

    assert captured["variables"] == {"id": 1, "type": "ANIME"}
    assert "source" in captured["query"]
    assert details["_catalog"]["season"] == "FALL"
    assert details["_catalog"]["seasonYear"] == 2023
    assert details["_catalog"]["source"] == "MANGA"
