# Support Team Development Dashboard

A local management dashboard with **eight fictional support engineers and six months of data (April–September 2026)**. Review customer feedback, training, projects, knowledge contributions, case quality, workload, and agreed coaching actions.

Team metrics and attention prompts use explicit calculations and rules. **Coaching-note analysis uses a local pretrained embedding model** to suggest Communication, Troubleshooting, Documentation, or Product knowledge. The manager confirms or changes the suggestion before saving an action.

## Run on Windows

Extract the project so `app.py` is at `C:\Users\George\support-team-dashboard\app.py`. Open PowerShell and run:

```powershell
cd C:\Users\George\support-team-dashboard
py -3.13 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe -m streamlit run app.py
```

Use the local URL printed by Streamlit, usually `http://localhost:8501`. If another Streamlit app is running, this app may use another port. Keep PowerShell running; stop the app with Ctrl+C. No paid API or API key is needed. Installation requires internet access. The first note analysis downloads the embedding model; subsequent use can use its local cache.

## Screens

- **Team overview:** weighted CSAT, response counts and rate, training completion, case-quality score, knowledge contributions, month-end workload, project assignments, and manager attention prompts. Download the filtered monthly summary as CSV.
- **Individual profile:** results and trends with training assignments, project roles and milestones, and monthly KB contributions.
- **Coaching actions:** analyze a fictional case-review note, inspect theme similarity scores, and confirm or change the suggested theme. Save agreed actions with owners, themes, and due dates; mark them completed or reopen them. Data persists in local SQLite `coaching.db` across refreshes and restarts.

Select a reporting month, specialty, and team members in the sidebar. Historical charts stop at the selected month. Training and project status are assessed at its month end. The coaching register is explicitly current and independent of that historical month; its date control changes overdue checks, not historical completion state.

## AI coaching-note analysis

1. Open **Coaching actions** and enter a fictional **Case-review note**.
2. Click **Analyze note**. Pretrained `all-MiniLM-L6-v2` embeddings compare the note with four theme descriptions on the local CPU.
3. Inspect the suggestion and scores. Cosine similarities are not confidence percentages.
4. Confirm or change the theme, then click **Use reviewed theme in action**.
5. Select the action owner, write the agreed action, check the theme, and save.

A best score below 0.30 or top-two gap below 0.05 requests review. These thresholds are provisional. Mixed notes may still receive a single theme; select Other or save separate actions. Positive wording and negation may be misunderstood. No custom training, generated action, or validated model accuracy is claimed.

Raw notes and scores stay in the Streamlit session and are not saved to SQLite. Only the owner, manager-selected theme, action text, dates, and completion status are saved. Editing a note hides its previous result until reanalysis. Manual actions remain available if inference fails. AI suggestions never change metrics or attention prompts.

Try these manual checks; expected labels are hypotheses to verify:

| Fictional note | Expected theme |
| --- | --- |
| Customer updates lacked clear next steps and an agreed follow-up time. | Communication |
| The investigation lacked reproducible steps and logs before testing a hypothesis. | Troubleshooting |
| Case notes omitted the resolution details and internal handover information. | Documentation |
| The engineer needs to learn the product configuration options and supported feature behavior. | Product knowledge |
| What will the weather be tomorrow? | Needs review |

## Definitions

| Metric | Calculation or interpretation |
| --- | --- |
| CSAT | Satisfied or very satisfied responses divided by all survey responses |
| Team CSAT | Sum of satisfied responses divided by sum of responses; not an average of engineer percentages |
| Survey response rate | Responses divided by survey invitations |
| Training completion | Completed assignments divided by assignments made through selected month end |
| Case-quality score | Total quality points divided by number of sampled cases reviewed; scale 0–100 |
| Project participation | Number of engineer-project assignments; also shows distinct project names |
| KB contributions | Articles created, updated, and reviewed during the selected month; separate measures, not an employee score |
| Open cases | Month-end snapshot, not summed across months |
| Aged open cases | Open cases older than 30 days at month end |
| High-severity open cases | Fictional high-severity subset of open cases; may overlap with aged cases |

