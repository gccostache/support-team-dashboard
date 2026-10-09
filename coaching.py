"""Local coaching actions. No notes leave the computer."""
import sqlite3
from datetime import date
from contextlib import contextmanager


@contextmanager
def connect(path):
    connection = sqlite3.connect(path)
    connection.execute('''CREATE TABLE IF NOT EXISTS actions (
        id INTEGER PRIMARY KEY, engineer_id TEXT NOT NULL, theme TEXT NOT NULL,
        action TEXT NOT NULL, due_date TEXT NOT NULL, created_date TEXT NOT NULL,
        completed_date TEXT)''')
    try:
        yield connection
        connection.commit()
    except Exception:
        connection.rollback()
        raise
    finally:
        connection.close()


def add_action(path, engineer_id, theme, action, due_date):
    if not engineer_id.strip() or not theme.strip() or not action.strip():
        raise ValueError('Engineer, theme, and action are required.')
    due = date.fromisoformat(str(due_date))
    with connect(path) as db:
        cursor = db.execute('INSERT INTO actions (engineer_id, theme, action, due_date, created_date) VALUES (?, ?, ?, ?, ?)',
            (engineer_id, theme, action.strip(), due.isoformat(), date.today().isoformat()))
        return cursor.lastrowid


def list_actions(path):
    with connect(path) as db:
        db.row_factory = sqlite3.Row
        return [dict(row) for row in db.execute('SELECT * FROM actions ORDER BY due_date, id')]


def set_completed(path, action_id, completed):
    with connect(path) as db:
        db.execute('UPDATE actions SET completed_date = ? WHERE id = ?',
                   (date.today().isoformat() if completed else None, action_id))


def action_status(action, as_of):
    if action['completed_date']:
        return 'Completed'
    return 'Overdue' if date.fromisoformat(action['due_date']) < as_of else 'Open'
