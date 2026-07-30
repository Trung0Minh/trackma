from trackma.engine import Engine


class _Msg:
    def with_classname(self, _name):
        return self

    def debug(self, *_args, **_kwargs):
        pass


class _ParsedEpisode:
    def __init__(self, _msg, _filename):
        pass

    def getName(self):
        return 'Kamiina Botan'

    def getEpisodeNumbers(self, force_numbers=False):
        return (1, 1)


def test_add_show_to_library_rechecks_cached_miss():
    engine = object.__new__(Engine)
    engine.msg = _Msg()
    engine.parser_class = _ParsedEpisode
    engine.redirections = None

    show = {'id': 187869, 'title': 'Botan Kamiina Fully Blossoms When Drunk'}
    library = {}
    library_cache = {'[Judas] Kamiina Botan - S01E01.mkv': None}

    def guess_show(title):
        assert title == 'Kamiina Botan'
        return show

    library, library_cache = engine._add_show_to_library(
        library,
        library_cache,
        False,
        '/media/[Judas] Kamiina Botan - S01E01.mkv',
        '[Judas] Kamiina Botan - S01E01.mkv',
        ({show['id']: show}, {}),
        guess_show,
    )

    assert library == {187869: {1: '/media/[Judas] Kamiina Botan - S01E01.mkv'}}
    assert library_cache == {'[Judas] Kamiina Botan - S01E01.mkv': (187869, 1)}
