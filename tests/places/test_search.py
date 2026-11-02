import pytest
import pytest_asyncio


async def search_ids(client, term: str, **extra_params) -> set[str]:
    response = await client.get("/places", params={"search": term, **extra_params})
    assert response.status_code == 200, response.text
    return {item["id"] for item in response.json()}


async def test_search_matches_substring(client, searchable_places):
    ids = await search_ids(client, "park")
    assert ids == {searchable_places["park"], searchable_places["cafe"]}


async def test_search_matches_default_place(client, searchable_places, place_payload):
    ids = await search_ids(client, place_payload["name"])
    assert ids == {searchable_places["default"]}


async def test_search_is_case_insensitive(client, searchable_places):
    assert await search_ids(client, "MUSEUM") == {searchable_places["museum"]}
    assert await search_ids(client, "mUsEuM") == {searchable_places["museum"]}


async def test_search_no_results(client, searchable_places):
    assert await search_ids(client, "does-not-exist") == set()


async def test_search_strips_surrounding_whitespace(client, searchable_places):
    assert await search_ids(client, "  museum  ") == {searchable_places["museum"]}


async def test_search_whitespace_only_is_ignored(client, searchable_places):
    # "   " passes min_length validation, but is stripped to empty -> no filter
    ids = await search_ids(client, "   ")
    assert ids == set(searchable_places.values())


async def test_search_escapes_like_wildcards(client, searchable_places):
    # "%" must be matched literally, not as "match everything"
    assert await search_ids(client, "%") == {searchable_places["discount"]}
    # "_" must be matched literally, not as "any single character"
    assert await search_ids(client, "_") == {searchable_places["underscore"]}


async def test_search_combines_with_pagination(client, searchable_places):
    pages = [
        await client.get(
            "/places", params={"search": "park", "page": page, "page_size": 1}
        )
        for page in (1, 2, 3)
    ]
    assert all(r.status_code == 200 for r in pages)

    first_ids = [item["id"] for item in pages[0].json()]
    second_ids = [item["id"] for item in pages[1].json()]

    assert len(first_ids) == 1
    assert len(second_ids) == 1
    assert set(first_ids + second_ids) == {
        searchable_places["park"],
        searchable_places["cafe"],
    }
    assert pages[2].json() == []


@pytest.mark.parametrize(
    "search",
    ["", "x" * 101],
    ids=["empty", "too_long"],
)
async def test_search_validation(client, search):
    response = await client.get("/places", params={"search": search})
    assert response.status_code == 422
