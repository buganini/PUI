"""Pure URL tests: python -m unittest discover -s tests -p web_urls.py -v."""
import unittest

from PUI.web.urls import WebURLs


class WebURLTests(unittest.TestCase):
    def test_default_and_prefix_preserving_proxy(self):
        for prefix in ('/', '/tools/pui', '/tools/pui/'):
            with self.subTest(prefix=prefix):
                urls = WebURLs(prefix)
                base = prefix.rstrip('/') + '/'
                self.assertEqual(urls.base_url, base)
                self.assertEqual(urls.mount_path, base)
                self.assertEqual(urls.asset('v1', 'client/main.js'), base + 'assets/v1/client/main.js')
                self.assertEqual(urls.route('pui/ws'), base + 'pui/ws')
                self.assertEqual(urls.websocket(), base + 'pui/ws')

    def test_prefix_stripping_proxy_keeps_public_endpoints(self):
        urls = WebURLs('/tools/pui/', mount_path='/')
        self.assertEqual(urls.route('pui/ws'), '/pui/ws')
        self.assertEqual(urls.route('assets/v1/main.js'), '/assets/v1/main.js')
        self.assertEqual(urls.websocket(), '/tools/pui/pui/ws')
        self.assertEqual(urls.asset('v1', 'main.js'), '/tools/pui/assets/v1/main.js')

    def test_absolute_public_origin_is_independent_of_upstream(self):
        for scheme, ws in [('http', 'ws'), ('https', 'wss')]:
            urls = WebURLs(scheme + '://example.com:8443/tools/pui', mount_path='/internal/')
            self.assertEqual(urls.base_url, scheme + '://example.com:8443/tools/pui/')
            self.assertEqual(urls.websocket(), ws + '://example.com:8443/tools/pui/pui/ws')
            self.assertEqual(urls.route('pui/ws'), '/internal/pui/ws')
        self.assertEqual(WebURLs('https://[::1]:8443').websocket(), 'wss://[::1]:8443/pui/ws')

    def test_unicode_and_encoded_paths_have_one_canonical_form(self):
        urls = WebURLs('/工具/')
        self.assertEqual(urls.base_url, '/%E5%B7%A5%E5%85%B7/')
        self.assertEqual(WebURLs(urls.base_url).base_url, urls.base_url)

    def test_reject_ambiguous_or_external_path_components(self):
        invalid = ('', 'tools/pui', '//example.com/pui', 'ftp://example.com/',
                   'https://user:pass@example.com/', 'https://example.com:invalid/',
                   'https://exa mple.com/', ' https://example.com/',
                   '/a/../b', '/%2e%2e/', '/a//b/', '/a//',
                   '/a%2fb/', '/a%5cb/', '/%252e/', '/a?x=1', '/a#b', '/a?',
                   '/a\\b/', '/a\nb/', '/a%00b/', '/a%zz/')
        for value in invalid:
            with self.subTest(value=value), self.assertRaises(ValueError):
                WebURLs(value)
        for endpoint in ('/pui/ws', '../pui/ws', 'https://other.example/x', 'a/../b'):
            with self.subTest(endpoint=endpoint), self.assertRaises(ValueError):
                WebURLs('/prefix/').public(endpoint)
        with self.assertRaises(ValueError):
            WebURLs(mount_path='relative')
        with self.assertRaises(ValueError):
            WebURLs().asset('nested/build', 'main.js')


if __name__ == '__main__':
    unittest.main()
