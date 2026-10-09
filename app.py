from datetime import date, timedelta
from pathlib import Path
import os
import pandas as pd
import streamlit as st
from dashboard import load_data, summarize, month_end, assignment_status, engineer_snapshot, attention_items
from coaching import add_action, list_actions, set_completed, action_status
from coaching_ai import THEMES, REVIEW, SemanticNoteClassifier

ROOT = Path(__file__).resolve().parent
DB_PATH = Path(os.environ.get('SUPPORT_DASHBOARD_DB', str(ROOT / 'coaching.db')))
st.set_page_config(page_title='Support Team Dashboard', page_icon='📊', layout='wide')


@st.cache_resource
def prepare_note_classifier():
    return SemanticNoteClassifier()


def pct(value):
    return 'N/A' if value is None or pd.isna(value) else f'{value:.1f}%'


try:
    data = load_data(ROOT / 'data')
except (ValueError, OSError) as exc:
    st.error(f'The demo data could not be loaded: {exc}')
    st.stop()

st.title('Support Team Development Dashboard')
st.caption('Fictional team • April–September 2026 • Management discussion prompts, not employee rankings')
months = sorted(data['monthly_metrics']['month'].unique())
with st.sidebar:
    st.header('Review scope')
    month = st.selectbox('Reporting month', months, index=len(months)-1)
    specialties = sorted(data['engineers']['specialty'].unique())
    specialty = st.selectbox('Specialty', ['All specialties', *specialties])
    available = data['engineers'] if specialty == 'All specialties' else data['engineers'][data['engineers']['specialty'] == specialty]
    names = available['name'].tolist()
    selected_names = st.multiselect('Team members', names, default=names)
    st.caption('Monthly metrics and trends follow these filters. Training and projects are evaluated at the selected month end.')
    st.divider()
    st.caption('CSAT: satisfied or very satisfied responses ÷ all survey responses. No overall employee score is calculated.')

engineers = available[available['name'].isin(selected_names)]
ids = engineers['engineer_id'].tolist()
if not ids:
    st.info('Select at least one team member in the sidebar.')
    st.stop()
metrics = data['monthly_metrics']
scoped = metrics[metrics['engineer_id'].isin(ids)]
current = scoped[scoped['month'] == month]
cutoff = month_end(month)
snapshot = engineer_snapshot(data, month, ids)
training = assignment_status(data['training'][data['training']['engineer_id'].isin(ids)], cutoff, 'assigned_date')
projects = assignment_status(data['projects'][data['projects']['engineer_id'].isin(ids)], cutoff, 'start_date')
summary = summarize(current)
name_map = dict(zip(data['engineers']['engineer_id'], data['engineers']['name']))


def display_assignments(frame, columns):
    shown = frame.copy()
    shown.insert(0, 'Engineer', shown['engineer_id'].map(name_map))
    st.dataframe(shown[['Engineer', *columns]], hide_index=True, width='stretch')


