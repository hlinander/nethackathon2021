#!/usr/bin/env python3

import db
import math
import time
import sys
import datetime
from dataclasses import dataclass
import argparse


TIME_PER_TICK = datetime.timedelta(seconds=2)
START_OF_TIME = datetime.datetime.fromtimestamp(1645291485)

state = dict(
    players = dict()
)
players = state["players"]

def get_dispatch():
    return dict(change_stat=_handle_change_stat)


def timestamp_to_tick(timestamp):
    return math.floor((timestamp - START_OF_TIME) / TIME_PER_TICK)

def tick_to_timestamp_range(tick):
    return (tick * TIME_PER_TICK, (tick + 1) * TIME_PER_TICK)

def get_event_handler():
    event_handler = db.session.query(db.EventHandler).first()
    if event_handler is None:
        event_handler = db.EventHandler(
            last_handled_timestamp = START_OF_TIME
        )
        db.session.add(event_handler)
        db.session.commit()

    return event_handler


def get_events_between(start_inclusive, stop):
    event_handler = get_event_handler()
    events = db.session.query(db.Event).filter(db.Event.timestamp >= start_inclusive).filter(db.Event.timestamp < stop)
    return events

def handle_event(event):
    dispatch = get_dispatch()

    if event.name in dispatch:
        dispatch[event.name](event)
    else:
        print(event.__dict__)

    event_handler = get_event_handler()
    event_handler.last_handled_timestamp = max(event.timestamp, event_handler.last_handled_timestamp)
    db.session.commit()

def handle_events(events):
    for event in events:
        handle_event(event)


def stonk_for_player(player):
    return dict(
        hunger=player.get("hunger", 0),
        hp=player.get("hp", 0)
    )

def update_stonks(timestamp):
    for player_id, player in state["players"].items():
        stonks = stonk_for_player(player)
        for stonk_name, stonk_value in stonks.items():
            db.insert_stonk(player_id, stonk_name, stonk_value, timestamp)
    db.session.commit()


def save_state():
    event_handler = get_event_handler()
    event_handler.state = state
    db.session.commit()

def _handle_change_stat(event):
    data = event.__dict__.copy()
    if not event.player_id in players:
        players[event.player_id] = dict()
    players[event.player_id][event.string_value] = event.value
    print(players)


def event_loop():
    event_handler = get_event_handler()
    next_tick_time = event_handler.last_handled_timestamp + TIME_PER_TICK
    while True:
        while datetime.datetime.now() > next_tick_time:
            # time.sleep(TIME_PER_TICK)
            sys.stdout.write(".")
            sys.stdout.flush()
            unhandled_events = get_events_between(event_handler.last_handled_timestamp, next_tick_time)
            handle_events(unhandled_events)
            update_stonks(next_tick_time)
            save_state()
            event_handler.last_handled_timestamp = next_tick_time
            next_tick_time += TIME_PER_TICK

        time.sleep(TIME_PER_TICK)

def reset_last_handled_timestamp():
    event_handler = get_event_handler()
    event_handler.last_handled_timestamp = db.session.query(db.Event).order_by(db.Event.timestamp).first().timestamp
    db.reset_stonks()
    db.session.commit()

def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument("--reset", action="store_true")
    args = parser.parse_args()
    return args

if __name__ == "__main__":
    args = parse_args()
    db.open_db()
    if args.reset:
        reset_last_handled_timestamp()
    event_loop()
