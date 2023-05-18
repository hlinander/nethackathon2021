#!/usr/bin/env python3

import db
import math
import time
import sys
import datetime
from dataclasses import dataclass
import argparse
import math


# Gamble på död innan efter utdelning random

TIME_PER_TICK = datetime.timedelta(seconds=2)
START_OF_TIME = datetime.datetime.fromtimestamp(1645291485)

state = dict(
    players = dict()
)

def get_dispatch():
    return dict(
        change_stat=_handle_change_stat,
        buy_stonk=_handle_buy_stonk,
        reach_depth=_handle_reach_depth,
        death=_handle_player_death,
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

    _ensure_player(event)
    # print(event.__dict__)
    if event.name in dispatch:
        dispatch[event.name](event)
    # else:
    #     print(event.__dict__)

    event_handler = get_event_handler()
    event_handler.last_handled_timestamp = max(event.timestamp, event_handler.last_handled_timestamp)

def handle_events(events):
    for event in events:
        handle_event(event)


    # stonk_holding = db.insert_stonk_holding(event.player_id, stonk.id, expires)

def calculate_stonk(player):
    hp = player.get("hp", 0)
    # if hp <= 0:
    #     return 0
    maxhp = player.get("hpmax", hp) + 1
    if maxhp <= 0:
        maxhp = 1
    hunger = player.get("hunger", 0)
    ac = player.get("ac", 0)
    dlevel = player.get("dlevel", 0)
    level = player.get("level", 0)


    hunger_stonk = max(0, (1500 - hunger) / 800.)
    hp_stonk = 1.0 - (hp / maxhp)
    hp_stonk2 = 1.0 - maxhp / 200.
    ac_stonk = 1.0 / (11 - ac)
    dlevel_stonk = dlevel / 60.0
    level_stonk = 1.0 - level / 30.0

    # print("hunger_stonk", hunger_stonk)
    # print("hp_stonk", hp_stonk)
    # print("hp_stonk2", hp_stonk2)
    # print("ac_stonk", ac_stonk)
    # print("dlevel_stonk", dlevel_stonk)
    # print("level_stonk", level_stonk)

    stonk = hunger_stonk * 8 + hp_stonk * 30 + hp_stonk2 * 20 + ac_stonk * 10 + dlevel_stonk * 20 + level_stonk * 20
    return stonk

def stonk_for_player(player):
    return dict(
        # hunger=player.get("hunger", 0),
        # hp=player.get("hp", 0),
        stonk=calculate_stonk(player)
    )

def update_stonks(timestamp):
    for player_id, player in state["players"].items():
        stonks = stonk_for_player(player)
        for stonk_name, stonk_value in stonks.items():
            db.insert_stonk(player_id, stonk_name, stonk_value, timestamp)
    db.session.commit()


def pay_out_stonk(stonk_holding):
    stonk = db.session.query(db.Stonk).filter_by(player_id=stonk_holding.player_id, name=stonk_holding.stonk_name).first()
    turn_fraction = stonk_holding.expires_delta / 250.
    roi = math.ceil(turn_fraction * stonk_holding.fraction * stonk.value)
    db.add_clan_gems_for_clan(stonk_holding.clan_id, roi)
    db.add_transaction(stonk_holding.buy_event_id)
    print(f"Clan {stonk_holding.clan_id} recieved {roi} gems")

    item = db.Event(
        player_id=stonk_holding.player_id,
        clan_id=stonk_holding.clan_id,
        session_start_time=stonk_holding.session_start_time,
        session_turn=1,
        name="payout_stonk",
        extra=dict(
            stonk_player_id=stonk_holding.player_id,
            roi=roi,
            is_long=stonk_holding.long,
        )
        )
    db.session.add(item)
    db.session.commit()
    open("/tmp/payouts", "a").write(f"Clan {stonk_holding.clan_id} recieved {roi} gems. {stonk_holding.__dict__}\n")

def _handle_player_death(event):
    print(f"Player death! {event.__dict__}")
    shorts = db.session.query(db.StonkHolding).filter_by(player_id=event.player_id, session_start_time=event.session_start_time, long=False)
    delete = []
    for short in shorts:
        pay_out_stonk(short)
        delete.append(short.id)

    for d in delete:
        db.delete_holding(d)

def handle_transactions(timestamp):
    delete_holdings = []
    for stonk_holding in db.get_stonk_holdings():
        stonk = db.session.query(db.Stonk).filter_by(player_id=stonk_holding.player_id, name=stonk_holding.stonk_name).first()
        stonk_player_turn = state["players"][str(stonk.player_id)]["last_turn"]
        if stonk_player_turn >= stonk_holding.expires_turn:
            print("After expire turn!")
            buy_event = db.session.query(db.Event).filter_by(id=stonk_holding.buy_event_id).first()
            # print(buy_event.__dict__)
            # import pdb; pdb.set_trace()
            delete_holdings.append(stonk_holding.id)
            if db.get_transaction(buy_event) is None:
                print(stonk_holding.session_start_time, " =?= ", state["players"][str(stonk.player_id)]["current_session"])
                if stonk_holding.session_start_time == state["players"][str(stonk.player_id)]["current_session"]:
                    print("Payed out stonk!")
                    pay_out_stonk(stonk_holding)

    for holding_id in delete_holdings:
        db.delete_holding(holding_id)


def save_state():
    event_handler = get_event_handler()
    event_handler.state = state
    db.session.commit()

def _ensure_player(event):
    if not str(event.player_id) in state["players"]:
        player = db.get_player(event.player_id)
        state["players"][str(event.player_id)] = dict(
            dlevel=1,
            player_name=player.username,
            player_ticker=player.ticker)
    state["players"][str(event.player_id)]["last_turn"] = event.session_turn
    state["players"][str(event.player_id)]["last_event_time"] = event.timestamp.timestamp()
    state["players"][str(event.player_id)]["current_session"] = event.session_start_time

def _handle_reach_depth(event):
    state["players"][str(event.player_id)]["dlevel"] = event.value

# def pay_out_short(stonk_holding):
#     stonk = db.session.query(db.Stonk).filter_by(player_id=stonk_holding.player_id, name=stonk_holding.stonk_name).first()
#     roi = stonk_holding.fraction * stonk.value
#     db.add_clan_gems_for_clan(stonk_holding.clan_id, roi)
#     db.add_transaction(stonk_holding.buy_event_id)
#     print(f"Clan {stonk_holding.clan_id} recieved {roi} gems")

def _handle_change_stat(event):
    if event.string_value not in state["players"][str(event.player_id)]:
        print(f"New stat: {event.string_value}")
    state["players"][str(event.player_id)][event.string_value] = event.value



def _handle_buy_stonk(event):
    stonk_player_id = event.extra["stonk_player_id"]
    stonk_name = event.extra["stonk_name"]
    stonk = db.get_stonk(stonk_player_id, stonk_name)
    expires_delta = event.extra["expires_delta"]
    spent_gems = event.extra["spent_gems"]
    stonk_player_turn = state["players"][str(stonk_player_id)]["last_turn"]
    buy_long = event.extra["buy_long"]

    # event.session_start_time = state["players"][event.player_id]
    stonk_holding = db.buy_stonk(event,
                                 state["players"][str(stonk_player_id)]["current_session"],
                                 stonk_player_id,
                                 stonk_name,
                                 spent_gems,
                                 stonk_player_turn + expires_delta,
                                 expires_delta,
                                 buy_long)

    # pay_out_stonk(stonk_holding)


def event_loop(once=False):
    global TIME_PER_TICK
    event_handler = get_event_handler()
    next_tick_time = event_handler.last_handled_timestamp + TIME_PER_TICK
    std_out_time = datetime.datetime.utcnow()
    while True:
        while datetime.datetime.utcnow() > next_tick_time:
            if datetime.datetime.utcnow() - next_tick_time > datetime.timedelta(minutes=30):
                TIME_PER_TICK = datetime.timedelta(minutes=30)
            else:
                TIME_PER_TICK = datetime.timedelta(seconds=2)

            if datetime.datetime.utcnow() > std_out_time:
                std_out_time = datetime.datetime.utcnow() + datetime.timedelta(seconds=5)
                # print(next_tick_time)

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
            print(f"Unhandled events: {unhandled_events.count()}")
            handle_events(unhandled_events)
            update_stonks(next_tick_time)
            handle_transactions(next_tick_time)
            save_state()
            event_handler.last_handled_timestamp = next_tick_time
            next_tick_time += TIME_PER_TICK
            if once:
                return

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


def reload_state():
    global state
    event_handler = get_event_handler()
    state = event_handler.state
    # print(state)


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
        event_loop(once=True)
    else:
        reload_state()
        event_loop()
