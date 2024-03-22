use lazy_static::*;
use regex::Regex;
use std::{
    cmp::Ordering,
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

use crate::{nh_api::obj_to_obj_data, oracle};

static mut TOKIO_RUNTIME: Option<tokio::runtime::Runtime> = None;

#[derive(Debug, Default, PartialEq, Copy, Clone)]
enum MapObjectID {
    #[default]
    None,
    Item,
    Monster,
    Tile,
}

impl MapObjectID {
    fn sort_key(&self) -> i32 {
        match self {
            MapObjectID::None => 0,
            MapObjectID::Monster => 1,
            MapObjectID::Item => 2,
            MapObjectID::Tile => 3,
        }
    }
}

#[derive(Clone, Default)]
struct MapObject {
    id: MapObjectID,
    name: String,
    symbol: char,
    color: u8,
    distance: f32,
}

impl MapObject {
    pub fn new_monster(name: impl Into<String>) -> Self {
        Self {
            id: MapObjectID::Monster,
            name: name.into(),
            ..Default::default()
        }
    }
    pub fn new_item(name: impl Into<String>) -> Self {
        Self {
            id: MapObjectID::Item,
            name: name.into(),
            ..Default::default()
        }
    }
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
    if TOKIO_RUNTIME.is_some() {
        return;
    }
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
    r#type: String,
    message: String,
}

async fn new_prompt_request(prompt: String, tx: Sender<ReceiveMsg>) {
    let ip = "192.168.1.11"; // hampoos
                              // let ip = "172.26.2.104"; // jannix
    let client = Client::builder()
        .connect_timeout(Duration::from_millis(2000))
        .http2_keep_alive_timeout(Duration::from_millis(2000))
        .build()
        .unwrap();
    let req = client
        .get(format!("http://{ip}:8383/"))
        .body(
            serde_json::to_string_pretty(&PromptRequest {
                message: prompt,
                r#type: "chat".to_string(),
            })
            .unwrap(),
        )
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

fn log(s: &str) {
    let mut log = std::fs::File::options()
        .create(true)
        .append(true)
        .open("/home/herden/projects/nethackathon2024/nethacklog")
        .unwrap();
    writeln!(log, "{}", s);
}

unsafe fn abort_active_request() {
    if let Some(req) = ACTIVE_REQUEST.as_mut() {
        req.join_handle.abort();
    }
    ACTIVE_REQUEST = None;
}

unsafe fn new_request(user_visible_prompt: String, prompt: String) {
    abort_active_request();
    if let Some(ui_state) = UI_STATE.as_mut() {
        ui_state.last_request_state_update = Some(Instant::now());
        ui_state.request_status = RequestStatus::Active(user_visible_prompt);
        ui_state.received_text = "".to_string();
        ui_state.processed_text = Vec::new();
        ui_state.printed_text = Vec::new();
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
    execute!(stdout(), MoveTo(0, default_prompt_pos().1), EnableBlinking);
    const ORACLE_PROMPT: &str = "Ask the oracle: ";
    print!("{}", ORACLE_PROMPT);
    stdout().flush();
    loop {
        let c = nethackathon_getch();
        if c == 8 || c == 127 {
            // backspace
            if !line.is_empty() {
                line.remove(line.len() - 1);
                execute!(
                    stdout(),
                    Clear(terminal::ClearType::CurrentLine),
                    MoveTo(0, default_prompt_pos().1),
                    EnableBlinking
                );
                print!("{}{}", ORACLE_PROMPT, line);
                stdout().flush();
            }
            continue;
        }
        if let Some(c) = char::from_u32(c as u32) {
            if c == '\n' {
                execute!(stdout(), Clear(terminal::ClearType::CurrentLine));
                if line.trim() != "" {
                    if line == "tax me" {
                        crate::nh_api::rust_clear_gems();
                    } else {
                        new_request(format!("$ {}", line.clone()), line);
                    }
                }

                break;
            }
            line += &c.to_string();
            print!("{}", c);
            stdout().flush();
        }
    }
    0
}

#[derive(Default, PartialEq)]
enum RequestStatus {
    #[default]
    None,
    Active(String),
    Done,
    Error(String, String),
}

#[derive(Default)]
struct UiState {
    last_request_id: u32,
    printed_text: Vec<(TextStyle, String)>,
    received_text: String,
    processed_text: Vec<(TextStyle, String)>,
    request_status: RequestStatus,
    last_request_state_update: Option<Instant>,
    printed_status_line: String,
    cursor_pos: (u16, u16),

    described_objects: Vec<MapObject>,
    queued_descriptions: Vec<MapObject>,
}

static mut UI_STATE: Option<UiState> = None;

fn default_prompt_pos() -> (u16, u16) {
    (0, 24)
}

fn default_cursor_pos() -> (u16, u16) {
    (0, 26)
}

unsafe fn get_status_line() -> String {
    match &UI_STATE.as_ref().unwrap().request_status {
        RequestStatus::Active(prompt_text) => format!("{} ...", prompt_text),
        RequestStatus::Done => "The oracle has spoken.".to_string(),
        RequestStatus::Error(prompt, err) => format!("server unhappy when {}: {}", prompt, err),
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
        );
        let wrapped_text = textwrap::wrap(&text, 80);
        for line in wrapped_text {
            println!("{}", line);
        }
        stdout().flush();
        execute!(stdout(), RestorePosition);
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
        if obj.where_ == nethack_rs::OBJ_FLOOR as i8 {
            let viz_array_addr = nethack_rs::g_viz_array();
            let column_addr = viz_array_addr.add(obj.oy as usize).read();
            let vis_state = column_addr.add(obj.ox as usize).read();
            if vis_state & nethack_rs::COULD_SEE as i8 != 0 {
                let o = nethack_rs::objects.as_ptr().add(obj.otyp as usize).read();
                let oc_name = nethack_rs::obj_descr
                    .as_ptr()
                    .add(o.oc_name_idx as usize)
                    .read()
                    .oc_name;
                let mut gi: nethack_rs::glyph_info = core::mem::zeroed();
                let glyph = if obj.otyp == nethack_rs::STATUE as i16 {
                    obj.corpsenm + GLYPH_STATUE_OFF as i32
                } else if obj.otyp == nethack_rs::CORPSE as i16 {
                    obj.corpsenm + GLYPH_BODY_OFF as i32
                } else {
                    obj.otyp as i32 + GLYPH_OBJ_OFF as i32
                };
                nethack_rs::map_glyphinfo(0, 0, glyph, 0, &mut gi);
                let (sym_char, name) = if obj.known() == 0 {
                    let oclass_id = nethack_rs::def_char_to_objclass(gi.ttychar as i8);
                    let oc_info = nethack_rs::def_oc_syms
                        .as_ptr()
                        .add(oclass_id as usize)
                        .read();
                    (oc_info.sym as i32, oc_info.name)
                } else {
                    (gi.ttychar, oc_name)
                };
                if !name.is_null() {
                    let item_pos = (obj.ox as f32, obj.oy as f32);
                    let dx = player_pos.0 - item_pos.0;
                    let dy = player_pos.1 - item_pos.1;
                    let distance = (dx * dx + dy * dy).sqrt();
                    let name = CStr::from_ptr(name);
                    list.push(MapObject {
                        id: MapObjectID::Item,
                        name: name.to_string_lossy().into(),
                        symbol: char::from_u32(sym_char as u32).unwrap_or('?'),
                        color: gi.color as u8,
                        distance,
                    });
                }
            }
        }
        o_iter = (&*o_iter).nobj;
    }
    list
}

unsafe fn get_tile_list() -> Vec<MapObject> {
    let player_pos = (u.ux as f32, u.uy as f32);
    let mut tiles = Vec::new();
    let viz_array_addr = nethack_rs::g_viz_array();
    for y in 0..21 {
        let column_addr = viz_array_addr.add(y as usize).read();
        for x in 0..80 {
            let vis_state = column_addr.add(x as usize).read();
            if vis_state & nethack_rs::COULD_SEE as i8 != 0 {
                let r = nethack_rs::get_location_rm(x, y);
                match r.typ as u32 {
                    nethack_rs::levl_typ_types_STONE
                    | nethack_rs::levl_typ_types_VWALL
                    | nethack_rs::levl_typ_types_HWALL
                    | nethack_rs::levl_typ_types_TLCORNER
                    | nethack_rs::levl_typ_types_TRCORNER
                    | nethack_rs::levl_typ_types_BLCORNER
                    | nethack_rs::levl_typ_types_BRCORNER
                    | nethack_rs::levl_typ_types_CROSSWALL
                    | nethack_rs::levl_typ_types_TUWALL
                    | nethack_rs::levl_typ_types_TDWALL
                    | nethack_rs::levl_typ_types_TLWALL
                    | nethack_rs::levl_typ_types_TRWALL
                    | nethack_rs::levl_typ_types_DBWALL
                    | nethack_rs::levl_typ_types_SDOOR
                    | nethack_rs::levl_typ_types_SCORR
                    | nethack_rs::levl_typ_types_DOOR
                    | nethack_rs::levl_typ_types_CORR
                    | nethack_rs::levl_typ_types_ROOM
                    | nethack_rs::levl_typ_types_STAIRS
                    | nethack_rs::levl_typ_types_LADDER
                    | nethack_rs::levl_typ_types_AIR => continue,
                    typ => {
                        let name_buf = nethack_rs::levltyp_to_name(typ as i32);
                        let name = CStr::from_ptr(name_buf);
                        let mut gi: nethack_rs::glyph_info = core::mem::zeroed();
                        nethack_rs::map_glyphinfo(0, 0, r.glyph, 0, &mut gi);
                        let dx = player_pos.0 - x as f32;
                        let dy = player_pos.1 - y as f32;
                        let distance = (dx * dx + dy * dy).sqrt();
                        tiles.push(MapObject {
                            id: MapObjectID::Tile,
                            name: name.to_string_lossy().into_owned(),
                            symbol: char::from_u32(gi.ttychar as u32).unwrap_or('?'),
                            color: gi.color as u8,
                            distance,
                        });
                    }
                }
            }
        }
    }
    tiles
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
                color: gi.color as u8,
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
        obj.name, obj.symbol,
    )
}

fn pick_object_to_describe(objects: &mut Vec<MapObject>) -> Option<MapObject> {
    if objects.is_empty() {
        return None;
    }
    // sort by type of object, then distance, to prioritize in order: monster -> item -> tile
    objects.sort_by(|a, b| match a.id.sort_key().cmp(&b.id.sort_key()) {
        Ordering::Equal => a.distance.total_cmp(&b.distance),
        ord => ord,
    });
    Some(objects.remove(0))
}

pub unsafe fn update_oracle_ui() {
    if TOKIO_RUNTIME.is_none() {
        return;
    }
    if g.program_state.something_worth_saving <= 0 {
        return;
    }
    if UI_STATE.is_none() {
        UI_STATE = Some(UiState {
            cursor_pos: default_cursor_pos(),
            last_request_state_update: Some(Instant::now()),
            described_objects: vec![
                MapObject::new_monster("little dog"),
                MapObject::new_monster("kitten"),
                MapObject::new_monster("kitten"),
                MapObject::new_item("gold piece"),
                MapObject::new_item("boulder"),
            ],
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
        map_things.extend(get_tile_list());
        map_things.retain(|obj| {
            !ui_state
                .described_objects
                .iter()
                .any(|a| a.id == obj.id && a.name == obj.name)
        });
        for thing in map_things {
            ui_state.described_objects.push(thing.clone());
            ui_state.queued_descriptions.push(thing);
        }
        let time_since_desc = ui_state
            .last_request_state_update
            .map(|t| Instant::now().duration_since(t))
            .unwrap_or(Duration::from_secs(100000000));
        let time_to_do_new_description = time_since_desc > Duration::from_secs(5);
        if time_to_do_new_description {
            if let Some(to_describe) = pick_object_to_describe(&mut ui_state.queued_descriptions) {
                let prompt = generate_object_prompt(&to_describe);
                new_request(
                    format!(
                        "Advising on {} (\x1b[;{}m{}\x1b[;39m)...",
                        to_describe.name,
                        30 + to_describe.color,
                        to_describe.symbol,
                    ),
                    prompt,
                );
                ui_state.described_objects.push(to_describe);
            }
        }
    }
    let needs_update = ui_state.processed_text != ui_state.printed_text || clear;
    if needs_update {
        let refresh_text = ui_state
            .printed_text
            .iter()
            .enumerate()
            .any(|(idx, (_, text))| {
                !ui_state
                    .processed_text
                    .get(idx)
                    .map(|s| s.1.starts_with(text))
                    .unwrap_or(false)
            });
        if clear || refresh_text {
            execute!(
                stdout(),
                SavePosition,
                MoveTo(default_cursor_pos().0, default_cursor_pos().1),
                Clear(terminal::ClearType::FromCursorDown),
                RestorePosition
            );
            ui_state.cursor_pos = default_cursor_pos();
        }
        if refresh_text {
            ui_state.printed_text = Vec::new();
        }
        let (mut x, mut y) = ui_state.cursor_pos;
        execute!(stdout(), SavePosition, MoveTo(x, y));
        let max_line = 33;
        'outer: for (idx, (text_style, text)) in ui_state.processed_text.iter().enumerate() {
            if ui_state.cursor_pos.1 >= max_line {
                // max terminal size supported
                break;
            }
            if ui_state.printed_text.len() <= idx {
                ui_state
                    .printed_text
                    .push((text_style.clone(), "".to_string()));
            }
            let printed_text = &mut ui_state.printed_text[idx].1;
            while printed_text.len() < text.len() {
                (x, y) = ui_state.cursor_pos;
                if y >= max_line {
                    // max terminal size supported
                    break;
                }
                execute!(stdout(), MoveTo(x, y));
                let chars_to_next_line = 79 - x;
                if chars_to_next_line <= 0 {
                    ui_state.cursor_pos.1 += 1;
                    ui_state.cursor_pos.0 = 0;
                    continue;
                }
                let line_end_for_received = printed_text.len()
                    + (text.len() - printed_text.len()).min(chars_to_next_line as usize);
                let diff = &text[printed_text.len()..line_end_for_received];
                printed_text.push_str(diff);
                let mut stdout = stdout();
                let mut content = crossterm::style::style(diff);
                use crossterm::style::*;
                if text_style.bold {
                    content = content.bold();
                }

                if let Some(link) = &text_style.link {
                    let link_prefix =
                        format!("\x1b]8;;https://nethackwiki.com/wiki/{}\x1b\\", link);
                    stdout.write(link_prefix.as_bytes());
                    content = content.blue().underlined();
                }
                stdout.execute(crossterm::style::PrintStyledContent(content));
                if text_style.link.is_some() {
                    let link_postfix = "\x1b]8;;\x1b\\";
                    stdout.write(link_postfix.as_bytes());
                }

                stdout.flush();
                if let Ok(pos) = crossterm::cursor::position() {
                    ui_state.cursor_pos = pos;
                } else {
                    break 'outer;
                }
            }
        }
        execute!(stdout(), RestorePosition);
        stdout().flush();
    }
    update_status_line();
}

lazy_static! {
    static ref LINK_REGEX: Regex = Regex::new(r#"(?:\[\[|\{\{)(?:((?:\w|\d|\s|\:|\'|\.|\,|\-|\#)+)(?:\||\:))?((?:\w|\d|\s|\:|\'|\.|\,|\-|\#)+)(?:\]\]|\}\})"#).unwrap();
}

#[derive(Debug, Default, Clone, PartialEq)]
struct TextStyle {
    bold: bool,
    link: Option<String>,
    source_char: char,
}

impl TextStyle {
    fn view_of_stack(stack: &[TextStyle]) -> TextStyle {
        let mut bold = None;
        let mut link = None;
        for s in stack.iter().rev() {
            if bold.is_none() && s.bold {
                bold = Some(s.bold);
            }
            if link.is_none() && s.link.is_some() {
                link = Some(s.link.clone());
            }
        }
        Self {
            bold: bold.unwrap_or(false),
            link: link.unwrap_or(None),
            source_char: '\x00',
        }
    }
}

fn process_received_text(ui_state: &mut UiState) {
    let received_text = &ui_state.received_text;
    let mut processed = String::new();
    let mut last_index = 0;
    let mut replacements = Vec::new();
    for capture in LINK_REGEX.captures_iter(received_text) {
        let start = capture.get(0).unwrap().start();
        let end = capture.get(0).unwrap().end();
        let capture_content = capture.get(2).unwrap().as_str();

        let processed_start = start - last_index + processed.len() + 1;
        let processed_end = start + capture_content.len() - last_index + processed.len() + 1;

        processed.push_str(&received_text[last_index..start]);
        processed.push_str(capture_content);

        let link = capture
            .get(1)
            .map(|s| s.as_str())
            .unwrap_or(capture_content)
            .replace(" ", "_");
        replacements.push(((processed_start..processed_end), link.to_string()));

        last_index = end;
    }
    if last_index < received_text.len() {
        processed.push_str(&received_text[last_index..received_text.len()]);
    }
    ui_state.processed_text = Vec::new();
    //log(received_text);
    //log(&format!("{:?}", replacements));
    //ui_state.received_text = processed.to_string();

    let mut segments = Vec::new();
    let mut style_stack = vec![TextStyle::default()];
    let mut current_segment = String::new();
    let mut prev_char = None;
    let mut char_iter_bytes = processed.chars();
    let mut char_iter = processed.chars().peekable();
    while let Some(c) = char_iter.next() {
        char_iter_bytes.next();
        let byte_idx = processed.len() - char_iter_bytes.as_str().len();
        if let Some((_, link)) = replacements.iter().find(|r| r.0.start == byte_idx) {
            let new_style = TextStyle {
                source_char: '[',
                link: Some(link.clone()),
                ..Default::default()
            };
            segments.push((
                TextStyle::view_of_stack(&style_stack),
                core::mem::take(&mut current_segment),
            ));
            style_stack.push(new_style);
        }
        if let Some(_) = replacements.iter().find(|r| r.0.end == byte_idx) {
            let pos = style_stack
                .iter()
                .position(|s: &TextStyle| s.source_char == '[')
                .unwrap();

            segments.push((
                TextStyle::view_of_stack(&style_stack),
                core::mem::take(&mut current_segment),
            ));
            style_stack.remove(pos);
        }
        match c {
            '\'' => {
                if prev_char == Some('\'') {
                    current_segment.pop();
                    while let Some('\'') = char_iter.peek() {
                        char_iter.next();
                        char_iter_bytes.next();
                    }
                    segments.push((
                        TextStyle::view_of_stack(&style_stack),
                        core::mem::take(&mut current_segment),
                    ));
                    if let Some(pos) = style_stack
                        .iter()
                        .position(|s: &TextStyle| s.source_char == c)
                    {
                        style_stack.remove(pos);
                    } else {
                        let new_style = TextStyle {
                            source_char: '\'',
                            bold: true,
                            ..Default::default()
                        };
                        style_stack.push(new_style);
                    }
                } else {
                    current_segment.push(c);
                }
            }
            c => current_segment.push(c),
        }
        prev_char = Some(c);
    }
    if !current_segment.is_empty() {
        segments.push((TextStyle::view_of_stack(&style_stack), current_segment));
    }
    //log(&format!("{:?}", segments));
    ui_state.processed_text = segments;
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
                    process_received_text(ui_state);
                }
                Ok(ReceiveMsg::Error(error_msg)) => {
                    let visible_prompt = match &ui_state.request_status {
                        RequestStatus::Active(prompt) => prompt.clone(),
                        _ => req.prompt.clone(),
                    };
                    ui_state.request_status = RequestStatus::Error(visible_prompt, error_msg);
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
