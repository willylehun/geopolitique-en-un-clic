import copy
import json
import unittest
from datetime import datetime
from pathlib import Path
from election_background import apply_reviews, monitor_sources, fingerprint, add_discoveries


class BackgroundTests(unittest.TestCase):
    def setUp(self):
        root = Path(__file__).resolve().parents[1]
        self.reviewed = json.loads((root / 'data/election-program-reviewed.json').read_text())
        self.data = json.loads((root / 'data/election.json').read_text())

    def test_every_candidate_has_a_documented_review(self):
        apply_reviews(self.data, self.reviewed)
        for candidate in self.data['candidates']:
            self.assertIn(candidate['id'], self.reviewed)
            self.assertTrue(candidate['program_review']['review_note'])
            self.assertTrue(candidate['program_documents'])
        self.assertIn('philippe-brun', {c['id'] for c in self.data['candidates']})

    def test_sector_sources_are_required(self):
        for record in self.reviewed.values():
            for topic in record['program']:
                self.assertIn(topic, self.data['sectors'])
                self.assertTrue(record['program_sources'][topic])
                self.assertTrue(all('https://' in s for s in record['program_sources'][topic]))

    def test_newer_proposal_is_not_overwritten(self):
        c = self.data['candidates'][0]
        c['program']['Économie'] = 'Nouvelle annonce vérifiée séparément.'
        apply_reviews(self.data, self.reviewed)
        self.assertEqual(c['program']['Économie'], 'Nouvelle annonce vérifiée séparément.')

    def test_owned_reviews_update_without_overwriting_external_changes(self):
        data = {'candidates':[{'id':'a','program':{'Économie':''}}]}
        reviewed = {'a':{'program':{'Économie':'Première version'}, 'sources':['https://exemple.fr']}}
        apply_reviews(data, reviewed)
        reviewed['a']['program']['Économie'] = 'Version corrigée'
        apply_reviews(data, reviewed)
        self.assertEqual(data['candidates'][0]['program']['Économie'], 'Version corrigée')
        data['candidates'][0]['program']['Économie'] = 'Annonce plus récente'
        apply_reviews(data, reviewed)
        self.assertEqual(data['candidates'][0]['program']['Économie'], 'Annonce plus récente')

    def test_equal_quota_rotation_and_failure_keeps_last_success(self):
        data = {'candidates':[{'id':'a'},{'id':'b'}]}
        reviewed = {cid:{'source_documents':[{'url':f'https://exemple.fr/{cid}/{i}'} for i in range(3)]} for cid in ('a','b')}
        state = {}
        monitor_sources(data, state, reviewed, '2026-09-29T12:00:00+02:00', lambda url: ('initial', []))
        self.assertEqual(state['last_program_source_attempt_count'], 4)
        self.assertFalse(any(c.get('program_source_changes') for c in data['candidates']))
        monitor_sources(data, state, reviewed, '2026-09-29T13:00:00+02:00', lambda url: ('modifié', []))
        self.assertEqual(len(data['candidates'][0]['program_source_changes']), 1)
        self.assertEqual(len(data['candidates'][1]['program_source_changes']), 1)
        successful = copy.deepcopy(state['program_source_checks'])
        def fail(url):
            raise TimeoutError('timeout')
        monitor_sources(data, state, reviewed, '2026-09-29T14:00:00+02:00', fail)
        self.assertEqual(state['last_program_source_success_count'], 0)
        for key, result in state['program_source_checks'].items():
            self.assertEqual(result.get('successful_at'), successful[key].get('successful_at'))
        self.assertTrue(any(r['status']=='error' for r in data['candidates'][0]['program_watch']))

    def test_pdf_link_change_is_detected_and_scripts_are_ignored(self):
        page = '<main>' + 'Programme de campagne. ' * 12 + '<a href="v1.pdf">Lire</a></main><script>1</script>'
        first = fingerprint(page.encode(), 'text/html', 'https://exemple.fr/')
        self.assertEqual(first, fingerprint(page.replace('>1</script>','>2</script>').encode(), 'text/html', 'https://exemple.fr/'))
        self.assertNotEqual(first[0], fingerprint(page.replace('v1.pdf','v2.pdf').encode(), 'text/html', 'https://exemple.fr/')[0])
        with self.assertRaises(ValueError):
            fingerprint(b'<html>Access denied</html>', 'text/html', 'https://exemple.fr/')

    def test_discovery_never_becomes_a_promise_or_a_controversy(self):
        candidate = {'program':{}, 'controversies':[]}
        rows = [{'url':'https://exemple.fr/article','title':'Une accusation à vérifier','date':datetime.fromisoformat('2026-09-01'),'source':'Média'}]
        add_discoveries(candidate, rows, lambda row: True, lambda row: True, '2026-09-29')
        self.assertEqual(candidate['program'], {})
        self.assertEqual(candidate['controversies'], [])
        self.assertEqual(candidate['background_discoveries'][0]['status'], 'to_review')


if __name__ == '__main__':
    unittest.main()
