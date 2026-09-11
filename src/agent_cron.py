"""
PPLE Background Learning Daemon.

Runs the recursive self-improvement cycle and data-driven history mining on a
schedule so the agent keeps learning tirelessly: measure accuracy, mine the
latest measurement data for precursor patterns, and tune the learning layer
with a never-regress guardrail. All steps are error-safe - a failing cycle
never kills the daemon.
"""

import datetime
import time

from src.agent_memory import save_chat
from src.agents.self_improvement import RecursiveSelfImprover


def run_learning_cycle() -> dict:
    """Execute one learning iteration: mine history + self-improve."""
    improver = RecursiveSelfImprover()
    summary = {"cycle_at": datetime.datetime.now().isoformat(), "mining": None, "improvement": None}

    # 1. Learn from the latest historical measurement data (best effort)
    try:
        from src.data_loader import get_latest_data, get_data_path, load_mcsa_data

        df = load_mcsa_data(get_data_path("mcsa_updated.csv"))
        if df is None or df.empty:
            df = load_mcsa_data(get_data_path("Report MCSA.xls"))
        if df is not None and not df.empty:
            summary["mining"] = improver.learn_from_history(df)
        else:
            summary["mining"] = {"status": "skipped", "message": "Tidak ada data MCSA aktif.", "lessons_created": 0}
    except Exception as exc:
        summary["mining"] = {"status": "error", "message": str(exc), "lessons_created": 0}

    # 2. Recursive self-improvement cycle (never-regress hill climbing)
    try:
        summary["improvement"] = improver.run_improvement_cycle()
    except Exception as exc:
        summary["improvement"] = {"status": "error", "message": str(exc)}

    # 3. Persist an audit trail in agent memory
    try:
        imp = summary.get("improvement") or {}
        mine = summary.get("mining") or {}
        save_chat(
            "system",
            "SELF-IMPROVE: gen={gen} skor={score} improved={improved} pelajaran_baru={lessons}".format(
                gen=imp.get("generation", "-"),
                score=imp.get("final_score", "-"),
                improved=imp.get("improved", "-"),
                lessons=mine.get("lessons_created", 0),
            ),
        )
    except Exception:
        pass

    return summary


def run_cron_loop(interval_seconds: int = 300):
    """
    Background daemon loop. In production, APScheduler or celery might be used;
    this keeps the repo dependency-free.
    """
    print(f"[{datetime.datetime.now()}] Power Plant Learning Engineering (PPLE) Daemon Started.")
    print(f"Recursive self-improvement engine active (interval: {interval_seconds}s).")

    try:
        while True:
            now = datetime.datetime.now()
            print(f"[{now.strftime('%H:%M:%S')}] PPLE Daemon: menjalankan siklus belajar...")

            try:
                summary = run_learning_cycle()
                imp = summary.get("improvement") or {}
                mine = summary.get("mining") or {}
                print(
                    f"[{now.strftime('%H:%M:%S')}] Siklus selesai: "
                    f"generasi={imp.get('generation', '-')} "
                    f"skor={imp.get('final_score', '-')} "
                    f"membaik={imp.get('improved', '-')} "
                    f"pelajaran_data={mine.get('lessons_created', 0)}"
                )
            except Exception as exc:
                print(f"[{now.strftime('%H:%M:%S')}] Siklus belajar gagal (daemon lanjut): {exc}")

            try:
                from src.automations import run_due_workflows

                automation_runs = run_due_workflows()
                if automation_runs:
                    print(
                        f"[{now.strftime('%H:%M:%S')}] "
                        f"Workflow otomasi diproses: {len(automation_runs)}"
                    )
            except Exception as exc:
                print(f"[{now.strftime('%H:%M:%S')}] Workflow otomasi gagal (daemon lanjut): {exc}")

            time.sleep(interval_seconds)

    except KeyboardInterrupt:
        print("\nPPLE Daemon stopped manually.")


if __name__ == "__main__":
    run_cron_loop()
