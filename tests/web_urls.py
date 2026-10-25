"""Page-relative URLs must remain independent of upstream mounts."""
import unittest
from urllib.parse import urljoin
from PUI.web.urls import WebURLs


class WebURLTests(unittest.TestCase):
    def test_mount_does_not_change_public_urls(self):
        for mount in ('/', '/internal', '/tools/pui/'):
            urls = WebURLs(mount_path=mount)
            self.assertEqual(urls.mount_path, mount.rstrip('/') + '/')
            self.assertEqual(urls.route('pui/ws'), mount.rstrip('/') + '/pui/ws')
            self.assertEqual(urls.websocket(), 'pui/ws')
            self.assertEqual(urls.asset('v1', 'client.js'), 'assets/v1/client.js')
            for public in ('http://localhost:8000/', 'https://example.com/demo/',
                           'https://example.com/deeply/nested/app/'):
                self.assertEqual(urljoin(public, urls.websocket()), public + 'pui/ws')
                self.assertEqual(urljoin(public, urls.public('pui/images/id')), public + 'pui/images/id')

    def test_unicode_mount_normalizes(self):
        urls = WebURLs(mount_path='/工具/')
        self.assertEqual(urls.mount_path, '/%E5%B7%A5%E5%85%B7/')
        self.assertEqual(WebURLs(mount_path=urls.mount_path).mount_path, urls.mount_path)
        self.assertEqual(urls.public('pui/upload'), 'pui/upload')

    def test_invalid_mounts_and_endpoints(self):
        for mount in ('', 'tools/pui', '//example.com/pui', '/a/../b', '/%2e%2e/',
                      '/a//b/', '/a%2fb/', '/a%5cb/', '/%252e/', '/a?x=1', '/a#b',
                      '/a\\b/', '/a\nb/', '/a%00b/', '/a%zz/'):
            with self.subTest(mount=mount), self.assertRaises(ValueError):
                WebURLs(mount_path=mount)
        for endpoint in ('/pui/ws', '../pui/ws', 'https://other.example/x', 'a/../b'):
            with self.subTest(endpoint=endpoint), self.assertRaises(ValueError):
                WebURLs().public(endpoint)
        with self.assertRaises(ValueError):
            WebURLs().asset('nested/build', 'main.js')

    def test_base_url_is_removed(self):
        with self.assertRaises(TypeError):
            WebURLs(base_url='/public/')
