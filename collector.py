"""WMATA raw snapshot collector. Python 3.11+; no third-party dependencies."""
import argparse
import json
import os
from pathlib import Path
import sqlite3
import sys
import time
from datetime import datetime, timezone
from urllib.request import Request, urlopen
from urllib.error import HTTPError, URLError

ENDPOINT = 'https://api.wmata.com/Bus.svc/json/jBusPositions'

def initialize(db):
    db.executescript('''
    CREATE TABLE IF NOT EXISTS polls (
      poll_id INTEGER PRIMARY KEY, fetched_at_utc TEXT NOT NULL,
      status TEXT NOT NULL, http_status INTEGER, row_count INTEGER,
      error TEXT, raw_json TEXT);
    CREATE TABLE IF NOT EXISTS positions (
      poll_id INTEGER NOT NULL REFERENCES polls(poll_id),
      row_number INTEGER NOT NULL, vehicle_id TEXT, route_id TEXT,
      trip_id TEXT, source_time_local TEXT, direction TEXT,
      lat REAL, lon REAL, deviation_min REAL, raw_json TEXT NOT NULL,
      PRIMARY KEY (poll_id,row_number));
    CREATE INDEX IF NOT EXISTS idx_route ON positions(route_id,source_time_local);
    ''')

def numeric(value):
    try:
        result = float(value)
        return result if abs(result) < float('inf') else None
    except (TypeError, ValueError):
        return None

def ingest(db, payload, fetched_at):
    if not isinstance(payload, dict) or not isinstance(payload.get('BusPositions'), list):
        raise ValueError('Expected a BusPositions array; raw schema needs review.')
    rows = payload['BusPositions']
    if any(not isinstance(row, dict) for row in rows):
        raise ValueError('Expected position objects.')
    with db:
        cursor = db.execute('INSERT INTO polls(fetched_at_utc,status,http_status,row_count,raw_json) VALUES (?, ?, 200, ?, ?)',
                            (fetched_at, 'ok', len(rows), json.dumps(payload)))
        poll_id = cursor.lastrowid
        for i, row in enumerate(rows):
            db.execute('INSERT INTO positions VALUES (?,?,?,?,?,?,?,?,?,?,?)',
                       (poll_id,i,row.get('VehicleID'),row.get('RouteID'),row.get('TripID'),
                        row.get('DateTime'),row.get('DirectionText'),numeric(row.get('Lat')),
                        numeric(row.get('Lon')),numeric(row.get('Deviation')),json.dumps(row)))
    return len(rows)

def collect(db, key):
    fetched_at = datetime.now(timezone.utc).isoformat()
    try:
        # Credentials stay in the request header and are never saved in the database.
        request = Request(ENDPOINT, headers={'api_key': key, 'Accept': 'application/json'})
        with urlopen(request, timeout=30) as response:
            payload = json.load(response)
        count = ingest(db,payload,fetched_at)
        print(f'{fetched_at}: stored {count} positions',flush=True)
    except (HTTPError,URLError,ValueError,TimeoutError) as exc:
        status = exc.code if isinstance(exc,HTTPError) else None
        # Do not log response bodies or exception URLs that might disclose credentials.
        message = f'{type(exc).__name__}: HTTP {status}' if status else type(exc).__name__
        with db:
            db.execute('INSERT INTO polls(fetched_at_utc,status,http_status,error) VALUES (?, ?, ?, ?)',
                       (fetched_at,'error',status,message))
        print(f'{fetched_at}: {message}',file=sys.stderr,flush=True)
        return False
    return True

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--db',default='data/wmata.sqlite')
    parser.add_argument('--polls',type=int,default=1,help='Finite poll count; default one request')
    parser.add_argument('--interval',type=int,default=60,help='Seconds between requests; verify your subscription limits')
    args=parser.parse_args()
    if args.polls < 1 or args.interval < 30:
        parser.error('polls must be positive and interval must be at least 30 seconds')
    key=os.environ.get('WMATA_API_KEY')
    if not key:
        parser.error('Set WMATA_API_KEY in your local environment. Do not commit or share it.')
    Path(args.db).parent.mkdir(parents=True,exist_ok=True)
    db=sqlite3.connect(args.db)
    initialize(db)
    success=True
    try:
        for i in range(args.polls):
            ok=collect(db,key)
            success=success and ok
            if not ok:
                break  # Stop on auth, quota, network or schema failures; review before restarting.
            if i+1 < args.polls:
                time.sleep(args.interval)
    finally:
        db.close()
    return 0 if success else 1

if __name__=='__main__':
    sys.exit(main())