"""Synthetic ingestion tests only. These fixtures are not portfolio findings."""
import sqlite3
import unittest
from pathlib import Path
from collector import initialize,ingest

class PipelineTests(unittest.TestCase):
    def setUp(self):
        self.db=sqlite3.connect(':memory:')
        initialize(self.db)
    def tearDown(self):
        self.db.close()
    def test_repeated_polls_do_not_weight_hourly_indicator(self):
        row={'VehicleID':'TEST','RouteID':'TEST','TripID':'TEST','DateTime':'2026-10-09T12:01:00','Deviation':10}
        for _ in range(3):
            ingest(self.db,{'BusPositions':[row]},'2026-10-09T16:02:00+00:00')
        row2=dict(row,VehicleID='TEST2',Deviation=None)
        ingest(self.db,{'BusPositions':[row2]},'2026-10-09T16:02:00+00:00')
        sql=(Path(__file__).parents[1]/'sql/route_hour.sql').read_text()
        result=self.db.execute(sql).fetchone()
        self.assertEqual(result[2:],(2,1,10.0,1,100.0))
    def test_empty_feed_and_invalid_schema(self):
        self.assertEqual(ingest(self.db,{'BusPositions':[]},'2026-10-09T16:00:00+00:00'),0)
        with self.assertRaises(ValueError):
            ingest(self.db,{'error':'bad key'},'2026-10-09T16:00:00+00:00')
        self.assertEqual(self.db.execute('SELECT count(*) FROM polls').fetchone()[0],1)

if __name__=='__main__':
    unittest.main()
