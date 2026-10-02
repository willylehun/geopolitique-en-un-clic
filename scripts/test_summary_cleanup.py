import json
import unittest
from pathlib import Path
from unittest.mock import patch
from scripts.summary_cleanup import dedupe_sentences
from scripts import update_news

TITLE = 'L’UE rejette la proposition de l’Ukraine de renégocier ses quotas d’exportation.'
DETAIL = "L'Union européenne n'envisage pas de renégocier les quotas d'exportation avec l'Ukraine, a déclaré mardi un porte-parole de la Commission européenne, rejetant la demande de Kiev d'un accès commercial supplémentaire alors que les frappes russes mettent son économie à rude épreuve, a rapporté Reuters."
CONTEXT = "Les conditions commerciales avec l'Ukraine sont devenues une question sensible au sein de l'UE après que l'accès sans droits de douane et sans quota accordé à Kiev en 2022 a entraîné un afflux de produits agricoles."


class SummaryCleanupTests(unittest.TestCase):
    def test_screenshot_keeps_detail_and_context(self):
        self.assertEqual(dedupe_sentences(f'{TITLE} {DETAIL} {CONTEXT}'), f'{DETAIL} {CONTEXT}')
        self.assertEqual(update_news.dedupe_summary_sentences(f'{TITLE} {DETAIL} {CONTEXT}'), f'{DETAIL} {CONTEXT}')

    def test_richer_sentence_replaces_repeated_headline(self):
        text = 'La France augmente les tarifs douaniers. La France augmente les tarifs douaniers de 10 % dès lundi.'
        self.assertEqual(dedupe_sentences(text), 'La France augmente les tarifs douaniers de 10 % dès lundi.')

    def test_later_short_repetition_is_removed(self):
        text = 'La France augmente les tarifs douaniers de 10 % dès lundi. La France augmente les tarifs douaniers.'
        self.assertEqual(dedupe_sentences(text), 'La France augmente les tarifs douaniers de 10 % dès lundi.')

    def test_changes_of_numbers_dates_actors_and_certainty_survive(self):
        examples = [
            'Les attaques font 7 morts à Gaza. Les attaques font 9 morts à Gaza.',
            'Les tarifs augmentent de 10 % en 2026. Les tarifs augmentent de 10 % en 2027.',
            'Donald Trump annonce des sanctions contre la Chine. Donald Trump annonce des sanctions contre la Russie.',
            'La France accepte les négociations commerciales. La France refuse les négociations commerciales.',
            'La France augmente les tarifs douaniers. La France ne relève pas les tarifs douaniers.',
            'La France pourrait augmenter les tarifs douaniers. La France augmente les tarifs douaniers.',
            'La France propose de nouvelles sanctions contre la Chine. La France annonce de nouvelles sanctions contre la Chine.',
            'La France approuve un plan de relance. La France annule un plan de relance.',
            'Burnham se prépare pour les élections de mai. Andy Burnham se prépare pour les élections anticipées.',
            'Le ministère de la Justice dépose une plainte sur les entretiens consacrés à l’immigration. Le ministère de la Justice dépose une plainte sur les entretiens accordés au quotidien.',
        ]
        for text in examples:
            with self.subTest(text=text):
                self.assertEqual(dedupe_sentences(text), text)

    def test_exact_repetition_and_decimals(self):
        sentence = 'La France augmente les tarifs de 2.5 %.'
        self.assertEqual(dedupe_sentences(f'{sentence} {sentence}'), sentence)

    def test_domains_and_abbreviations_are_not_split(self):
        text = 'La Maison Blanche lance America. Gov. America. Gov, un site public, doit simplifier les démarches.'
        self.assertEqual(dedupe_sentences(text), text)
        text = 'M. Martin présente une réforme fiscale. M. Martin présente une réforme fiscale.'
        self.assertEqual(dedupe_sentences(text), 'M. Martin présente une réforme fiscale.')

    def test_new_article_pipeline_uses_cleanup(self):
        art = {'title': TITLE, 'description': DETAIL + ' ' + CONTEXT, 'url':'https://publisher.example/world'}
        with patch.object(update_news, 'french_summary', return_value=f'{TITLE} {DETAIL} {CONTEXT}'), patch.object(update_news, 'content_rejection_reason', return_value=None):
            summary = update_news.article_summary(art)
        self.assertNotIn('rejette la proposition', summary)
        self.assertIn('porte-parole', summary)

    def test_cleanup_is_idempotent_over_the_existing_store(self):
        root = Path(__file__).resolve().parents[1]
        for item in json.loads((root/'data/news.json').read_text())['items']:
            summary = dedupe_sentences(item.get('summary',''))
            self.assertEqual(dedupe_sentences(summary), summary)


if __name__ == '__main__':
    unittest.main()
