use std::{
    default,
    ffi::{CStr, CString},
    io::{stdin, stdout, Read, Write},
    os::unix::prelude::{AsFd, AsRawFd},
    ptr::{null, null_mut},
    time::{Duration, Instant},
};

use crossterm::{cursor::*, terminal::Clear, *};
use libc::abort;
use nethack_rs::{g, u};
use reqwest::Client;
use serde::Serialize;
use termios::{tcgetattr, tcsetattr, Termios, ICANON};
use tokio::{
    runtime::Runtime,
    sync::mpsc::{
        error::TryRecvError, unbounded_channel, UnboundedReceiver as Receiver,
        UnboundedSender as Sender,
    },
    task::JoinHandle,
};

use crate::nh_api::obj_to_obj_data;

static mut TOKIO_RUNTIME: Option<tokio::runtime::Runtime> = None;

#[derive(PartialEq)]
enum MapObjectID {
    Item,
    Monster,
    Tile,
}

struct MapObject {
    id: MapObjectID,
    name: String,
    symbol: char,
    color: u8,
    distance: f32,
}

enum ReceiveMsg {
    MoreData(String),
    End,
    Error(String),
}

struct ActiveRequest {
    id: u32,
    prompt: String,
    response_buf: String,
    join_handle: JoinHandle<()>,
    data_receive: Receiver<ReceiveMsg>,
}

static mut ACTIVE_REQUEST: Option<ActiveRequest> = None;
static mut REQUEST_ID: u32 = 0;

pub unsafe fn init() {
    assert!(TOKIO_RUNTIME.is_none());
    TOKIO_RUNTIME = Some(Runtime::new().unwrap());
    let stdin_fd = std::io::stdin().as_raw_fd();

    // get the current terminal attributes
    let mut termios = Termios::from_fd(stdin_fd).unwrap();

    // disable input buffering
    termios.c_lflag &= !(libc::ECHO | libc::ICANON);
    termios.c_cc[termios::VMIN] = 1;
    termios.c_cc[termios::VTIME] = 0;

    // set the new terminal attributes
    tcsetattr(stdin_fd, libc::TCSANOW, &termios).unwrap();
    tcsetattr(stdin_fd, libc::TCSAFLUSH, &termios).unwrap();
}

#[derive(Serialize)]
struct PromptRequest {
    prompt: String,
}

async fn new_prompt_request(prompt: String, tx: Sender<ReceiveMsg>) {
    let ip = "192.168.1.148"; // hampoos
    let ip = "172.26.2.104"; // jannix
    let client = Client::builder()
        .connect_timeout(Duration::from_millis(2000))
        .http2_keep_alive_timeout(Duration::from_millis(2000))
        .build()
        .unwrap();
    let req = client
        .get(format!("http://{ip}:8383/"))
        .body(serde_json::to_string_pretty(&PromptRequest { prompt }).unwrap())
        .send();

    match req.await {
        Ok(mut r) => loop {
            match r.chunk().await {
                Ok(Some(chunk)) => {
                    let _ = tx.send(ReceiveMsg::MoreData(
                        std::str::from_utf8(&chunk).unwrap().to_string(),
                    ));
                }
                Ok(None) => {
                    let _ = tx.send(ReceiveMsg::End);
                    break;
                }
                Err(e) => {
                    let _ = tx.send(ReceiveMsg::Error(format!("{:?}", e)));
                    break;
                }
            }
        },
        Err(err) => {
            let _ = tx.send(ReceiveMsg::Error(format!("{:?}", err)));
        }
    }
}

unsafe fn abort_active_request() {
    if let Some(req) = ACTIVE_REQUEST.as_mut() {
        req.join_handle.abort();
    }
    ACTIVE_REQUEST = None;
}

unsafe fn new_request(prompt: String) {
    abort_active_request();
    if let Some(ui_state) = UI_STATE.as_mut() {
        ui_state.last_request_state_update = Some(Instant::now());
        ui_state.request_status = RequestStatus::Active;
    }
    let runtime = TOKIO_RUNTIME.as_ref().unwrap();
    let (tx, rx) = unbounded_channel();

    let join_handle = runtime.spawn(new_prompt_request(prompt.clone(), tx));
    REQUEST_ID += 1;
    ACTIVE_REQUEST = Some(ActiveRequest {
        id: REQUEST_ID,
        prompt,
        response_buf: String::new(),
        join_handle,
        data_receive: rx,
    })
}

