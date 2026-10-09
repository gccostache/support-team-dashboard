import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from streamlit.testing.v1 import AppTest
from coaching import list_actions

ROOT = Path(__file__).resolve().parents[1]


def selectbox(app, label):
    return next(widget for widget in app.selectbox if widget.label == label)


class InterfaceTests(unittest.TestCase):
    def setUp(self):
        import streamlit as st
        st.cache_resource.clear()
        self.folder = tempfile.TemporaryDirectory()
        self.db = Path(self.folder.name) / 'coaching.db'
        self.env = patch.dict(os.environ, {'SUPPORT_DASHBOARD_DB': str(self.db)})
        self.env.start()
        self.app = AppTest.from_file(str(ROOT / 'app.py'), default_timeout=20).run()

    def tearDown(self):
        import streamlit as st
        st.cache_resource.clear()
        self.env.stop()
        self.folder.cleanup()

    def assert_no_errors(self):
        self.assertEqual(len(self.app.exception), 0, [e.message for e in self.app.exception])

    def test_default_metrics_and_specialty_filter(self):
        self.assert_no_errors()
        self.assertEqual(self.app.metric[0].value, '82.1%')
        self.assertEqual(self.app.metric[2].value, '87.5%')
        selectbox(self.app, 'Specialty').select('Authentication').run()
        self.assert_no_errors()
        self.assertEqual(set(self.app.multiselect[0].value), {'Alex Morgan', 'Dana Popescu', 'Hana Lee'})
        self.assertEqual(selectbox(self.app, 'View team member').options, ['Alex Morgan', 'Dana Popescu', 'Hana Lee'])
        selectbox(self.app, 'Reporting month').select('2026-04').run()
        self.assert_no_errors()
        self.assertEqual(self.app.metric[2].value, '0.0%')

    def test_save_action_complete_reopen_and_reload(self):
        next(w for w in self.app.text_area if w.label == 'Agreed action').set_value('Review two case updates together.')
        next(w for w in self.app.button if w.label == 'Save action').click().run()
        self.assert_no_errors()
        self.assertEqual(list_actions(self.db)[0]['action'], 'Review two case updates together.')
        self.app.checkbox[0].check().run()
        self.assert_no_errors()
        self.assertIsNotNone(list_actions(self.db)[0]['completed_date'])
        self.app.checkbox[0].uncheck().run()
        self.assertIsNone(list_actions(self.db)[0]['completed_date'])
        self.app = AppTest.from_file(str(ROOT / 'app.py'), default_timeout=20).run()
        self.assert_no_errors()
        self.assertEqual(len(self.app.checkbox), 1)

    def test_empty_selection_shows_prompt(self):
        self.app.multiselect[0].set_value([]).run()
        self.assert_no_errors()
        self.assertTrue(any('Select at least one' in item.value for item in self.app.info))

class NoteAnalysisInterfaceTests(unittest.TestCase):
    """Model scores are mocked; verifies review/save behavior, not accuracy."""
    setUp = InterfaceTests.setUp
    tearDown = InterfaceTests.tearDown
    assert_no_errors = InterfaceTests.assert_no_errors

    def test_reviewed_theme_saved_instead_of_model_suggestion(self):
        from coaching_ai import decide_theme
        fake_scores = {'Communication': .70, 'Troubleshooting': .20, 'Documentation': .10, 'Product knowledge': .05}
        with patch('coaching_ai.SemanticNoteClassifier.analyze', return_value=decide_theme(fake_scores)), patch('coaching_ai.SemanticNoteClassifier.__init__', return_value=None):
            next(w for w in self.app.text_area if w.label == 'Case-review note').set_value('Updates lack next steps.')
            next(w for w in self.app.button if w.label == 'Analyze note').click().run()
            self.assert_no_errors()
            selectbox(self.app, 'Confirm or change the suggested theme').select('Documentation').run()
            next(w for w in self.app.button if w.label == 'Use reviewed theme in action').click().run()
            self.assertEqual(selectbox(self.app, 'Coaching theme').value, 'Documentation')
            next(w for w in self.app.text_area if w.label == 'Agreed action').set_value('Document the agreed next steps.')
            next(w for w in self.app.button if w.label == 'Save action').click().run()
            self.assert_no_errors()
            record = list_actions(self.db)[0]
            self.assertEqual(record['theme'], 'Documentation')
            self.assertNotIn('note', record)

    def test_changed_note_hides_stale_suggestion(self):
        from coaching_ai import decide_theme
        fake_scores = {'Communication': .70, 'Troubleshooting': .20, 'Documentation': .10, 'Product knowledge': .05}
        with patch('coaching_ai.SemanticNoteClassifier.analyze', return_value=decide_theme(fake_scores)), patch('coaching_ai.SemanticNoteClassifier.__init__', return_value=None):
            next(w for w in self.app.text_area if w.label == 'Case-review note').set_value('Updates lack next steps.')
            next(w for w in self.app.button if w.label == 'Analyze note').click().run()
            next(w for w in self.app.text_area if w.label == 'Case-review note').set_value('Different note.').run()
            self.assert_no_errors()
            self.assertFalse(any(w.label == 'Use reviewed theme in action' for w in self.app.button))


if __name__ == '__main__':
    unittest.main()
