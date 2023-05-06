#!/usr/bin/env python3

import os
import oldjens
import db
import datetime
import observer
import time
import sys
import session


def get_stonks():
    stonk_defs = db.session.query(db.Stonk).distinct(db.Stonk.player_id, db.Stonk.name)
    
    # all_stonks = []
    # for stonk_id, value in investment_by_stonk_id:
    #     stonk = (db.session.query(db.Stonk)
    #             .filter_by(id=stonk_id)).first()
    #     all_stonks.append(stonk)

    all_stonks = []
    for stonk in stonk_defs:
        player = db.get_player(stonk.player_id)
        all_stonks.append({
            'player_id': stonk.player_id,
            'player_name': player.username,
            'stonk_name': stonk.name,
            'investment': 0,
            'series': None
        })
        

    return all_stonks

def interest_level(stonk, player_states):
    is_active = True
    if stonk['player_id'] in player_states:
        player_state = player_states[stonk['player_id']] 
        if 'last_event_time' in player_state:
            time_since_last = time.time() - player_state['last_event_time']
            if time_since_last > 60:
                is_active = False

    value = stonk['investment'] + 0.1
    if not is_active:
        value *= 0.1
    return value

last_live_time = {}

def choose_on_display(on_display, all_stonks):
    player_states = session.get_state()['players']
    holdings = db.session.query(db.StonkHolding)
    investment_by_stonk_id = {}
    for holding in holdings:
        investment = 0
        if (holding.player_id, holding.stonk_name) in investment_by_stonk_id:
            investment = investment_by_stonk_id[(holding.player_id, holding.stonk_name)]
        investment += holding.fraction
        investment_by_stonk_id[(holding.player_id, holding.stonk_name)] = investment

    for stonk in all_stonks:
        investment = 0
        if (stonk['player_id'], stonk['stonk_name']) in investment_by_stonk_id:
            investment = investment_by_stonk_id[(stonk['player_id'], stonk['stonk_name'])]
        stonk['investment'] = investment

    sorted_stonks = sorted(all_stonks, reverse=True, key=lambda x: x['investment'])
	
    sorted_not_displayed = list(filter(lambda x: not any(o['stonk']['player_id'] == x['player_id'] and o['stonk']['stonk_name'] == x['stonk_name'] for o in on_display), sorted_stonks))

    for i in range(4):
        if len(on_display) <= i:
            if len(sorted_not_displayed) > 0:
                on_display.append( {
                    'stonk': sorted_not_displayed[0],
                    'live_at': time.time(),
                })
                del sorted_not_displayed[0]
        else:
            current = on_display[i]
            stonk = current['stonk']
            last_live_time[(stonk['player_id'], stonk['stonk_name'])] = time.time()
            time_live = time.time() - current['live_at']
            if time_live > 10:
                current_interest_level = interest_level(current['stonk'], player_states)
                current_interest_level *= 1.0 - min(time_live / 60.0, 1.0) * 0.85
                if len(sorted_not_displayed) > 0:
                    other = sorted_not_displayed[0]
                    other_interest_level = interest_level(other, player_states)
                    other_last_live_time = 0
                    if (stonk['player_id'], stonk['stonk_name']) in last_live_time:
                        other_last_live_time = last_live_time[(stonk['player_id'], stonk['stonk_name'])]
                    
                    time_since_other_live = time.time() - other_last_live_time
                    other_interest_level *= 1.0 - max(min(time_since_other_live / 360, 1.0), 0.0) * 0.25
                    if other_interest_level > current_interest_level:
                        # check if something is more interesting
                        on_display[i] = {
                            'stonk': other,
                            'live_at': time.time(),
                        }
                        del sorted_not_displayed[0]

    for i in range(4):
        if len(on_display) > i:
            on_display[i]['x'] = 1 + (i & 1) * (observer.MON_W + 2) + (i&1)
            on_display[i]['y'] = 1 + (i >> 1) * (observer.MON_H + 1) + (i>>1)

observer.set_4x4_size()
db.open_db()
on_display = []
while True:
    oldjens.clear()
    all_stonks = get_stonks()
    choose_on_display(on_display, all_stonks)

    for i, display in enumerate(on_display):
        it = display['stonk']
        name = it['player_name'] + " " + it['stonk_name'] + " " + str(it['investment'])
        series = db.get_stonk_series(it['player_id'], it['stonk_name'], observer.MON_W, datetime.datetime.utcnow() - datetime.timedelta(minutes=5), datetime.datetime.utcnow()),
        oldjens.chart_in_box(display['x'], display['y'], observer.MON_W, observer.MON_H, series[0], name, 1)
    sys.stdout.flush()
    time.sleep(1)