#[no_mangle]
pub unsafe extern "C" fn oracle_prompt() -> i32 {
    let mut line = String::new();
    execute!(stdout(), MoveTo(0, default_prompt_pos().1), EnableBlinking).unwrap();
    loop {
        let c = nethackathon_getch();
        if c == 8 || c == 127 {
            // backspace
            if !line.is_empty() {
                line.remove(line.len() - 1);
            }
            execute!(
                stdout(),
                Clear(terminal::ClearType::CurrentLine),
                MoveTo(0, default_prompt_pos().1)
            )
            .unwrap();
            print!("{}", line);
            stdout().flush().unwrap();
            execute!(
                stdout(),
                MoveTo(line.len() as u16, default_prompt_pos().1),
                EnableBlinking
            )
            .unwrap();
            continue;
        }
        if let Some(c) = char::from_u32(c as u32) {
            if c == '\n' {
                execute!(stdout(), Clear(terminal::ClearType::CurrentLine)).unwrap();
                new_request(line);
                break;
            }
            line += &c.to_string();
            print!("{}", c);
            stdout().flush().unwrap();
        }
    }
    0
}

#[derive(Default, PartialEq)]
enum RequestStatus {
    #[default]
    None,
    Active,
    Done,
    Error(String),
}

#[derive(Default)]
struct UiState {
    last_request_id: u32,
    printed_text: String,
    received_text: String,
    request_status: RequestStatus,
    last_request_state_update: Option<Instant>,
    printed_status_line: String,
    cursor_pos: (u16, u16),

    described_objects: Vec<MapObject>,
}

static mut UI_STATE: Option<UiState> = None;

fn default_prompt_pos() -> (u16, u16) {
    (0, 25)
}

fn default_cursor_pos() -> (u16, u16) {
    (0, 27)
}

unsafe fn get_status_line() -> String {
    match &UI_STATE.as_ref().unwrap().request_status {
        RequestStatus::Active => "...".to_string(),
        RequestStatus::Done => "The oracle has spoken.".to_string(),
        RequestStatus::Error(err) => format!("server unhappy: {}", err),
        RequestStatus::None => format!("___"),
    }
}
unsafe fn update_status_line() {
    let ui_state = UI_STATE.as_mut().unwrap();
    let text = get_status_line();
    if ui_state.printed_status_line != text {
        execute!(
            stdout(),
            SavePosition,
            MoveTo(default_cursor_pos().0, default_cursor_pos().1 - 1),
            Clear(terminal::ClearType::CurrentLine),
            MoveTo(default_cursor_pos().0, default_cursor_pos().1 - 1),
        )
        .unwrap();
        print!("{}", text);
        stdout().flush().unwrap();
        execute!(stdout(), RestorePosition).unwrap();
        ui_state.printed_status_line = text;
    }
}

const NUMMONS: u32 = nethack_rs::monnums_NUMMONS;
const GLYPH_MON_OFF: u32 = 0;
const GLYPH_PET_OFF: u32 = NUMMONS + GLYPH_MON_OFF;
const GLYPH_INVIS_OFF: u32 = NUMMONS + GLYPH_PET_OFF;
const GLYPH_DETECT_OFF: u32 = 1 + GLYPH_INVIS_OFF;
const GLYPH_BODY_OFF: u32 = NUMMONS + GLYPH_DETECT_OFF;
const GLYPH_RIDDEN_OFF: u32 = NUMMONS + GLYPH_BODY_OFF;
const GLYPH_OBJ_OFF: u32 = NUMMONS + GLYPH_RIDDEN_OFF;
const GLYPH_CMAP_OFF: u32 = nethack_rs::NUM_OBJECTS + GLYPH_OBJ_OFF;
const GLYPH_EXPLODE_OFF: u32 =
    (nethack_rs::screen_symbols_MAXPCHARS - nethack_rs::MAXEXPCHARS) + GLYPH_CMAP_OFF;
const GLYPH_ZAP_OFF: u32 =
    (nethack_rs::MAXEXPCHARS * nethack_rs::explosion_types_EXPL_MAX) + GLYPH_EXPLODE_OFF;
const GLYPH_SWALLOW_OFF: u32 = (nethack_rs::NUM_ZAP << 2) + GLYPH_ZAP_OFF;
const GLYPH_WARNING_OFF: u32 = (NUMMONS << 3) + GLYPH_SWALLOW_OFF;
const GLYPH_STATUE_OFF: u32 = nethack_rs::WARNCOUNT + GLYPH_WARNING_OFF;
const GLYPH_UNEXPLORED_OFF: u32 = NUMMONS + GLYPH_STATUE_OFF;
const GLYPH_NOTHING_OFF: u32 = GLYPH_UNEXPLORED_OFF + 1;
const MAX_GLYPH: u32 = GLYPH_NOTHING_OFF + 1;

