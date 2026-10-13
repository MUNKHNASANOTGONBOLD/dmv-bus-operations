"""Export route-hour observations and pipeline health to CSV for Power BI/Tableau."""
import argparse
import csv
from pathlib import Path
import sqlite3

def write_csv(db,query,path):
    cursor=db.execute(query)
    with path.open('w',newline='',encoding='utf-8') as handle:
        writer=csv.writer(handle)
        writer.writerow([item[0] for item in cursor.description])
        writer.writerows(cursor)

if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--db',default='data/wmata.sqlite')
    parser.add_argument('--out',default='exports')
    args=parser.parse_args()
    if not Path(args.db).is_file():
        parser.error('Database not found. Collect a real snapshot first.')
    out=Path(args.out)
    out.mkdir(parents=True,exist_ok=True)
    with sqlite3.connect(f'file:{Path(args.db).resolve()}?mode=ro',uri=True) as db:
        write_csv(db,(Path(__file__).parent/'sql/route_hour.sql').read_text(),out/'route_hour.csv')
        write_csv(db,'SELECT poll_id,fetched_at_utc,status,http_status,row_count,error FROM polls ORDER BY poll_id',out/'pipeline_health.csv')
    print(f'Exported to {out}')