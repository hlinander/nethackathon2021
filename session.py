#!/usr/bin/env python3

import db
import event_handler

SESSION = None

def ensure_db():
    global SESSION
    if SESSION is None:
        SESSION = db.open_db()

def get_state():
    ensure_db()
    eh = event_handler.get_event_handler()
    return eh.state

def get_player_state(player_id):
    ensure_db()
    eh = event_handler.get_event_handler()
    return eh.state["players"][str(player_id)]