unsafe fn get_map_item_list() -> Vec<MapObject> {
    let mut o_iter = g.level.objlist;
    let player_pos = (u.ux as f32, u.uy as f32);
    let mut list = Vec::new();
    while !o_iter.is_null() {
        let obj = &*o_iter;
        let vis_state = nethack_rs::g
            .viz_array
            .add(obj.oy as usize)
            .read()
            .add(obj.ox as usize)
            .read();
        if vis_state & nethack_rs::COULD_SEE as i8 != 0 {
            let glyph = if obj.otyp == nethack_rs::STATUE as i16 {
                obj.corpsenm + GLYPH_STATUE_OFF as i32
            } else if obj.otyp == nethack_rs::CORPSE as i16 {
                obj.corpsenm + GLYPH_BODY_OFF as i32
            } else {
                obj.otyp as i32 + GLYPH_OBJ_OFF as i32
            };
            let o = nethack_rs::objects.as_ptr().add(obj.otyp as usize).read();
            let oc_name = nethack_rs::obj_descr
                .as_ptr()
                .add(o.oc_name_idx as usize)
                .read()
                .oc_name;
            let mut gi: nethack_rs::glyph_info = core::mem::zeroed();
            nethack_rs::map_glyphinfo(0, 0, glyph, 0, &mut gi);
            if !oc_name.is_null() {
                let item_pos = (obj.ox as f32, obj.oy as f32);
                let dx = player_pos.0 - item_pos.0;
                let dy = player_pos.1 - item_pos.1;
                let distance = (dx * dx + dy * dy).sqrt();
                let name = CStr::from_ptr(oc_name);
                list.push(MapObject {
                    id: MapObjectID::Item,
                    name: name.to_string_lossy().into(),
                    symbol: char::from_u32(gi.ttychar as u32).unwrap_or('?'),
                    color: 0,
                    distance,
                });
            }
        }
        o_iter = (&*o_iter).nobj;
    }
    list
}

unsafe fn get_monster_list() -> Vec<MapObject> {
    let mut m_iter = g.level.monlist;
    let player_pos = (u.ux as f32, u.uy as f32);
    let mut list = Vec::new();
    while !m_iter.is_null() {
        if nethack_rs::howmonseen(m_iter) & nethack_rs::MONSEEN_NORMAL != 0 {
            let name_buf =
                nethack_rs::x_monnam(m_iter, nethack_rs::ARTICLE_NONE as i32, null(), !0, 0);
            let name = CStr::from_ptr(name_buf);
            let tame = (&*m_iter).mtame;
            let m_data = (&*m_iter).data;
            let mon_index = nethack_rs::monsndx(m_data);
            let glyph = if tame != 0 {
                mon_index + nethack_rs::monnums_NUMMONS as i32
            } else {
                mon_index + nethack_rs::GLYPH_MON_OFF as i32
            };
            let mut gi: nethack_rs::glyph_info = core::mem::zeroed();
            nethack_rs::map_glyphinfo(0, 0, glyph, 0, &mut gi);
            let mon_pos = ((&*m_iter).mx as f32, (&*m_iter).my as f32);
            let dx = player_pos.0 - mon_pos.0;
            let dy = player_pos.1 - mon_pos.1;
            let distance = (dx * dx + dy * dy).sqrt();
            assert!(
                mon_index >= 0 && mon_index < nethack_rs::monnums_NUMMONS as i32,
                "{}",
                mon_index
            );
            list.push(MapObject {
                id: MapObjectID::Monster,
                name: name.to_string_lossy().into_owned(),
                symbol: char::from_u32(gi.ttychar as u32).unwrap_or('?'),
                color: nethack_rs::mons
                    .as_ptr()
                    .add(mon_index as usize)
                    .read()
                    .mcolor,
                distance,
            });
        }
        m_iter = (&*m_iter).nmon;
    }
    list
}

fn generate_object_prompt(obj: &MapObject) -> String {
    format!(
        "When encountering a {} ({}), a common strategy is to",
        obj.name, obj.symbol
    )
}

fn pick_object_to_describe(
    ui_state: &mut UiState,
    mut objects: Vec<MapObject>,
) -> Option<MapObject> {
    objects.retain(|obj| {
        !ui_state
            .described_objects
            .iter()
            .any(|a| a.id == obj.id && a.name == obj.name)
    });
    if objects.is_empty() {
        return None;
    }
    objects.sort_by(|a, b| a.distance.total_cmp(&b.distance));
    Some(objects.remove(0))
}

