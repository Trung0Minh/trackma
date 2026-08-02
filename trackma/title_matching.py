import difflib
import re
import unicodedata


def normalize_title(title):
    """Normalize release and catalog titles for recognition."""
    if not title:
        return ""

    for before, after in {
        '@': 'a',
        '×': 'x',
        '꞉': ':',
        'Ō': 'ou',
        'ō': 'ou',
        'ū': 'uu',
    }.items():
        title = title.replace(before, after)

    title = unicodedata.normalize('NFKC', title)
    title = ''.join(
        char for char in title
        if unicodedata.category(char) not in {'Mn', 'Cc', 'Cf'}
    ).casefold()

    for before, after in (
        ('xiii', '13'), ('xii', '12'), ('xi', '11'), ('viii', '8'),
        ('vii', '7'), ('vi', '6'), ('iii', '3'), ('ii', '2'),
        ('ix', '9'), ('iv', '4'), ('v', '5'),
    ):
        title = re.sub(r'\b{}\b'.format(before), after, title)

    for before, after in (
        ('first', '1st'), ('second', '2nd'), ('third', '3rd'),
        ('fourth', '4th'), ('fifth', '5th'), ('sixth', '6th'),
        ('seventh', '7th'), ('eighth', '8th'), ('ninth', '9th'),
    ):
        title = re.sub(r'\b{}\b'.format(before), after, title)

    for number in range(1, 7):
        suffix = {1: 'st', 2: 'nd', 3: 'rd'}.get(number, 'th')
        for pattern in (
            '{}{} season'.format(number, suffix),
            'season {}'.format(number),
            'series {}'.format(number),
            's{}'.format(number),
        ):
            title = re.sub(r'\b{}\b'.format(pattern), str(number), title)

    title = title.replace('&', ' and ')
    for before, after in (
        ('the animation', ''), ('the', ''), ('episode', ''),
        ('oad', 'ova'), ('oav', 'ova'), ('specials', 'sp'),
        ('special', 'sp'), ('tv', ''),
    ):
        title = re.sub(r'\b{}\b'.format(re.escape(before)), after, title)

    title = re.sub(r'\s+', ' ', title).strip()
    title = ''.join(char for char in title if char.isalnum() or char.isspace())
    return re.sub(r'\s+', ' ', title).strip()


class TitleMatcher:
    """Preprocessed title index for repeated filename-to-list matching."""

    def __init__(self, tracker_list):
        showlist, altnames_map = tracker_list
        self.showlist = showlist
        self.altnames_map = altnames_map or {}
        self.entries = []
        self.exact = {}

        for item in showlist.values():
            aliases = []
            for title in item['titles']:
                normalized = normalize_title(title)
                matcher = difflib.SequenceMatcher(None, '', title.lower())
                aliases.append((normalized, matcher))
                self.exact.setdefault(normalized, item)
            self.entries.append((item, aliases))

    def match(self, show_title):
        if not show_title:
            return None

        showid = self.altnames_map.get(show_title.lower())
        if showid in self.showlist:
            return self.showlist[showid]

        normalized_query = normalize_title(show_title)
        exact = self.exact.get(normalized_query)
        if exact is not None:
            return exact

        if len(normalized_query.split()) >= 2:
            padded_query = ' ' + normalized_query + ' '
            for item, aliases in self.entries:
                for normalized, _matcher in aliases:
                    if (normalized.startswith(normalized_query + ' ')
                            or normalized.endswith(' ' + normalized_query)
                            or padded_query in (' ' + normalized + ' ')):
                        return item

        query = show_title.lower()
        candidates = []
        for item, aliases in self.entries:
            local_highest = 0
            for _normalized, matcher in aliases:
                matcher.set_seq1(query)
                threshold = max(local_highest, 0.7)
                if matcher.real_quick_ratio() <= threshold:
                    continue
                if matcher.quick_ratio() <= threshold:
                    continue
                local_highest = max(local_highest, matcher.ratio())
            if local_highest > 0.7:
                candidates.append((item, local_highest))

        if not candidates:
            return None

        candidates.sort(key=lambda candidate: candidate[1], reverse=True)
        best_ratio = candidates[0][1]
        watching = [
            candidate for candidate in candidates
            if candidate[1] >= best_ratio - 0.15
            and candidate[0].get('my_status') == 1
        ]
        return watching[0][0] if watching else candidates[0][0]
