#!/usr/bin/env python3

import jens
import db
import datetime
import time
import sys

db.open_db()
while True:
    hunger = db.get_stonk(1, "hunger", 100, datetime.datetime.utcnow() - datetime.timedelta(minutes=1), datetime.datetime.utcnow())
    hp = db.get_stonk(1, "hp", 100, datetime.datetime.utcnow() - datetime.timedelta(minutes=1), datetime.datetime.utcnow())
    jens.clear()
    jens.chart_in_box(10, 1, 100, 20, hunger, "hunger", 1)
    jens.chart_in_box(10, 25, 100, 20, hp, "hp", 1)
    sys.stdout.flush()
    time.sleep(1)
