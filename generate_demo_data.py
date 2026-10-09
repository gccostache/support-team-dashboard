"""Reproduce fictional fixtures with a fixed random seed. Run from any folder."""
import calendar
import csv
import random
from pathlib import Path

ROOT = Path(__file__).resolve().parent / 'data'
ENGINEERS = [
    ('E01', 'Alex Morgan', 'Authentication'), ('E02', 'Bianca Marin', 'Integration'),
    ('E03', 'Chris Patel', 'Performance'), ('E04', 'Dana Popescu', 'Authentication'),
    ('E05', 'Elliot Reed', 'Integration'), ('E06', 'Fatima Khan', 'Performance'),
    ('E07', 'Gabriel Ionescu', 'Integration'), ('E08', 'Hana Lee', 'Authentication'),
]


def write(name, fields, rows):
    ROOT.mkdir(exist_ok=True)
    with (ROOT / name).open('w', encoding='utf-8', newline='') as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        w.writerows(rows)


def main():
    rng = random.Random(42)
    write('engineers.csv', ['engineer_id', 'name', 'specialty'], [dict(zip(['engineer_id', 'name', 'specialty'], e)) for e in ENGINEERS])
    metrics = []
    for month in range(4, 10):
        for i, (eid, _, _) in enumerate(ENGINEERS):
            closed = rng.randint(25, 65)
            surveys = 3 if i == 7 else rng.randint(12, min(30, closed))
            satisfied = surveys if i == 7 else round(surveys * (0.70 + rng.random() * .28))
            reviews = rng.randint(3, 8)
            open_cases = rng.randint(8, 28)
            metrics.append(dict(engineer_id=eid, month=f'2026-{month:02d}', closed_cases=closed,
                survey_invites=closed, survey_responses=surveys, satisfied_responses=satisfied,
                open_cases=open_cases, aged_open_cases=rng.randint(0, min(7, open_cases)),
                high_severity_open_cases=rng.randint(0, min(4, open_cases)), quality_reviews=reviews,
                quality_points=sum(rng.randint(70, 100) for _ in range(reviews)),
                kb_created=rng.randint(0, 4), kb_updated=rng.randint(0, 5), kb_reviewed=rng.randint(0, 4)))
    write('monthly_metrics.csv', list(metrics[0]), metrics)
    trainings = []
    courses = [('Secure troubleshooting', '2026-04-01', '2026-05-15'),
               ('Customer communication', '2026-06-01', '2026-07-31'),
               ('API diagnostics', '2026-08-01', '2026-09-15')]
    for i, (eid, _, _) in enumerate(ENGINEERS):
        for j, (course, assigned, due) in enumerate(courses):
            completed = ['2026-05-10', '2026-07-20', '2026-09-10'][j]
            if (i, j) in {(1, 2), (3, 1), (6, 2)}:
                completed = ''
            if (i, j) == (2, 2):
                completed = '2026-09-20'
            trainings.append(dict(training_id=f'T{i+1:02d}{j+1}', engineer_id=eid, course=course,
                                 assigned_date=assigned, due_date=due, completed_date=completed))
    write('training.csv', list(trainings[0]), trainings)
    projects = []
    names = ['Login runbook refresh', 'API escalation checklist', 'Performance lab', 'New engineer onboarding']
    for i, (eid, _, _) in enumerate(ENGINEERS):
        projects.append(dict(project_id=f'P{i+1:02d}', engineer_id=eid, project=names[i % 4],
             role='Lead' if i < 4 else 'Contributor', milestone='Deliver reviewed draft',
             start_date='2026-07-01', due_date='2026-09-20' if i % 2 else '2026-10-15',
             completed_date='2026-09-18' if i in {0, 1, 4} else ''))
    write('projects.csv', list(projects[0]), projects)
    print('Created 8 fictional engineers, 48 monthly records, 24 training assignments, and 8 project assignments.')


if __name__ == '__main__':
    main()