team_tab, profile_tab, coaching_tab = st.tabs(['Team overview', 'Individual profile', 'Coaching actions'])
with team_tab:
    st.subheader(f'Team overview · {month}')
    st.caption(f'{len(ids)} selected team members; {len(current)} monthly records. Backlog is a month-end snapshot.')
    cols = st.columns(4)
    cols[0].metric('CSAT', pct(summary['csat']))
    cols[0].caption(f"{summary['satisfied_responses']} satisfied / {summary['responses']} responses")
    cols[1].metric('Survey response rate', pct(summary['response_rate']))
    cols[1].caption(f"{summary['responses']} responses / {summary['invites']} invitations")
    completed_training = int((training['status'] == 'Completed').sum())
    cols[2].metric('Training completion', pct(100 * completed_training / len(training) if len(training) else None))
    cols[2].caption(f'{completed_training} / {len(training)} assignments through month end')
    cols[3].metric('Case quality', 'N/A' if summary['quality'] is None else f"{summary['quality']:.1f}/100")
    cols[3].caption(f"Average review score / 100 · {summary['reviews']} sampled cases")
    cols = st.columns(4)
    cols[0].metric('Open cases', summary['open_cases'])
    cols[0].caption(f"{summary['aged_open_cases']} older than 30 days; {summary['high_severity_open_cases']} high severity")
    cols[1].metric('KB articles created', summary['kb_created'])
    cols[1].caption(f"{summary['kb_updated']} updated · {summary['kb_reviewed']} reviewed")
    cols[2].metric('Project assignments', len(projects))
    cols[2].caption(f"{projects['project'].nunique()} distinct projects · {(projects['status'] == 'Overdue').sum()} overdue milestones")
    cols[3].metric('Cases closed', summary['closed_cases'])
    cols[3].caption('Volume needs case complexity and workload context.')

    st.subheader('CSAT trend')
    # Restrict the chart to the selected reporting month; do not show future data.
    history = scoped[scoped['month'] <= month].groupby('month')[['satisfied_responses', 'survey_responses']].sum()
    history['CSAT %'] = 100 * history['satisfied_responses'] / history['survey_responses'].replace(0, float('nan'))
    st.line_chart(history[['CSAT %']], y_label='CSAT %')
    st.caption('Team CSAT is weighted by response counts, rather than averaging engineer percentages. N/A means no responses.')

    st.subheader('Manager attention')
    prompts = attention_items(snapshot)
    if prompts.empty:
        st.info('No prompts from the demo rules for this selection.')
    else:
        st.dataframe(prompts, hide_index=True, width='stretch')
    st.caption('Illustrative prompts: fewer than 10 CSAT responses; CSAT below 85% with at least 10 responses; overdue training or milestones; at least 5 aged cases. Review context before acting.')

    st.subheader('Team member details')
    view = snapshot[['name', 'specialty', 'CSAT %', 'survey_responses', 'Quality score', 'quality_reviews',
                     'Training completion %', 'Training overdue', 'Project assignments', 'Project milestones overdue',
                     'kb_created', 'kb_updated', 'kb_reviewed', 'open_cases', 'aged_open_cases', 'closed_cases']].copy()
    view = view.rename(columns={'name': 'Engineer', 'specialty': 'Specialty', 'survey_responses': 'Survey responses',
                                'quality_reviews': 'Cases reviewed', 'kb_created': 'KB created', 'kb_updated': 'KB updated',
                                'kb_reviewed': 'KB reviewed', 'open_cases': 'Open cases', 'aged_open_cases': 'Aged cases', 'closed_cases': 'Closed cases'})
    st.dataframe(view.round(1), hide_index=True, width='stretch')
    st.download_button('Download filtered monthly summary', view.round(1).to_csv(index=False).encode('utf-8'),
                       file_name=f'team-summary-{month}.csv', mime='text/csv')
    with st.expander('Training assignments'):
        display_assignments(training, ['course', 'due_date', 'completed_date', 'status'])
    with st.expander('Project participation and milestones'):
        display_assignments(projects, ['project', 'role', 'milestone', 'due_date', 'completed_date', 'status'])

with profile_tab:
    person = st.selectbox('View team member', engineers['name'].tolist())
    eid = engineers.loc[engineers['name'] == person, 'engineer_id'].iloc[0]
    row = snapshot[snapshot['engineer_id'] == eid].iloc[0]
    st.subheader(person)
    st.caption(f"{row['specialty']} · Reporting month {month}")
    cols = st.columns(3)
    cols[0].metric('CSAT', pct(row['CSAT %']))
    cols[0].caption(f"{int(row['survey_responses']) if pd.notna(row['survey_responses']) else 'No'} survey responses")
    cols[1].metric('Case quality', 'N/A' if pd.isna(row['Quality score']) else f"{row['Quality score']:.1f}/100")
    cols[2].metric('Training completion', pct(row['Training completion %']))
    person_history = scoped[(scoped['engineer_id'] == eid) & (scoped['month'] <= month)].set_index('month')
    person_history['CSAT %'] = 100 * person_history['satisfied_responses'] / person_history['survey_responses'].replace(0, float('nan'))
    st.line_chart(person_history[['CSAT %']], y_label='CSAT %')
    if pd.notna(row['survey_responses']) and row['survey_responses'] < 10:
        st.warning('Small survey sample: inspect individual feedback before drawing conclusions.')
    st.write('Training')
    display_assignments(training[training['engineer_id'] == eid], ['course', 'due_date', 'completed_date', 'status'])
    st.write('Projects')
    display_assignments(projects[projects['engineer_id'] == eid], ['project', 'role', 'milestone', 'due_date', 'status'])
    st.write('Knowledge contributions by month')
    st.bar_chart(person_history[['kb_created', 'kb_updated', 'kb_reviewed']])

