"""Build a small sanitized SQLite preview from the local WMATA database.

Usage: python make_sample_db.py --source data/wmata.sqlite --out wmata-sample.sqlite
The public preview removes raw JSON payloads and uses only a small subset of polls.
Never commit the full database or credentials.
"""
import argparse
import sqlite3
from pathlib import Path

def build(source, output, polls=8, per_poll=100):
    output=Path(output)
    if output.exists():
        raise FileExistsError(f"Refusing to overwrite: {output}")
    with sqlite3.connect(f"file:{Path(source).resolve()}?mode=ro",uri=True) as src, sqlite3.connect(output) as dst:
        for (sql,) in src.execute("SELECT sql FROM sqlite_master WHERE type='table' AND name IN ('polls','positions') ORDER BY name"):
            dst.execute(sql)
        ids=[r[0] for r in src.execute("SELECT poll_id FROM polls WHERE status='ok' ORDER BY poll_id LIMIT ?",(polls,))]
        for poll_id in ids:
            row=src.execute("SELECT poll_id,fetched_at_utc,status,http_status,row_count,error FROM polls WHERE poll_id=?",(poll_id,)).fetchone()
            dst.execute("INSERT INTO polls VALUES (?,?,?,?,?,?,NULL)",row)
            for pos in src.execute("SELECT poll_id,row_number,vehicle_id,route_id,trip_id,source_time_local,direction,lat,lon,deviation_min FROM positions WHERE poll_id=? LIMIT ?",(poll_id,per_poll)):
                dst.execute("INSERT INTO positions VALUES (?,?,?,?,?,?,?,?,?,?,?)",(*pos,'{}'))
        dst.execute("CREATE INDEX IF NOT EXISTS idx_route ON positions(route_id,source_time_local)")
        dst.commit()

if __name__=='__main__':
    p=argparse.ArgumentParser()
    p.add_argument('--source',default='data/wmata.sqlite')
    p.add_argument('--out',default='wmata-sample.sqlite')
    p.add_argument('--polls',type=int,default=8)
    p.add_argument('--per-poll',type=int,default=100)
    a=p.parse_args()
    build(a.source,a.out,a.polls,a.per_poll)
    print(f'Created sanitized sample: {a.out}')
