from trackma import utils


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
