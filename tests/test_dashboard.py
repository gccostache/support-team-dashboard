import tempfile
import unittest
from datetime import date
from pathlib import Path
import pandas as pd
from dashboard import load_data, summarize, month_end, assignment_status, engineer_snapshot, attention_items, validate_data
from coaching import add_action, list_actions, set_completed, action_status

ROOT = Path(__file__).resolve().parents[1]


class DashboardTests(unittest.TestCase):
    def setUp(self):
        self.data = load_data(ROOT / 'data')

    def test_fixture_shape(self):
        self.assertEqual(len(self.data['engineers']), 8)
        self.assertEqual(len(self.data['monthly_metrics']), 48)

    def test_weighted_csat_not_average_of_percentages(self):
        metrics = self.data['monthly_metrics'].iloc[:2].copy()
        metrics['survey_responses'] = [2, 40]
        metrics['satisfied_responses'] = [2, 20]
        result = summarize(metrics)
        self.assertAlmostEqual(result['csat'], 100 * 22 / 42)
        self.assertNotEqual(result['csat'], 75)

    def test_zero_surveys_is_na(self):
        metrics = self.data['monthly_metrics'].iloc[:1].copy()
        metrics[['survey_responses', 'satisfied_responses', 'quality_reviews', 'quality_points']] = 0
        result = summarize(metrics)
        self.assertIsNone(result['csat'])
        self.assertIsNone(result['quality'])

    def test_empty_selection_is_na(self):
        result = summarize(self.data['monthly_metrics'].iloc[:0])
        self.assertIsNone(result['csat'])
        self.assertEqual(result['open_cases'], 0)

    def test_september_known_totals(self):
        result = summarize(self.data['monthly_metrics'].query('month == "2026-09"'))
        self.assertEqual(result['responses'], 156)
        self.assertEqual(result['satisfied_responses'], 128)
        self.assertEqual(result['open_cases'], 151)
        self.assertAlmostEqual(result['quality'], 3942 / 46)

    def test_month_end_leap_year(self):
        self.assertEqual(month_end('2024-02').day, 29)

    def test_completion_after_selected_date_is_hidden(self):
        frame = self.data['training'].iloc[:1].copy()
        frame['completed_date'] = '2026-05-10'
        result = assignment_status(frame, '2026-04-30', 'assigned_date')
        self.assertEqual(result.iloc[0]['status'], 'In progress')
        self.assertEqual(result.iloc[0]['completed_date'], '')

    def test_not_yet_assigned_is_excluded(self):
        self.assertTrue(assignment_status(self.data['projects'], '2026-06-30', 'start_date').empty)

    def test_due_today_not_overdue(self):
        frame = self.data['training'].iloc[:1].copy()
        frame['completed_date'] = ''
        result = assignment_status(frame, frame.iloc[0]['due_date'], 'assigned_date')
        self.assertEqual(result.iloc[0]['status'], 'In progress')

    def test_historical_completion_and_overdue(self):
        training = assignment_status(self.data['training'], '2026-09-30', 'assigned_date')
        self.assertEqual((training['status'] == 'Completed').sum(), 21)
        self.assertEqual((training['status'] == 'Overdue').sum(), 3)

    def test_filter_single_engineer(self):
        snapshot = engineer_snapshot(self.data, '2026-09', ['E08'])
        self.assertEqual(len(snapshot), 1)
        self.assertEqual(snapshot.iloc[0]['name'], 'Hana Lee')
        prompts = attention_items(snapshot)
        self.assertIn('Small CSAT sample', prompts['Prompt'].tolist())
        self.assertNotIn('Discuss customer feedback', prompts['Prompt'].tolist())

    def test_invalid_counts_rejected(self):
        self.data['monthly_metrics'].loc[0, 'satisfied_responses'] = 999
        with self.assertRaises(ValueError):
            validate_data(self.data)

    def test_duplicate_month_rejected(self):
        frame = self.data['monthly_metrics']
        self.data['monthly_metrics'] = pd.concat([frame, frame.iloc[:1]])
        with self.assertRaises(ValueError):
            validate_data(self.data)

    def test_unknown_engineer_rejected(self):
        self.data['training'].loc[0, 'engineer_id'] = 'UNKNOWN'
        with self.assertRaises(ValueError):
            validate_data(self.data)


class CoachingTests(unittest.TestCase):
    def test_save_reload_complete_and_reopen(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / 'test.db'
            identifier = add_action(path, 'E01', 'Communication', 'Review updates', '2026-10-15')
            actions = list_actions(path)
            self.assertEqual(actions[0]['action'], 'Review updates')
            self.assertEqual(action_status(actions[0], date(2026, 10, 15)), 'Open')
            self.assertEqual(action_status(actions[0], date(2026, 10, 16)), 'Overdue')
            set_completed(path, identifier, True)
            self.assertEqual(action_status(list_actions(path)[0], date(2026, 10, 16)), 'Completed')
            set_completed(path, identifier, False)
            self.assertIsNone(list_actions(path)[0]['completed_date'])

    def test_empty_action_rejected(self):
        with tempfile.TemporaryDirectory() as folder:
            with self.assertRaises(ValueError):
                add_action(Path(folder) / 'test.db', 'E01', 'Training', '   ', '2026-10-15')

    def test_quoted_text_saved_literally(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / 'test.db'
            text = "Review engineer's notes; don't delete records."
            add_action(path, 'E01', 'Documentation', text, '2026-10-15')
            self.assertEqual(list_actions(path)[0]['action'], text)


if __name__ == '__main__':
    unittest.main()
