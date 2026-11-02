from uuid import uuid4

import pytest

pytestmark = pytest.mark.asyncio


def ids(response) -> list[str]:
    return [p["id"] for p in response.json()]


async def test_returns_only_places_with_category(
        client, category_cafe, place_cafe, place_park
):
    response = await client.get(
        "/places",
        params={"category_id": str(category_cafe.id)}
    )

    assert response.status_code == 200
    assert ids(response) == [place_cafe["id"]]


@pytest.mark.usefixtures("place_cafe")
async def test_unknown_category_returns_empty_list(client):
    response = await client.get(
        "/places",
        params={"category_id": str(uuid4())}
    )

    assert response.status_code == 200
    assert response.json() == []


async def test_no_filter_returns_all_places(
        client,
        place,
        place_cafe,
        place_park
):
    response = await client.get("/places")

    assert set(ids(response)) == {
        place["id"],
        place_cafe["id"],
        place_park["id"]
    }


async def test_filtered_place_includes_all_its_categories(
        client,
        category_cafe,
        category_park,
        place_cafe_and_park
):
    response = await client.get(
        "/places",
        params={"category_id": str(category_cafe.id)}
    )

    (found,) = response.json()
    assert {c["id"] for c in found["categories"]} == {
        str(category_cafe.id),
        str(category_park.id),
    }


async def test_place_with_multiple_categories_not_duplicated(
        client,
        category_cafe,
        place_cafe_and_park
):
    response = await client.get(
        "/places",
        params={"category_id": str(category_cafe.id)}
    )

    assert ids(response) == [place_cafe_and_park["id"]]


@pytest.mark.usefixtures("place")  # uncategorized
async def test_uncategorized_places_excluded(
        client,
        category_cafe,
        place_cafe
):
    response = await client.get(
        "/places",
        params={"category_id": str(category_cafe.id)}
    )

    assert ids(response) == [place_cafe["id"]]


async def test_place_with_other_categories_only_excluded(
        client,
        category_cafe,
        place_park,
        place_cafe_and_park
):
    response = await client.get(
        "/places",
        params={"category_id": str(category_cafe.id)}
    )

    assert ids(response) == [place_cafe_and_park["id"]]


@pytest.mark.parametrize("value", ["abc", "123", ""])
async def test_invalid_category_id_returns_422(client, value):
    response = await client.get(
        "/places",
        params={"category_id": value}
    )

    assert response.status_code == 422


async def test_combined_with_search(
        client,
        category_cafe,
        place_cafe,
        place_cafe_and_park,
        place_park
):
    response = await client.get(
        "/places", params={
            "category_id": str(category_cafe.id),
            "search": "Blue"
        }
    )

    assert ids(response) == [place_cafe["id"]]


async def test_results_ordered_newest_first(
        client,
        category_cafe,
        many_cafe_places
):
    response = await client.get(
        "/places",
        params={
            "category_id": str(category_cafe.id),
            "page_size": 5
        }
    )

    expected = [p["id"] for p in reversed(many_cafe_places)][:5]
    assert ids(response) == expected


@pytest.mark.usefixtures("place", "place_park")
async def test_pagination_applies_to_filtered_set(
        client,
        category_cafe,
        many_cafe_places
):
    params = {
        "category_id": str(category_cafe.id),
        "page_size": 10
    }

    pages = [
        (
            await client.get(
                "/places",
                params={**params, "page": n}
            )
        ).json()
        for n in (1, 2, 3)
    ]

    assert [len(p) for p in pages] == [10, 10, 5]
    all_ids = [p["id"] for page in pages for p in page]
    assert len(all_ids) == len(set(all_ids)) == 25
    assert set(all_ids) == {p["id"] for p in many_cafe_places}
