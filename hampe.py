import random
import curses
from curses import wrapper
import time
import traceback
import db
import sys
import json
import os

NETHACK = "/home/nethack/nh/install/games/lib/nethackdir/"
NETHACK_BIN = os.path.join(NETHACK, "nethack")

username = ""
player_id = None


def handle_login(states, stdscr):
    global username, player_id
    result = db.login(states["login"]["buffer"], states["password"]["buffer"])
    stdscr.addstr(6, 8, result["status"])
    if result["logged_in"]:
        username = states["login"]["buffer"]
        player_id = result["player_id"]
        stdscr.addstr(7, 8, "Press any key to face the dungeon of doom")
        return "play"
    else:
        states["login"]["buffer"] = ""
        states["password"]["buffer"] = ""
        return "login"

def handle_play(states, stdscr):
    ttydir = os.path.join(NETHACK, "ttyrec", username)
    os.makedirs(ttydir, exist_ok=True)
    ttyfile = os.path.join(ttydir, str(random.randint(0, 100000)))
    command = f"ovh-ttyrec/ttyrec -f {ttyfile}_{player_id}.ttyrec -- sh -c 'DB_USER_ID={player_id} {NETHACK_BIN} -u {username}'"
    #command = f"sh -c 'DB_USER_ID={player_id} {NETHACK_BIN} -u {username}'"
    open("cmd", "w").write(command)
    os.system(command)
    return "play"


states = dict(
    login=dict(prompt=True, prompt_text="username: ", y=5, buffer="", next_state = "password"),
    password=dict(prompt=True, prompt_text="password: ", y=5, buffer="", next_state = "validate"),
    validate=dict(prompt=False, func=handle_login, buffer="", next_state="play"),
    play=dict(prompt=False, func=handle_play, buffer="", next_state="play")
)


def main(stdscr):
    db.open_db()
    stdscr.clear()
    curses.noecho()
    curses.start_color()
    curses.use_default_colors()
    curses.init_pair(1, curses.COLOR_WHITE, curses.COLOR_BLACK)
    curses.init_pair(2, curses.COLOR_WHITE, curses.COLOR_GREEN)
    curses.init_pair(3, curses.COLOR_WHITE, curses.COLOR_RED)
    no_color = curses.color_pair(1)
    selection_color = curses.color_pair(2)
    error_color = curses.color_pair(3)
    username = ""
    password = ""
    buffer = ""
    current_state = "login"

    while True:
        #stdscr.addstr(0, 0, banner)
        stdscr.addstr(0, 0, "Nethackathon 2021")
        if "func" in states[current_state]:
            open("state","a").write(current_state)
            current_state = states[current_state]["func"](states, stdscr)
            open("state","a").write(current_state)
        open("state","a").write(current_state)
        if states[current_state]["prompt"]:
            stdscr.addstr(states[current_state]["y"], 8, states[current_state]["prompt_text"])
            stdscr.addstr(states[current_state]["y"] + 1, 8, " "*20)
            stdscr.addstr(states[current_state]["y"] + 1, 8, states[current_state]["buffer"])

        stdscr.refresh()
        v = stdscr.getch()
        if -1 == v:
            continue
        if v == 263: # Backspace
            states[current_state]["buffer"] = states[current_state]["buffer"][:-1]
        elif v == 10:
            current_state = states[current_state]["next_state"]
            stdscr.clear()
        else:
            states[current_state]["buffer"] += chr(v)

wrapper(main)
