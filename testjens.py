#!/usr/bin/env python3

import jens
import db
import datetime

db.open_db()
hunger = db.get_stonk(1, "hunger", 100, datetime.datetime.now() - datetime.timedelta(hours=20), datetime.datetime.now())
hp = db.get_stonk(1, "hp", 100, datetime.datetime.now() - datetime.timedelta(hours=20), datetime.datetime.now())
jens.chart_in_box(10, 10, 100, 20, hunger, "hunger", 1)
jens.chart_in_box(10, 35, 100, 20, hp, "hp", 1)
input()