A zero denominator displays N/A. Missing monthly rows remain missing in individual details rather than being treated as zero performance. Blank completion dates mean unfinished assignments. A task due on the cutoff date is not yet overdue; a later completion is hidden when viewing earlier months. Completed-late assignments are shown as completed, not currently overdue.

## Manager attention rules

These are discussion prompts, not judgments:

- Fewer than 10 survey responses: flag a small sample.
- CSAT below 85% with at least 10 responses: discuss feedback and case context.
- Outstanding training or project milestones past their due date: follow up on blockers.
- At least five open cases older than 30 days: review aging work.
- Missing monthly metrics: confirm the source data.

Thresholds are illustrative. No overall employee score, ranking, causal conclusion, or performance prediction is calculated. Case mix, survey selection, case complexity, and assigned responsibilities affect interpretation. Article counts do not establish article quality or customer impact.

## Fictional source data

| File | Records | Purpose |
| --- | ---: | --- |
| `data/engineers.csv` | 8 | Team identities and specialties |
| `data/monthly_metrics.csv` | 48 | Monthly feedback, case quality, KB activity, and workload |
| `data/training.csv` | 24 | Training assignment, due, and completion dates |
| `data/projects.csv` | 8 | Engineer-project assignments, roles, and milestones |

All names, metrics, and assignments are fabricated. Each project row represents an assignment, with its own ID; a shared project name groups participants. There is one survey invitation per closed case in these fixtures, an illustrative assumption rather than a universal CSAT practice.

Recreate the same demo data using the fixed seed:

```powershell
.\.venv\Scripts\python.exe generate_demo_data.py
```

This **overwrites the four fictional CSV fixtures**, so preserve any edits first. It does not modify coaching actions. There is no in-app upload or editing of the source CSVs in this version.

## Verification

```powershell
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
```

Tests check weighted metrics, zero denominators, date boundaries, future completions, selection filters, inconsistent input, and persisted coaching actions. Interface tests exercise the Streamlit app, filters, saving/completing/reopening an action, an empty selection, overriding an AI theme before saving, and hiding stale analysis. **AI interface tests mock scores** and do not establish model accuracy. There are 28 automated checks.

For the full team in September 2026, expected results are:

- CSAT **82.1%**: **128 / 156** satisfied responses.
- Survey response rate **42.6%**: **156 / 366** invitations.
- Training completion **87.5%**: **21 / 24** assignments.
- Case-quality score **85.7 / 100**, based on **46** sampled cases.
- **151** open cases; **30** older than 30 days.
- **20** KB articles created, **20** updated, **17** reviewed.
- **8** project assignments across **4** projects.

Filtering to Authentication selects Alex Morgan, Dana Popescu, and Hana Lee. Hana's September CSAT is 100% from only three responses, and the dashboard explicitly prompts caution.

## Architecture

- `app.py`: Streamlit forms, filters, tables, charts, and downloads.
- `dashboard.py`: validation, weighted calculations, date-aware assignment status, and attention prompts.
- `coaching.py`: parameterized SQLite operations for coaching actions.
- `coaching_ai.py`: embedding inference and theme-review rules.
- `generate_demo_data.py`: reproducible fictional fixtures.
- `tests/`: calculation, storage, and interface tests.

Coaching records stay on the computer running Streamlit. There is no authentication, multi-manager access control, external integration, or hosted deployment. The app is intended for fictional demonstration data. Dependency ranges permit updates; record your working environment before sharing a deployed version.

## Publish to GitHub

Create a repository named `support-team-dashboard`. Upload the code, README, requirements, fictional `data` folder, `tests`, and `.github/workflows/checks.yml`. Keep folder structure intact. Do not upload `.venv`, `__pycache__`, or `coaching.db`; `.gitignore` excludes them when using Git. Browser uploads require you to select only the intended files.

Built with AI coding assistance. Explain the metric definitions, validation, date handling, and human management decisions when presenting the project. Distinguish AI theme suggestions from ordinary dashboard calculations; do not claim validated model accuracy or measured productivity improvements.
