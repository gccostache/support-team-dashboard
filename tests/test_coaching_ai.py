import unittest
from coaching_ai import THEMES, REVIEW, decide_theme, SemanticNoteClassifier


class ThemeTests(unittest.TestCase):
    def scores(self, **updates):
        result = dict(zip(THEMES, [.65, .20, .15, .10]))
        result.update(updates)
        return result

    def test_clear_suggestion(self):
        self.assertEqual(decide_theme(self.scores())['theme'], 'Communication')

    def test_weak_match_requests_review(self):
        result = dict.fromkeys(THEMES, .10)
        result['Communication'] = .29
        self.assertEqual(decide_theme(result)['theme'], REVIEW)

    def test_close_match_requests_review(self):
        self.assertEqual(decide_theme(self.scores(Troubleshooting=.63))['theme'], REVIEW)

    def test_unrounded_score_is_used(self):
        self.assertEqual(decide_theme(self.scores(Communication=.2999))['theme'], REVIEW)

    def test_invalid_scores_rejected(self):
        with self.assertRaises(ValueError):
            decide_theme(self.scores(Communication=float('nan')))

    def test_blank_note_rejected_before_model_use(self):
        classifier = SemanticNoteClassifier.__new__(SemanticNoteClassifier)
        with self.assertRaises(ValueError):
            classifier.analyze('   ')
