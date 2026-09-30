"""Tests de non-régression pour les liens Google News CBMi récents."""
import importlib.util
import json
import unittest
from pathlib import Path
from unittest.mock import patch

MODULE_PATH=Path(__file__).with_name("update_news.py")
spec=importlib.util.spec_from_file_location("update_news",MODULE_PATH)
news=importlib.util.module_from_spec(spec)
spec.loader.exec_module(news)

# Identifiants CBMi réellement observés dans les résultats du run Actions #237.
RECENT_ARTICLE_IDS=(
    "CBMihgFBVV95cUxQS0h6WHkwV2lWMERQNlBLdVNBSF82dkpiUGFkZXFTVG13WW83X2xhVGt5Q2ZtRlhEQVFVQlh6em9ERXQzMDVzMmNaWWtaQXVQZTlvWnNyN0J",
    "CBMijAFBVV95cUxPcVBjSFpybU8xTVFWWmlNVjFRZHV0cTdESVVNVy1vYTFUbUxJdlBIaHAzaWhQa0dzNFdRZEYwZlN4REg4cFFGQUpUal92dzN3NVk5Mi02YTQ",
    "CBMiYkFVX3lxTE5MVUhlMXVDOTJIcW9oRkxORFA0WUdHZ1V3dUgzdG10UWtKQk5JTFNCVHpBVExxR2NRNEFPU0dfbkRMN2Z4U1l0SWVqX0VxTjZackhQZG5HU0Z",
)

class FakeResponse:
    def __init__(self, body, url):
        self.body=body.encode("utf-8") if isinstance(body,str) else body
        self.url=url
    def __enter__(self): return self
    def __exit__(self,*_args): return False
    def geturl(self): return self.url
    def read(self,_size=-1): return self.body

class GoogleNewsDecodeTests(unittest.TestCase):
    def setUp(self):
        news.GOOGLE_NEWS_URL_CACHE.clear()
        news.GOOGLE_NEWS_RESOLVED.clear()
        news.ARTICLE_DETAIL_CACHE.clear()
        news.DISCOVERY_STATS.clear()
        news.GOOGLE_NEWS_DECODE_USED=0
        news.ARTICLE_DETAIL_USED=0
        news.EXISTING_DETAIL_USED=0

    def test_recent_cbmi_ids_resolve_via_article_page_and_nested_rpc(self):
        publisher="https://www.reuters.com/world/europe/europe-policy-update-2026-09-30/"
        for article_id in RECENT_ARTICLE_IDS:
            source=f"https://news.google.com/rss/articles/{article_id}?oc=5"
            article_page=f'<html><div data-n-a-ts="1790722000" data-n-a-id="{article_id}" data-n-a-sg="signature-{article_id[:8]}"></div></html>'
            rpc=json.dumps([["wrb.fr","Fbv4je",json.dumps(["garturlres",publisher,None]),None,None,None,"generic"]])
            with patch.object(news,"_request_google_page",return_value=(f"https://news.google.com/articles/{article_id}",article_page)) as page, \
                 patch.object(news,"_post_google_article_decode",return_value=")]}'\n\n"+rpc):
                self.assertEqual(news.decode_google_news_url(source),publisher)
                page.assert_called_once()
        self.assertEqual(news.DISCOVERY_STATS["google_decode_success"],len(RECENT_ARTICLE_IDS))
        self.assertEqual(news.GOOGLE_NEWS_DECODE_USED,len(RECENT_ARTICLE_IDS))

    def test_old_base64_url_still_decodes_without_network(self):
        import base64
        raw=b'\x08\x13"https://publisher.example/world/story\xd2\x01'
        article_id=base64.urlsafe_b64encode(raw).decode().rstrip("=")
        self.assertEqual(news.decode_google_news_direct_id(article_id),"https://publisher.example/world/story")

    def test_canonical_external_url_is_a_safe_fallback_when_params_are_missing(self):
        article_id=RECENT_ARTICLE_IDS[0]
        source=f"https://news.google.com/rss/articles/{article_id}"
        body=f'<html><meta property="og:url" content="https://publisher.example/world/story"><div data-n-a-id="{article_id}"></div></html>'
        with patch.object(news,"_request_google_page",return_value=(f"https://news.google.com/articles/{article_id}",body)):
            self.assertEqual(news.decode_google_news_url(source),"https://publisher.example/world/story")
        self.assertEqual(news.DISCOVERY_STATS["google_decode_metadata_fallback"],1)

    def test_google_intermediate_is_never_fetched_as_article_content(self):
        source=f"https://news.google.com/rss/articles/{RECENT_ARTICLE_IDS[0]}"
        with patch.object(news,"decode_google_news_url",return_value=source), patch.object(news.urllib.request,"urlopen") as urlopen:
            self.assertEqual(news.fetch_article_detail(source),"")
            urlopen.assert_not_called()
        self.assertEqual(news.DISCOVERY_STATS["google_intermediaire_non_resolu"],1)

    def test_batchexecute_google_result_is_rejected(self):
        raw=")]}'\\n\\n"+json.dumps([["wrb.fr","Fbv4je",json.dumps(["garturlres","https://news.google.com/articles/CBMi",None]),None]])
        self.assertEqual(news._google_batchexecute_publisher(raw),"")

if __name__=="__main__":
    unittest.main()
