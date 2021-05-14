import curses
from curses import wrapper
import time
import traceback
import db
import sys
import json

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

STARTOFF = 8
DISTANCE = 18

menu = [
        { 'name': 'ads', 'print': 'Disable ADs!', 'x': STARTOFF, 'y': 18, 'lvl': 0, 'type': 'toggle' },
        { 'name': 'bag', 'print': 'Bag slots', 'x': STARTOFF+DISTANCE*0, 'y': 19, 'lvl': 0 },
        { 'name': 'helm', 'print': 'Keep Helm', 'x': STARTOFF+DISTANCE*1, 'y': 19, 'lvl': 0, 'type': 'toggle' },
        { 'name': 'body', 'print': 'Keep Armor', 'x': STARTOFF+DISTANCE*2, 'y': 19, 'lvl': 0, 'type': 'toggle' },
        { 'name': 'cloak', 'print': 'Keep Cloak', 'x': STARTOFF+DISTANCE*0, 'y': 20, 'lvl': 0, 'type': 'toggle' },
        { 'name': 'gloves', 'print': 'Keep Gloves', 'x': STARTOFF+DISTANCE*1, 'y': 20, 'lvl': 0, 'type': 'toggle' },
        { 'name': 'boots', 'print': 'Keep Boots', 'x': STARTOFF+DISTANCE*2, 'y': 20, 'lvl': 0, 'type': 'toggle' },
        { 'name': 'hp', 'x': STARTOFF+DISTANCE*0, 'y': 21, 'lvl': 0 },
        { 'name': 'pw', 'x': STARTOFF+DISTANCE*1, 'y': 21, 'lvl': 0 },
        { 'name': 'ac', 'x': STARTOFF+DISTANCE*2, 'y': 21, 'lvl': 0 },
        { 'name': 'str', 'x': STARTOFF+DISTANCE*0, 'y': 22, 'lvl': 0 },
        { 'name': 'int', 'x': STARTOFF+DISTANCE*1, 'y': 22, 'lvl': 0 },
        { 'name': 'wis', 'x': STARTOFF+DISTANCE*2, 'y': 22, 'lvl': 0 },
        { 'name': 'dex', 'x': STARTOFF+DISTANCE*0, 'y': 23, 'lvl': 0 },
        { 'name': 'con', 'x': STARTOFF+DISTANCE*1, 'y': 23, 'lvl': 0 },
        { 'name': 'cha', 'x': STARTOFF+DISTANCE*2, 'y': 23, 'lvl': 0 },
]

def cost(it):
    if it['name'] in ['hp', 'pw']:
        return 2
    elif it['name'] in ['str', 'int', 'wis', 'dex', 'con', 'cha', 'bag']:
        return 10
    elif it['name'] in ['ac']:
        return 30
    else:
        return 50

def update_power_levels(player_id):
    powers = db.get_clan_powers_for_player(player_id)
    for power, level in powers.items():
        for idx, item in enumerate(menu):
            if item["name"] == power:
                    menu[idx]['lvl'] = level

def main(stdscr):
    player_id = int(sys.argv[1])
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

    selection = 0
    error = ""
    power_gems = db.get_power_gems_for_player(player_id)
    open("log", "a").write(json.dumps(menu, indent=4))


    while True:
        power_gems = db.get_power_gems_for_player(player_id)
        update_power_levels(player_id)
        stdscr.addstr(0, 0, banner)
        for i in range(0, len(menu)):
            it = menu[i]
            c = no_color if (i != selection) else selection_color
            stdscr.addstr(it['y'], it['x'], (it['print'] if 'print' in it else it['name'].upper()) + ':')
            if 'type' not in it:
                stdscr.addstr(it['y'], it['x'] + 13, '%03d' % (it['lvl']), c)
            else:
                stdscr.addstr(it['y'], it['x'] + 13, '[%s]' % (' ' if 0 == it['lvl'] else 'X'), c)
            stdscr.addstr(24, 8, f"Cost to upgrade: {cost(menu[selection]):03d}")
            stdscr.addstr(24, 32, f'Team Power gems: {power_gems:03d}')
            if len(error):
                stdscr.addstr(18, 38, error, error_color)
            else:
                stdscr.addstr(18, 38, " " * 30)
            stdscr.move(menu[selection]['y'], menu[selection]['x'])
            stdscr.refresh()
        v = stdscr.getch()
        if -1 == v:
            continue
        n = chr(v).lower()
        if 'h' == n:
            selection -= 1
        elif 'l' == n:
            selection += 1
        elif 'k' == n:
            selection -= 3
        elif 'j' == n:
            if 0 == selection:
                selection += 1
            else:
                selection += 3
        elif ' ' == n:
            thecost = cost(menu[selection])
            if power_gems >= thecost:
                if 'type' in menu[selection]:
                    menu[selection]['lvl'] ^= 1
                else:
                    menu[selection]['lvl'] += 1
                dlevel = db.add_clan_power_for_player(
                        player_id,
                        menu[selection]['name'],
                        menu[selection]['lvl'],
                        thecost)
                menu[selection]['lvl'] = dlevel
                error = ""
            else:
                error = "Not enough power gems!"


        elif 'q' == n:
            break

        if selection < 0:
            selection = len(menu) - 1
        if selection >= len(menu):
            selection = 0
wrapper(main)
