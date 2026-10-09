"""Dashboard calculations, deliberately separate from Streamlit presentation."""
from pathlib import Path
import calendar
import pandas as pd

METRIC_COLUMNS = ['closed_cases', 'survey_invites', 'survey_responses', 'satisfied_responses',
                  'open_cases', 'aged_open_cases', 'high_severity_open_cases', 'quality_reviews',
                  'quality_points', 'kb_created', 'kb_updated', 'kb_reviewed']


def month_end(month):
    year, number = map(int, month.split('-'))
    return pd.Timestamp(year, number, calendar.monthrange(year, number)[1])


def load_data(folder):
    folder = Path(folder)
    frames = {name: pd.read_csv(folder / f'{name}.csv', keep_default_na=False)
              for name in ['engineers', 'monthly_metrics', 'training', 'projects']}
    validate_data(frames)
    return frames


def validate_data(frames):
    required = {
        'engineers': ['engineer_id', 'name', 'specialty'],
        'monthly_metrics': ['engineer_id', 'month', *METRIC_COLUMNS],
        'training': ['training_id', 'engineer_id', 'course', 'assigned_date', 'due_date', 'completed_date'],
        'projects': ['project_id', 'engineer_id', 'project', 'role', 'milestone', 'start_date', 'due_date', 'completed_date'],
    }
    for name, columns in required.items():
        if not set(columns).issubset(frames[name].columns):
            raise ValueError(f'{name}: required columns are missing.')
        if frames[name].empty:
            raise ValueError(f'{name}: data is empty.')
    ids = frames['engineers']['engineer_id']
    if ids.duplicated().any() or (ids == '').any():
        raise ValueError('Engineer IDs must be unique and nonempty.')
    for name in ['monthly_metrics', 'training', 'projects']:
        if not frames[name]['engineer_id'].isin(ids).all():
            raise ValueError(f'{name}: unknown engineer ID.')
    m = frames['monthly_metrics']
    if m.duplicated(['engineer_id', 'month']).any():
        raise ValueError('Monthly records must be unique per engineer and month.')
    for month in m['month']:
        month_end(month)
    for col in METRIC_COLUMNS:
        m[col] = pd.to_numeric(m[col], errors='raise')
        if m[col].isna().any() or (m[col] < 0).any() or (m[col] % 1 != 0).any():
            raise ValueError(f'{col}: counts must be nonnegative integers.')
    if (m['satisfied_responses'] > m['survey_responses']).any() or (m['survey_responses'] > m['survey_invites']).any():
        raise ValueError('CSAT counts are inconsistent.')
    for col in ['aged_open_cases', 'high_severity_open_cases']:
        if (m[col] > m['open_cases']).any():
            raise ValueError('Open case subsets cannot exceed the total backlog.')
    if (m['quality_points'] > 100 * m['quality_reviews']).any():
        raise ValueError('Quality points exceed the review scale.')
    for name, id_col, start in [('training', 'training_id', 'assigned_date'), ('projects', 'project_id', 'start_date')]:
        frame = frames[name]
        if frame[id_col].duplicated().any() or (frame[id_col] == '').any():
            raise ValueError(f'{name}: assignment IDs must be unique and nonempty.')
        for col in [start, 'due_date', 'completed_date']:
            raw = frame[col]
            if col != 'completed_date' and (raw == '').any():
                raise ValueError(f'{name}: {col} cannot be blank.')
            parsed = pd.to_datetime(raw.replace('', None), format='%Y-%m-%d', errors='raise')
            if col != 'completed_date' and parsed.isna().any():
                raise ValueError(f'{name}: invalid date.')
        starts = pd.to_datetime(frame[start])
        if (pd.to_datetime(frame['due_date']) < starts).any():
            raise ValueError(f'{name}: due date precedes assignment.')
        completed = pd.to_datetime(frame['completed_date'].replace('', None))
        if (completed < starts).any():
            raise ValueError(f'{name}: completion precedes assignment.')


def ratio(numerator, denominator):
    return 100 * numerator / denominator if denominator else None