pub unsafe fn update_oracle_ui() {
    if TOKIO_RUNTIME.is_none() {
        return;
    }
    if UI_STATE.is_none() {
        UI_STATE = Some(UiState {
            cursor_pos: default_cursor_pos(),
            last_request_state_update: Some(Instant::now()),
            ..Default::default()
        });
    }
    let ui_state = UI_STATE.as_mut().unwrap();
    let request_id = update_request_state(ui_state);
    let mut clear = false;
    if let Some(current_id) = request_id {
        if ui_state.last_request_id != current_id {
            clear = true;
            ui_state.last_request_id = current_id;
        }
    } else {
        let mut map_things: Vec<MapObject> = Vec::new();
        map_things.extend(get_monster_list());
        map_things.extend(get_map_item_list());
        let time_since_desc = ui_state
            .last_request_state_update
            .map(|t| Instant::now().duration_since(t))
            .unwrap_or(Duration::from_secs(100000000));
        let time_to_do_new_description = time_since_desc > Duration::from_secs(20);
        if time_to_do_new_description {
            if let Some(to_describe) = pick_object_to_describe(ui_state, map_things) {
                let prompt = generate_object_prompt(&to_describe);
                new_request(prompt);
                ui_state.described_objects.push(to_describe);
            }
        }
    }
    let needs_update = ui_state.received_text != ui_state.printed_text || clear;
    update_status_line();
    if needs_update {
        if clear {
            execute!(
                stdout(),
                SavePosition,
                MoveTo(default_cursor_pos().0, default_cursor_pos().1),
                Clear(terminal::ClearType::FromCursorDown),
                RestorePosition
            )
            .unwrap();
            ui_state.cursor_pos = default_cursor_pos();
        }
        let (x, y) = ui_state.cursor_pos;
        execute!(stdout(), SavePosition, MoveTo(x, y)).unwrap();
        if ui_state.printed_text.len() < ui_state.received_text.len() {
            let diff = &ui_state.received_text[ui_state.printed_text.len()..];
            ui_state.printed_text += diff;
            print!("{}", diff);
            stdout().flush().unwrap();
        }
        ui_state.cursor_pos = crossterm::cursor::position().unwrap();
        execute!(stdout(), RestorePosition).unwrap();
        stdout().flush().unwrap();
    }
}

unsafe fn update_request_state(ui_state: &mut UiState) -> Option<u32> {
    let mut request_id = None;
    if let Some(req) = ACTIVE_REQUEST.as_mut() {
        request_id = Some(req.id);
        loop {
            match req.data_receive.try_recv() {
                Ok(ReceiveMsg::MoreData(data)) => {
                    ui_state.received_text += &data;
                    ui_state.last_request_state_update = Some(Instant::now());
                }
                Ok(ReceiveMsg::Error(error_msg)) => {
                    ui_state.request_status = RequestStatus::Error(error_msg);
                    ui_state.last_request_state_update = Some(Instant::now());
                    abort_active_request();
                    break;
                }
                Err(TryRecvError::Disconnected) => {
                    ui_state.request_status = RequestStatus::Done;
                    ui_state.last_request_state_update = Some(Instant::now());
                    abort_active_request();
                    break;
                }
                Ok(ReceiveMsg::End) => {
                    ui_state.request_status = RequestStatus::Done;
                    ui_state.last_request_state_update = Some(Instant::now());
                    abort_active_request();
                    break;
                }
                Err(TryRecvError::Empty) => {
                    break;
                }
            }
        }
    }
    request_id
}

#[no_mangle]
pub unsafe extern "C" fn nethackathon_getch() -> i32 {
    let mut selector = selecting::Selector::new();
    selector.add_read(&0);
    update_oracle_ui();
    loop {
        let mut rfds: libc::fd_set = std::mem::zeroed();
        libc::FD_SET(0, &mut rfds);

        let mut tv = libc::timeval {
            tv_sec: 0,
            tv_usec: 200 * 1000,
        };

        let retval = libc::select(
            1,
            &mut rfds as _,
            std::ptr::null_mut(),
            std::ptr::null_mut(),
            &mut tv as _,
        );
        if retval == -1 {
            eprintln!("select() failed: {}", std::io::Error::last_os_error());
        } else if retval > 0 {
            let c = libc::getchar();
            return c;
        } else {
            update_oracle_ui();
        }
    }
}
