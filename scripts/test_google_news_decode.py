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

class FakeHTTPXResponse:
    status_code=200
    headers={}
    url="https://news.google.com/rss/articles/test"
    content=b"<html>article splash</html>"
    text="rpc response"
    def raise_for_status(self): pass

class FakeHTTPXClient:
    options=[]
    def __init__(self,**kwargs): self.options.append(kwargs)
    def __enter__(self): return self
    def __exit__(self,*_args): return False
    def get(self,*_args,**_kwargs): return FakeHTTPXResponse()
    def post(self,*_args,**_kwargs): return FakeHTTPXResponse()

class GoogleNewsDecodeTests(unittest.TestCase):
    def setUp(self):
        news.GOOGLE_NEWS_URL_CACHE.clear()
        news.GOOGLE_NEWS_RESOLVED.clear()
        news.ARTICLE_DETAIL_CACHE.clear()
        news.DISCOVERY_STATS.clear()
        news.GOOGLE_NEWS_DECODE_USED=0
        news.GOOGLE_BING_FALLBACK_USED=0
        news.ARTICLE_DETAIL_USED=0
        news.EXISTING_DETAIL_USED=0

    def test_recent_cbmi_ids_resolve_via_rss_splash_and_nested_rpc(self):
        publisher="https://www.reuters.com/world/europe/europe-policy-update-2026-09-30/"
        for article_id in RECENT_ARTICLE_IDS:
            source=f"https://news.google.com/rss/articles/{article_id}?oc=5"
            article_page=f'<html><div data-n-a-ts="1790722000" data-n-a-id="{article_id}" data-n-a-sg="signature-{article_id[:8]}"></div></html>'
            rpc=json.dumps([["wrb.fr","Fbv4je",json.dumps(["garturlres",publisher,None]),None,None,None,"generic"]])
            with patch.object(news,"_request_google_page",return_value=(f"https://news.google.com/articles/{article_id}",article_page)) as page, \
                 patch.object(news,"_post_google_article_decode",return_value=")]}'\n\n"+rpc):
                self.assertEqual(news.decode_google_news_url(source),publisher)
                page.assert_called_once()
                self.assertIn("/rss/articles/"+article_id,page.call_args.args[0])
                self.assertIn("hl=en-US&gl=US&ceid=US%3Aen",page.call_args.args[0])
                self.assertNotIn("oc=5",page.call_args.args[0])
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

    def test_read_input_uses_only_rss_splash_route_for_decode_parameters(self):
        article_id=RECENT_ARTICLE_IDS[0]
        source=f"https://news.google.com/read/{article_id}?hl=en-US&gl=US&ceid=US%3Aen"
        publisher="https://publisher.example/world/current-story"
        page=f'<div data-n-a-id="{article_id}" data-n-a-ts="1790722000" data-n-a-sg="read-signature"></div>'
        rpc=json.dumps([["wrb.fr","Fbv4je",json.dumps(["garturlres",publisher,None]),None]])
        with patch.object(news,"_request_google_page",return_value=("https://news.google.com/rss/articles/"+article_id,page)) as get_page, \
             patch.object(news,"_post_google_article_decode",return_value=")]}'\n\n"+rpc):
            self.assertEqual(news.decode_google_news_url(source),publisher)
        self.assertEqual(get_page.call_count,1)
        self.assertEqual(get_page.call_args.args[0],f"https://news.google.com/rss/articles/{article_id}?hl=en-US&gl=US&ceid=US%3Aen")

    def test_explicit_google_locale_is_preserved_for_splash_request(self):
        article_id=RECENT_ARTICLE_IDS[0]
        source=f"https://news.google.com/rss/articles/{article_id}?hl=de-DE&gl=DE&ceid=DE%3Ade&oc=5"
        page=f'<div data-n-a-id="{article_id}" data-n-a-ts="1790722000" data-n-a-sg="locale-signature"></div>'
        rpc=json.dumps([["wrb.fr","Fbv4je",json.dumps(["garturlres","https://publisher.example/world/story",None]),None]])
        with patch.object(news,"_request_google_page",return_value=("https://news.google.com/rss/articles/"+article_id,page)) as get_page, \
             patch.object(news,"_post_google_article_decode",return_value=")]}'\n\n"+rpc):
            self.assertEqual(news.decode_google_news_url(source),"https://publisher.example/world/story")
        self.assertEqual(get_page.call_args.args[0],f"https://news.google.com/rss/articles/{article_id}?hl=de-DE&gl=DE&ceid=DE%3Ade")

    def test_google_requests_use_http2_transport_when_available(self):
        FakeHTTPXClient.options=[]
        fake_httpx=type("FakeHTTPX",(),{"Client":FakeHTTPXClient})
        with patch.object(news,"httpx",fake_httpx):
            final_url,body=news._request_google_page("https://news.google.com/rss/articles/test")
            rpc=news._post_google_article_decode(RECENT_ARTICLE_IDS[0],"1790722000","signature")
        self.assertEqual(final_url,"https://news.google.com/rss/articles/test")
        self.assertIn("article splash",body)
        self.assertEqual(rpc,"rpc response")
        self.assertEqual(len(FakeHTTPXClient.options),2)
        self.assertTrue(all(options["http2"] for options in FakeHTTPXClient.options))
        self.assertTrue(all("headers" not in options for options in FakeHTTPXClient.options))

    def test_batchexecute_request_uses_expected_rpc_envelope(self):
        article_id=RECENT_ARTICLE_IDS[0]
        with patch.object(news,"httpx",None), patch.object(news.urllib.request,"urlopen",return_value=FakeResponse("ok","https://news.google.com")) as urlopen:
            news._post_google_article_decode(article_id,"1790722000","signature")
        req=urlopen.call_args.args[0]
        form=json.loads(news.urllib.parse.parse_qs(req.data.decode())["f.req"][0])
        rpc=form[0][0]
        self.assertEqual(rpc[0],"Fbv4je")
        self.assertEqual(len(rpc),4)
        self.assertEqual(rpc[2],None)
        self.assertEqual(rpc[3],"0")
        self.assertEqual(json.loads(rpc[1])[2],article_id)

    def test_unresolved_google_link_is_not_published_from_a_rss_snippet(self):
        day=news.datetime.now(news.UTC)
        source=f"https://news.google.com/rss/articles/{RECENT_ARTICLE_IDS[0]}"
        article={"title":"Government announces new sanctions after border conflict","source":"Reuters","date":day,"url":source,
                 "description":"A detailed RSS snippet that describes the sanctions, the border conflict, the government response, regional effects, and diplomatic consequences."}
        meta={"countries":["France"],"date":"30 septembre 2026","source":"Reuters","url":source}
        with patch.object(news,"matching_publisher_article_url",return_value=""), \
             patch.object(news,"resolve_google_news_with_bing",return_value=""), \
             patch.object(news,"detail_is_substantive",return_value=True), \
             patch.object(news,"fetch_article_detail") as fetch:
            self.assertIsNone(news.article_summary(article,meta,candidates=[article]))
        fetch.assert_not_called()
        self.assertEqual(news.DISCOVERY_STATS["google_intermediaire_non_resolu"],1)

    def test_automatic_items_with_stale_google_urls_are_purged(self):
        google=f"https://news.google.com/rss/articles/{RECENT_ARTICLE_IDS[0]}"
        self.assertTrue(news.has_unresolved_google_article_url({"origin":"rss","url":google}))
        self.assertTrue(news.has_unresolved_google_article_url({"origin":"global","url":google}))
        self.assertFalse(news.has_unresolved_google_article_url({"origin":"rss","url":"https://www.reuters.com/world/story"}))
        self.assertFalse(news.has_unresolved_google_article_url({"origin":"manual","url":google}))

    def test_google_intermediate_is_never_fetched_as_article_content(self):
        source=f"https://news.google.com/rss/articles/{RECENT_ARTICLE_IDS[0]}"
        with patch.object(news,"decode_google_news_url",return_value=source), patch.object(news.urllib.request,"urlopen") as urlopen:
            self.assertEqual(news.fetch_article_detail(source),"")
            urlopen.assert_not_called()
        self.assertEqual(news.DISCOVERY_STATS["google_intermediaire_non_resolu"],1)

    def test_batchexecute_google_result_is_rejected(self):
        raw=")]}'\\n\\n"+json.dumps([["wrb.fr","Fbv4je",json.dumps(["garturlres","https://news.google.com/articles/CBMi",None]),None]])
        self.assertEqual(news._google_batchexecute_publisher(raw),"")

    def test_exact_same_day_bing_match_supplies_publisher_url(self):
        article_id=RECENT_ARTICLE_IDS[0]
        day=news.datetime.now(news.UTC)
        google={"title":"Government announces new sanctions after border conflict","source":"Reuters","date":day,"url":f"https://news.google.com/rss/articles/{article_id}?oc=5","description":"A sufficiently detailed article description from Reuters describes the policy, the government response, the regional impact, and the next diplomatic steps."}
        bing={"title":google["title"],"source":"www.reuters.com","date":day,"url":"https://www.reuters.com/world/europe/sanctions-border-conflict/"}
        meta={"countries":["France"],"date":"30 septembre 2026","source":"Reuters","url":google["url"]}
        with patch.object(news,"detail_is_substantive",return_value=True), \
             patch.object(news,"french_summary",return_value="Le gouvernement annonce de nouvelles sanctions après un conflit frontalier."), \
             patch.object(news,"content_rejection_reason",return_value=None):
            self.assertIsNotNone(news.article_summary(google,meta,candidates=[google,bing]))
        self.assertEqual(google["url"],bing["url"])
        self.assertEqual(news.GOOGLE_NEWS_RESOLVED[f"https://news.google.com/rss/articles/{article_id}?oc=5"],bing["url"])
        self.assertEqual(news.DISCOVERY_STATS["google_decode_cross_feed_fallback"],1)

    def test_cross_feed_match_rejects_wrong_date_or_ambiguous_publisher(self):
        article_id=RECENT_ARTICLE_IDS[0]
        day=news.datetime.now(news.UTC)
        google={"title":"Government announces new sanctions after border conflict","source":"Reuters","date":day,"url":f"https://news.google.com/rss/articles/{article_id}?oc=5"}
        wrong_day={"title":google["title"],"source":"Reuters","date":day-news.timedelta(days=1),"url":"https://www.reuters.com/world/europe/old/"}
        self.assertEqual(news.matching_publisher_article_url(google,[wrong_day]),"")
        other_source={"title":google["title"],"source":"BBC","date":day,"url":"https://www.bbc.com/news/world-1"}
        self.assertEqual(news.matching_publisher_article_url(google,[wrong_day,other_source]),"")

    def test_near_identical_title_can_match_same_publisher(self):
        article_id=RECENT_ARTICLE_IDS[0]
        day=news.datetime.now(news.UTC)
        google={"title":"Government announces new sanctions after border conflict","source":"Reuters","date":day,"url":f"https://news.google.com/rss/articles/{article_id}?oc=5"}
        bing={"title":"Government announces new sanctions after border clashes","source":"www.reuters.com","date":day,"url":"https://www.reuters.com/world/europe/sanctions-border-conflict/"}
        self.assertEqual(news.matching_publisher_article_url(google,[bing]),bing["url"])

    def test_unresolved_google_link_can_use_a_targeted_bing_publisher_result(self):
        article_id=RECENT_ARTICLE_IDS[0]
        day=news.datetime.now(news.UTC)
        google={"title":"Government announces new sanctions after border conflict","source":"Reuters","date":day,"url":f"https://news.google.com/rss/articles/{article_id}?oc=5"}
        bing={"title":"Government announces new sanctions after border clashes","source":"www.reuters.com","date":day,"url":"https://www.reuters.com/world/europe/sanctions-border-conflict/"}
        with patch.object(news,"bing_rss_query",return_value=[bing]) as search:
            self.assertEqual(news.resolve_google_news_with_bing(google),bing["url"])
        self.assertIn('"Government announces new sanctions after border conflict"',search.call_args.args[0])
        self.assertEqual(news.GOOGLE_NEWS_URL_CACHE[google["url"]],bing["url"])
        self.assertEqual(news.DISCOVERY_STATS["google_bing_fallback_success"],1)

    def test_google_rss_description_recovers_matching_publisher_link(self):
        title="Government announces new sanctions after border conflict"
        raw='<a href="https://www.reuters.com/world/europe/sanctions-border-conflict/">Government announces new sanctions after border conflict</a>'
        self.assertEqual(
            news.google_rss_publisher_url(raw,title,"Reuters"),
            "https://www.reuters.com/world/europe/sanctions-border-conflict/",
        )

    def test_google_rss_description_rejects_google_and_unrelated_links(self):
        title="Government announces new sanctions after border conflict"
        google='<a href="https://news.google.com/articles/CBMi">Government announces new sanctions after border conflict</a>'
        unrelated='<a href="https://www.reuters.com/world/europe/old-story/">Sports results from the weekend</a>'
        self.assertEqual(news.google_rss_publisher_url(google,title,"Reuters"),"")
        self.assertEqual(news.google_rss_publisher_url(unrelated,title,"Reuters"),"")

    def test_google_rss_query_returns_verified_publisher_url_from_description(self):
        title="Government announces new sanctions after border conflict"
        google_url=f"https://news.google.com/rss/articles/{RECENT_ARTICLE_IDS[0]}?oc=5"
        publisher_url="https://www.reuters.com/world/europe/sanctions-border-conflict/"
        feed=("<?xml version='1.0'?><rss><channel><item>"
              f"<title>{title} - Reuters</title><link>{google_url}</link>"
              "<pubDate>Wed, 30 Sep 2026 05:00:00 GMT</pubDate>"
              "<source url='https://www.reuters.com'>Reuters</source>"
              f"<description>&lt;a href='{publisher_url}'&gt;{title}&lt;/a&gt;</description>"
              "</item></channel></rss>")
        with patch.object(news.urllib.request,"urlopen",return_value=FakeResponse(feed,"https://news.google.com/rss/search")):
            article=news.google_rss_query("test query")[0]
        self.assertEqual(article["url"],publisher_url)
        self.assertEqual(news.GOOGLE_NEWS_URL_CACHE[google_url],publisher_url)
        self.assertEqual(news.DISCOVERY_STATS["google_rss_description_fallback"],1)

    def test_direct_bing_item_survives_per_title_limit(self):
        day=news.datetime.now(news.UTC)
        title="Government announces new sanctions after border conflict"
        google=[{"title":title,"source":"Reuters","date":day,"url":f"https://news.google.com/rss/articles/{article_id}?oc=5"} for article_id in RECENT_ARTICLE_IDS[:2]]
        bing={"title":title,"source":"Reuters","date":day,"url":"https://www.reuters.com/world/europe/sanctions-border-conflict/"}
        today=news.editorial_day(day)
        retained=news.prioritize_articles([*google,bing],today,today)
        self.assertIn(bing,retained)

if __name__=="__main__":
    unittest.main()
