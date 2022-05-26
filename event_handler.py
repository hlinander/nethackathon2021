#!/usr/bin/env python3

import db
import math
import time
import sys
import datetime
from dataclasses import dataclass
import argparse


# Gamble på död innan efter utdelning random

TIME_PER_TICK = datetime.timedelta(seconds=2)
START_OF_TIME = datetime.datetime.fromtimestamp(1645291485)

state = dict(
    players = dict()
)
players = state["players"]

def get_dispatch():
    return dict(
        change_stat=_handle_change_stat,
        buy_stonk=_handle_buy_stonk,
        reach_depth=_handle_reach_depth,
    )


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

def get_latest_before(time):
    event_handler = get_event_handler()
    events = db.session.query(db.Event).filter(db.Event.timestamp <= time).order_by(db.Event.timestamp.desc())
    return events.first()

def get_earliest_after(time):
    event_handler = get_event_handler()
    events = db.session.query(db.Event).filter(db.Event.timestamp >= time).order_by(db.Event.timestamp)
    return events.first()

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


    # stonk_holding = db.insert_stonk_holding(event.player_id, stonk.id, expires)

def calculate_stonk(player):
    hp = player.get("hp", 0)
    if hp <= 0:
        return 0
    maxhp = player.get("hpmax", 0) + 1
    hunger = player.get("hunger", 0)
    ac = player.get("ac", 0)
    dlevel = player.get("dlevel", 0)
    level = player.get("level", 0)


    hunger_stonk = (1500 - hunger) / 800.
    hp_stonk = 1.0 - (hp / maxhp)
    hp_stonk2 = 1.0 - maxhp / 200.
    ac_stonk = 1.0 / (11 - ac)
    dlevel_stonk = dlevel / 60.0
    level_stonk = 1.0 - level / 30.0

    print("hunger_stonk", hunger_stonk)
    print("hp_stonk", hp_stonk)
    print("hp_stonk2", hp_stonk2)
    print("ac_stonk", ac_stonk)
    print("dlevel_stonk", dlevel_stonk)
    print("level_stonk", level_stonk)

    stonk = hunger_stonk * 8 + hp_stonk * 30 + hp_stonk2 * 20 + ac_stonk * 10 + dlevel_stonk * 20 + level_stonk * 20
    return stonk

def stonk_for_player(player):
    return dict(
        hunger=player.get("hunger", 0),
        hp=player.get("hp", 0),
        stonk=calculate_stonk(player)
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

def _handle_reach_depth(event):
    if not event.player_id in players:
        player = db.get_player(event.player_id)
        players[event.player_id] = dict(
            player_name=player.username,
            player_ticker=player.ticker)
    players[event.player_id]["dlevel"] = event.value

def _handle_change_stat(event):
    data = event.__dict__.copy()
    if not event.player_id in players:
        player = db.get_player(event.player_id)
        players[event.player_id] = dict(
            player_name=player.username,
            player_ticker=player.ticker)
    players[event.player_id][event.string_value] = event.value
    # players[event.player_id]["name"] =
    print(players)

def _handle_buy_stonk(event):
    stonk_player_id = event.extra["stonk_player_id"]
    stonk_name = event.extra["stonk_name"]
    stonk = db.get_stonk(stonk_player_id, stonk_name)
    expires = event.extra["expires_delta"]

    stonk_holding = db.buy_stonk(event.player_id, stonk_player_id, stonk_name, expires)
    if stonk_holding is None:
        print("Couldn't buy a stonk!")


def event_loop():
    event_handler = get_event_handler()
    next_tick_time = event_handler.last_handled_timestamp + TIME_PER_TICK
    std_out_time = datetime.datetime.utcnow()
    while True:
        while datetime.datetime.utcnow() > next_tick_time:
            if datetime.datetime.utcnow() > std_out_time:
                std_out_time = datetime.datetime.utcnow() + datetime.timedelta(seconds=5)
                print(next_tick_time)

            unhandled_events = get_events_between(event_handler.last_handled_timestamp, next_tick_time)
            if unhandled_events.first() is None:
                latest_before = get_latest_before(next_tick_time)
                earliest_after = get_earliest_after(next_tick_time)
                if earliest_after is None:
                    next_tick_time = datetime.datetime.utcnow()
                if latest_before is not None and earliest_after is not None:
                    delta = earliest_after.timestamp - latest_before.timestamp
                    if delta > datetime.timedelta(days=1):
                        next_tick_time = earliest_after.timestamp
                        print(f"Updating empty delta {delta}")
            handle_events(unhandled_events)
            update_stonks(next_tick_time)
            save_state()
            event_handler.last_handled_timestamp = next_tick_time
            next_tick_time += TIME_PER_TICK

        time.sleep(TIME_PER_TICK.total_seconds())

def reset_last_handled_timestamp():
    event_handler = get_event_handler()
    first_event = db.session.query(db.Event).order_by(db.Event.timestamp).first()
    if first_event is not None:
        event_handler.last_handled_timestamp = first_event.timestamp
    else:
        event_handler.last_handled_timestamp = datetime.datetime.utcnow()
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