def summarize(metrics):
    totals = metrics[METRIC_COLUMNS].sum()
    return {'csat': ratio(totals['satisfied_responses'], totals['survey_responses']),
            'responses': int(totals['survey_responses']), 'invites': int(totals['survey_invites']),
            'response_rate': ratio(totals['survey_responses'], totals['survey_invites']),
            'quality': ratio(totals['quality_points'], 100 * totals['quality_reviews']),
            'reviews': int(totals['quality_reviews']), **{col: int(totals[col]) for col in METRIC_COLUMNS}}


def assignment_status(frame, as_of, start_column):
    """Do not count assignments or completions that occur after the selected month."""
    cutoff = pd.Timestamp(as_of)
    out = frame[pd.to_datetime(frame[start_column]) <= cutoff].copy()
    done_dates = pd.to_datetime(out['completed_date'].replace('', None))
    done = done_dates.notna() & (done_dates <= cutoff)
    due = pd.to_datetime(out['due_date'])
    out['status'] = 'In progress'
    out.loc[(due < cutoff) & ~done, 'status'] = 'Overdue'
    out.loc[done, 'status'] = 'Completed'
    out.loc[~done, 'completed_date'] = ''
    return out


def engineer_snapshot(frames, month, ids):
    metrics = frames['monthly_metrics']
    selected = metrics[(metrics['month'] == month) & metrics['engineer_id'].isin(ids)].copy()
    out = frames['engineers'][frames['engineers']['engineer_id'].isin(ids)].merge(selected, on='engineer_id', how='left')
    out['CSAT %'] = 100 * out['satisfied_responses'] / out['survey_responses'].replace(0, float('nan'))
    out['Quality score'] = out['quality_points'] / out['quality_reviews'].replace(0, float('nan'))
    cutoff = month_end(month)
    training = assignment_status(frames['training'], cutoff, 'assigned_date')
    projects = assignment_status(frames['projects'], cutoff, 'start_date')
    for label, frame, status in [('Training assigned', training, None), ('Training completed', training, 'Completed'),
                                 ('Training overdue', training, 'Overdue'), ('Project assignments', projects, None),
                                 ('Project milestones overdue', projects, 'Overdue')]:
        counts = frame if status is None else frame[frame['status'] == status]
        out[label] = out['engineer_id'].map(counts.groupby('engineer_id').size()).fillna(0).astype(int)
    out['Training completion %'] = 100 * out['Training completed'] / out['Training assigned'].replace(0, float('nan'))
    return out.sort_values('name')


def attention_items(snapshot):
    """Coaching prompts, not rankings or performance verdicts."""
    rows = []
    for _, row in snapshot.iterrows():
        if pd.isna(row['survey_responses']):
            rows.append({'Engineer': row['name'], 'Prompt': 'Monthly metrics missing', 'Detail': 'Confirm the source data.'})
        elif row['survey_responses'] < 10:
            rows.append({'Engineer': row['name'], 'Prompt': 'Small CSAT sample', 'Detail': f"{int(row['survey_responses'])} responses; interpret cautiously."})
        elif row['CSAT %'] < 85:
            rows.append({'Engineer': row['name'], 'Prompt': 'Discuss customer feedback', 'Detail': f"CSAT {row['CSAT %']:.1f}% from {int(row['survey_responses'])} responses; review comments and case context."})
        for col, prompt in [('Training overdue', 'Follow up on training'), ('Project milestones overdue', 'Discuss project commitment')]:
            if row[col]:
                rows.append({'Engineer': row['name'], 'Prompt': prompt, 'Detail': f'{int(row[col])} overdue assignment(s).'})
        if pd.notna(row['aged_open_cases']) and row['aged_open_cases'] >= 5:
            rows.append({'Engineer': row['name'], 'Prompt': 'Review aging cases', 'Detail': f"{int(row['aged_open_cases'])} open cases older than 30 days; inspect blockers."})
    return pd.DataFrame(rows, columns=['Engineer', 'Prompt', 'Detail'])
