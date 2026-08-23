from io import BytesIO

import pytest
from bs4 import BeautifulSoup

from trackma import utils
from trackma.lib.libvndb import libvndb
from trackma.lib.nyaa import NyaaSearcher
from trackma.lib.qbittorrent import QBitClient


class Response(BytesIO):
    def __init__(self, payload, content_length=None):
        super().__init__(payload)
        self.headers = {}
        if content_length is not None:
            self.headers['Content-Length'] = str(content_length)


class ClosedSocket:
    def sendall(self, _payload):
        pass

    def recv(self, _size):
        return b''


def test_response_reader_rejects_declared_and_streamed_oversize():
    with pytest.raises(ValueError, match='exceeds'):
        utils.read_response_limited(Response(b'', content_length=11), limit=10)
    with pytest.raises(ValueError, match='exceeds'):
        utils.read_response_limited(Response(b'12345678901'), limit=10)


def test_vndb_eof_does_not_spin_forever():
    api = object.__new__(libvndb)
    api.s = ClosedSocket()

    with pytest.raises(utils.APIError, match='closed'):
        api._sendcmd('get vn basic')


def test_nyaa_rich_text_is_sanitized():
    fragment = BeautifulSoup(
        '<div onclick="steal()"><script>bad()</script>'
        '<a href="javascript:bad()" style="color:red">unsafe</a>'
        '<a href="https://example.com" data-x="1">safe</a></div>',
        'lxml',
    ).div

    sanitized = NyaaSearcher._sanitize(fragment)

    assert 'script' not in sanitized
    assert 'onclick' not in sanitized
    assert 'javascript:' not in sanitized
    assert 'style=' not in sanitized
    assert 'href="https://example.com"' in sanitized


def test_nyaa_search_reports_actual_next_page(monkeypatch):
    html = '''
      <table class="torrent-list"><tbody>
        <tr>
          <td><a title="Anime - English-translated"></a></td>
          <td><a href="/view/1" title="Release 1">Release 1</a></td>
          <td><a href="/download/1.torrent"></a><a href="magnet:?xt=test"></a></td>
          <td>1 GiB</td><td>2026-08-02</td><td>10</td><td>2</td><td>50</td>
        </tr>
      </tbody></table>
      <ul class="pagination"><li><a href="/?q=test&amp;p=2">2</a></li></ul>
    '''
    searcher = NyaaSearcher()
    monkeypatch.setattr(searcher, '_fetch', lambda *_args: html)

    result = searcher.search('test', page=1, include_page_info=True)

    assert result['has_next'] is True
    assert result['results'][0]['title'] == 'Release 1'


def test_qbittorrent_add_has_local_service_timeout(monkeypatch):
    client = QBitClient()
    captured = {}

    class SuccessfulResponse:
        status_code = 200
        text = 'Ok.'

    def post(_url, data, timeout):
        captured['data'] = data
        captured['timeout'] = timeout
        return SuccessfulResponse()

    monkeypatch.setattr(client.session, 'post', post)

    assert client.add_magnet('magnet:?xt=test') is True
    assert captured['timeout'] == 3


def test_qbittorrent_login_identifies_wrong_http_service(monkeypatch):
    warnings = []

    class Messenger:
        def warn(self, message):
            warnings.append(message)

    class UnsupportedResponse:
        status_code = 501
        text = (
            '<!DOCTYPE HTML><html><body><h1>Error response</h1>'
            '<p>Unsupported method (POST).</p></body></html>'
        )

    client = QBitClient(messenger=Messenger())
    monkeypatch.setattr(
        client.session,
        'post',
        lambda _url, data, timeout: UnsupportedResponse(),
    )

    assert client.login(auto_launch=False) is False
    assert warnings == [
        'qBittorrent: localhost:8080 is not serving the qBittorrent Web API '
        '(HTTP 501). Check that qBittorrent is running, Web UI is enabled, '
        'and Trackma\'s host and port match its Web UI settings.'
    ]
