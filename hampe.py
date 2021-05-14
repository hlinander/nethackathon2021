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

banner = r'''             _,---.      ,----.         ___                    
         _.='.'-,  \  ,-.--` , \ .-._ .'=.'\                   
        /==.'-     / |==|-  _.-`/==/ \|==|  |                  
       /==/ -   .-'  |==|   `.-.|==|,|  / - |                  
       |==|_   /_,-./==/_ ,    /|==|  \/  , |                  
       |==|  , \_.' )==|    .-' |==|- ,   _ |                  
       \==\-  ,    (|==|_  ,`-._|==| _ /\   |                  
        /==/ _  ,  //==/ ,     //==/  / / , /                  
        `--`------' `--`-----`` `--`./  `--`                   
   ,-,--.  ,--.--------.   _,.---._                    ,----.  
 ,-.'-  _\/==/,  -   , -\,-.' , -  `.   .-.,.---.   ,-.--` , \ 
/==/_ ,_.'\==\.-.  - ,-./==/_,  ,  - \ /==/  `   \ |==|-  _.-` 
\==\  \    `--`\==\- \ |==|   .=.     |==|-, .=., ||==|   `.-. 
 \==\ -\        \==\_ \|==|_ : ;=:  - |==|   '='  /==/_ ,    / 
 _\==\ ,\       |==|- ||==| , '='     |==|- ,   .'|==|    .-'  
/==/\/ _ |      |==|, | \==\ -    ,_ /|==|_  . ,'.|==|_  ,`-._ 
\==\ - , /      /==/ -/  '.='. -   .' /==/  /\ ,  )==/ ,     / 
 `--`---'       `--`--`    `--`--''   `--`-`--`--'`--`-----``  
'''

username = ""
player_id = None


def handle_login(states, stdscr):
    global username, player_id
    result = db.login(states["login"]["buffer"], states["password"]["buffer"])
    stdscr.addstr(24, 8, result["status"])
    if result["logged_in"]:
        username = states["login"]["buffer"]
        player_id = result["player_id"]
        stdscr.addstr(26, 8, "Press any key to face the dungeon of doom")
        return "play"
    else:
        states["login"]["buffer"] = ""
        states["password"]["buffer"] = ""
        return "login"

def handle_play(states, stdscr):
    ttydir = os.path.join(NETHACK, "ttyrec", username)
    os.makedirs(ttydir, exist_ok=True)
    ttyfile = os.path.join(ttydir, str(random.randint(0, 1000)))
    command = f"ovh-ttyrec/ttyrec -f {ttyfile}.ttyrec -- sh -c 'DB_USER_ID={player_id} {NETHACK_BIN} -u {username}'"
    open("cmd", "w").write(command)
    os.system(command)
    sys.exit()


states = dict(
    login=dict(prompt=True, prompt_text="username: ", y=20, buffer="", next_state = "password"),
    password=dict(prompt=True, prompt_text="password: ", y=20, buffer="", next_state = "validate"),
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
        stdscr.addstr(0, 0, banner)
            # stdscr.addstr(it['y'], it['x'], it['name'] + ':')
            # stdscr.addstr(it['y'], it['x'] + 5, '%02d' % (it['lvl']), c)
            # stdscr.addstr(23, 8, f"Cost to upgrade: {cost(menu[selection]['lvl']):03d}")
            # stdscr.addstr(23, 32, f'Team Power gems: {power_gems:03d}')
            # stdscr.addstr(24, 8, error, error_color)
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
        #try:
        v = stdscr.getch()
        if -1 == v:
            continue
        if v == 263: # Backspace
            states[current_state]["buffer"] = states[current_state]["buffer"][:-1]
        elif v == 10:
            open("state", "w").write(current_state)
            current_state = states[current_state]["next_state"]
            open("state", "a").write(current_state)
            stdscr.clear()
            # Enter
        else:
            states[current_state]["buffer"] += chr(v)
        #raise Exception(v)

        #except Exception as e:
        #    open('/tmp/fisk', 'w').write(str(e) + '\n' + traceback.format_exc())

wrapper(main)
