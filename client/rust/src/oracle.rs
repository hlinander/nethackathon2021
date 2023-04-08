use std::{
    ffi::{CStr, CString},
    io::{stdin, stdout, Read, Write},
    os::unix::prelude::{AsFd, AsRawFd},
    time::Duration,
};

use crossterm::{cursor::*, terminal::Clear, *};
use libc::abort;
use nethack_rs::g;
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

static mut TOKIO_RUNTIME: Option<tokio::runtime::Runtime> = None;

enum MapObjectID {
    Item,
    Monster,
    Tile,
}

struct MapObject {
    id: MapObjectID,
    name: String,
    symbol: String,
    color: String,
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
    let ip = "192.168.1.148";
    let client = Client::builder().build().unwrap();
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
    execute!(stdout(), MoveTo(0, 25), EnableBlinking).unwrap();
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
                MoveTo(0, 25)
            )
            .unwrap();
            print!("{}", line);
            stdout().flush().unwrap();
            execute!(stdout(), MoveTo(line.len() as u16, 25), EnableBlinking).unwrap();
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
    printed_status_line: String,
    cursor_pos: (u16, u16),
}

static mut UI_STATE: Option<UiState> = None;

fn default_cursor_pos() -> (u16, u16) {
    (0, 27)
}

unsafe fn get_status_line() -> String {
    match &UI_STATE.as_ref().unwrap().request_status {
        RequestStatus::Active => "...".to_string(),
        RequestStatus::Done => "The oracle has spoken.".to_string(),
        RequestStatus::Error(err) => format!("server unhappy: {}", err),
        RequestStatus::None => format!(""),
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
        execute!(stdout(), RestorePosition).unwrap();
        ui_state.printed_status_line = text;
    }
}

pub unsafe fn update_oracle_ui() {
    if UI_STATE.is_none() {
        UI_STATE = Some(UiState {
            cursor_pos: default_cursor_pos(),
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
            ui_state.request_status = RequestStatus::Active;
        }
    }
    let mut needs_update = ui_state.received_text != ui_state.printed_text || clear;
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
        match req.data_receive.try_recv() {
            Ok(ReceiveMsg::MoreData(data)) => {
                ui_state.received_text += &data;
            }
            Ok(ReceiveMsg::Error(error_msg)) => {
                ui_state.request_status = RequestStatus::Error(error_msg);
                abort_active_request();
            }
            Ok(ReceiveMsg::End) | Err(TryRecvError::Disconnected) => {
                ui_state.request_status = RequestStatus::Done;
                abort_active_request();
            }
            Err(TryRecvError::Empty) => {}
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