with coaching_tab:
    st.subheader('Agreed coaching actions')
    st.caption('This is a current action register. It follows the team member filters but is independent of the historical reporting month.')
    with st.expander('AI coaching-note analysis', expanded=True):
        st.write('Compare a fictional case-review note with four coaching themes. Review the suggestion before using it.')
        note = st.text_area('Case-review note', key='review_note', placeholder='The engineer resolved the issue, but customer updates lacked clear next steps and an agreed follow-up time.')
        if st.button('Analyze note'):
            st.session_state.pop('note_analysis', None)
            if not note.strip():
                st.warning('Enter a case-review note first.')
            else:
                try:
                    with st.spinner('Analyzing locally; first use may download the model...'):
                        result = prepare_note_classifier().analyze(note)
                    st.session_state['note_analysis'] = {'note': note, 'result': result}
                    st.session_state['reviewed_note_theme'] = result['theme'] if result['theme'] != REVIEW else 'Other'
                except Exception:
                    st.error('Note analysis could not run. Confirm sentence-transformers is installed and allow internet access for the first model download. Manual coaching actions remain available.')
        analysis = st.session_state.get('note_analysis')
        if analysis and analysis['note'] == note:
            result = analysis['result']
            st.write(f"Suggested theme: **{result['theme']}**")
            if result['theme'] == REVIEW:
                st.warning(result['reason'])
            else:
                st.info(result['reason'])
            st.table([{'Theme': theme_name, 'Similarity': round(score, 3)} for theme_name, score in result['scores'].items()])
            st.caption(f"Top-two score gap: {result['margin']:.3f}. Similarity is not a confidence percentage. Thresholds of 0.30 similarity and 0.05 gap are provisional; mixed notes may still receive one theme.")
            reviewed = st.selectbox('Confirm or change the suggested theme', [*THEMES, 'Other'], key='reviewed_note_theme')
            if st.button('Use reviewed theme in action'):
                st.session_state['action_theme'] = reviewed
                st.success('Reviewed theme copied to the action form. Select an owner and write the agreed action below.')
        elif analysis:
            st.info('The note has changed. Analyze it again to refresh the suggestion.')
        st.caption('The model compares meaning; it does not generate an action or assess employee performance. The raw note and scores are not saved to the database.')
    with st.form('new_action', clear_on_submit=True):
        action_person = st.selectbox('Action owner', engineers['name'].tolist())
        theme = st.selectbox('Coaching theme', ['Communication', 'Troubleshooting', 'Documentation', 'Product knowledge', 'Training', 'Projects', 'Other'], key='action_theme')
        action_text = st.text_area('Agreed action', placeholder='Example: Review two anonymized case updates together and agree on clearer next steps.')
        due = st.date_input('Action due date', value=date.today() + timedelta(days=14))
        save = st.form_submit_button('Save action')
    if save:
        owner_id = engineers.loc[engineers['name'] == action_person, 'engineer_id'].iloc[0]
        try:
            add_action(DB_PATH, owner_id, theme, action_text, due)
            st.success('Action saved.')
        except ValueError as exc:
            st.warning(str(exc))
    actions = [a for a in list_actions(DB_PATH) if a['engineer_id'] in ids]
    status_date = st.date_input('Check action due dates as of', value=date.today(), key='action_status_date')
    st.caption('Completion status is current. This date changes overdue checks; it does not reconstruct historical action states.')
    if not actions:
        st.info('No coaching actions saved for the selected team members. Add one above.')
    else:
        counts = {s: sum(action_status(a, status_date) == s for a in actions) for s in ['Open', 'Overdue', 'Completed']}
        cols = st.columns(3)
        for col, (label, count) in zip(cols, counts.items()):
            col.metric(label, count)
        for action in actions:
            label = f"{name_map[action['engineer_id']]} · {action['theme']} · {action_status(action, status_date)} · due {action['due_date']}"
            with st.expander(label):
                st.write(action['action'])
                completed = st.checkbox('Completed', value=bool(action['completed_date']), key=f"complete_{action['id']}")
                if completed != bool(action['completed_date']):
                    set_completed(DB_PATH, action['id'], completed)
                    st.rerun()
    st.caption('Actions are saved locally in coaching.db. Only the manager-reviewed action and selected theme are saved. AI suggestions never change team metrics or attention prompts.')
