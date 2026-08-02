from trackma import utils
from trackma import title_matching


def _show(show_id, titles, my_status=1):
    return {
        'id': show_id,
        'titles': titles,
        'my_status': my_status,
    }


def _tracker_list(*shows, altnames=None):
    return ({show['id']: show for show in shows}, altnames or {})


def test_normalize_title_matches_taiga_equivalencies():
    assert utils.normalize_title('BanG Dream! It\'s MyGO!!!!!') == utils.normalize_title('Bang Dream Its MyGO')
    assert utils.normalize_title('Love & Lies') == utils.normalize_title('Love and Lies')
    assert utils.normalize_title('Girls und Panzer OAD') == utils.normalize_title('Girls und Panzer OVA')
    assert utils.normalize_title('Non Non Biyori Special') == utils.normalize_title('Non Non Biyori SP')


def test_guess_show_uses_normalized_exact_titles_before_fuzzy_matching():
    expected = _show(1, ['Boku no Hero Academia 2'])
    other = _show(2, ['Boku no Hero Academia'])

    result = utils.guess_show('Boku no Hero Academia II', _tracker_list(expected, other))

    assert result is expected


def test_guess_show_matches_year_variant_from_filename():
    expected = _show(1, ['Bungou Stray Dogs (2019)'])
    other = _show(2, ['Bungou Stray Dogs'])

    result = utils.guess_show('Bungou Stray Dogs 2019', _tracker_list(expected, other))

    assert result is expected


def test_guess_show_matches_taiga_special_abbreviations():
    expected = _show(1, ['Non Non Biyori SP'])

    result = utils.guess_show('Non Non Biyori Specials', _tracker_list(expected))

    assert result is expected


def test_guess_show_matches_short_filename_title_inside_long_alias():
    expected = _show(1, ['Botan Kamiina Fully Blossoms When Drunk',
                         'Kamiina Botan, Yoeru Sugata wa Yuri no Hana'])

    result = utils.guess_show('Kamiina Botan', _tracker_list(expected))

    assert result is expected


def test_title_matcher_uses_episode_to_disambiguate_identical_titles():
    completed_special = {
        'id': 1,
        'titles': ['False Memory'],
        'my_progress': 1,
        'total': 1,
    }
    currently_watching = {
        'id': 2,
        'titles': ['False Memory'],
        'my_progress': 1,
        'total': 7,
    }
    matcher = utils.TitleMatcher(_tracker_list(completed_special, currently_watching))

    assert matcher.match('False Memory', episode=2) is currently_watching


def test_title_matcher_reuses_preprocessed_aliases(monkeypatch):
    shows = _tracker_list(*(
        _show(index, ['Example Show {}'.format(index)])
        for index in range(100)
    ))
    original_normalize = title_matching.normalize_title
    calls = 0

    def counted_normalize(title):
        nonlocal calls
        calls += 1
        return original_normalize(title)

    monkeypatch.setattr(title_matching, 'normalize_title', counted_normalize)
    matcher = utils.TitleMatcher(shows)
    initialization_calls = calls

    for _ in range(10):
        matcher.match('Unmatched Release Name')

    assert initialization_calls == 100
    assert calls == initialization_calls + 10


def test_title_matcher_matches_compatibility_function():
    tracker_list = _tracker_list(
        _show(1, ['Example Show'], my_status=2),
        _show(2, ['Example Show Season 2'], my_status=1),
        altnames={'custom title': 2},
    )
    matcher = utils.TitleMatcher(tracker_list)

    for title in ('Custom Title', 'Example Show S2', 'No Match At All'):
        assert matcher.match(title) is utils.guess_show(title, tracker_list)
