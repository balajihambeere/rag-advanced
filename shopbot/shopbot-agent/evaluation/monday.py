# evaluation/monday.py
# Source: Book 2, Chapter 8 — You Cannot Improve What You Do Not Measure
# RAGAS Monday ritual: run every Monday at 09:00 IST, append one row to the
# shared Google Sheets spreadsheet. Same dataset, same questions, every week.
# The column of Mondays tells whether the system is improving, degrading, or holding.
#
# Run manually:   python -m evaluation.monday
# Run via cron:   0 9 * * 1 cd /opt/shopbot && python -m evaluation.monday
#
# The spreadsheet "zUdyog ShopBot" must be accessible via a service account.
# Set GOOGLE_APPLICATION_CREDENTIALS env var to the path of the credentials JSON file.
# gspread.service_account() reads this via Application Default Credentials.

import sys
from datetime import date
from evaluation.evaluate import run_evaluation, RAGAS_AVAILABLE


def post_monday_row(notes: str = "") -> None:
    """Run evaluation and append one row to the RAGAS Monday spreadsheet."""
    scores = run_evaluation()

    try:
        import gspread
        sheet = gspread.service_account().open("zUdyog ShopBot").sheet1
        sheet.append_row([
            date.today().isoformat(),
            scores["F"],
            scores["AR"],
            scores["CP"],
            scores["CR"],
            notes,
        ])
        print(f"Row appended: {date.today().isoformat()} — {scores}")
    except Exception as e:
        # If gspread is unavailable, print results so the cron log captures them
        print(f"Spreadsheet unavailable ({e}) — scores for {date.today().isoformat()}:")
        print(f"  F={scores['F']}  AR={scores['AR']}  CP={scores['CP']}  CR={scores['CR']}")
        if notes:
            print(f"  Notes: {notes}")


if __name__ == "__main__":
    if not RAGAS_AVAILABLE:
        print("ERROR: ragas not available — cannot run RAGAS Monday.")
        sys.exit(1)
    notes = " ".join(sys.argv[1:]) if len(sys.argv) > 1 else ""
    post_monday_row(notes=notes)
