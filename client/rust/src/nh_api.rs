use crate::ipc::{Error, Ipc, Result};
use crate::nh_proto::{CoconutSong, ObjData, SessionEvent};
use crate::oracle;
use core::ptr::null_mut;
use nethack_rs::{g, obj};
use std::collections::HashMap;
use std::ops::Add;
use std::ptr::null;
use std::sync::mpsc::{channel, Receiver, RecvError, RecvTimeoutError, Sender};
use std::thread::JoinHandle;
use std::time::{Duration, Instant};
use std::{cell::RefCell, os::raw::c_char};
use std::{
    ffi::{CStr, CString},
    os::raw::c_long,
    rc::Rc,
};

enum NHEvent {
    Session(SessionEvent),
    Timed(SessionEvent, i32),
    Coconut(CoconutSong),
}

thread_local! {
    static IPC: RefCell<Option<Rc<RefCell<Ipc>>>> = RefCell::new(None);
    static EVENT_SENDER: RefCell<Option<Sender<NHEvent>>> = RefCell::new(None);
}
static mut PLAYER_LOGIN_ID: Option<i32> = None;
static mut SESSION_START_TIME: Option<i32> = None;
static mut PLINES: Option<Vec<String>> = None;

static mut EVENT_SENDER_THREAD: Option<JoinHandle<()>> = None;

fn ipc() -> Rc<RefCell<Ipc>> {
    unsafe { oracle::init() };
    unsafe {
        if PLAYER_LOGIN_ID.is_none() {
            if let Ok(Ok(id)) = std::env::var("DB_USER_ID").map(|s| s.parse()) {
                PLAYER_LOGIN_ID = Some(id);
            } else {
                panic!("DB_USER_ID login id not set");
            }
        }
        if SESSION_START_TIME.is_none() {
            SESSION_START_TIME = Some(nethack_rs::ubirthday as i32);
        }
    }
    IPC.with(|ipc| {
        let mut tl_ipc = ipc.borrow_mut();
        if tl_ipc.is_none() {
            let tries = 0;
            loop {
                if let Ok(mut ipc) = Ipc::new_tcp() {
                    let auth = ipc.auth(
                        unsafe { PLAYER_LOGIN_ID }.expect("no player id when attempting IPC call"),
                        unsafe {
                            SESSION_START_TIME
                                .expect("no session start time when attempting IPC call")
                        },
                    );
                    if let Ok(true) = auth {
                        tl_ipc.replace(Rc::new(RefCell::new(ipc)));
                        break;
                    }
                }
                std::thread::sleep(Duration::from_millis((tries * tries * 10).min(1000)));
            }
        }
        tl_ipc.as_ref().unwrap().clone()
    })
}

fn debug_print(f: String) {
    let c_str = std::ffi::CString::new(f.as_str()).unwrap();
    unsafe { nethack_rs::pline(c_str.as_ptr()) };
}
fn debug_print_file(s: String) {
    use std::io::Write;
    let mut f = std::fs::OpenOptions::new().create(true).append(true).open("/tmp/nethackdebuglog").unwrap();
    write!(f, "{}", s).unwrap();
}


fn until_io_success<R, F: FnMut(&mut Ipc) -> Result<R>>( debug_msg: &str, mut f: F) -> Result<R> {
    loop {
        let ipc_ref = ipc();
        let mut ipc = ipc_ref.borrow_mut();
        match f(&mut *ipc) {
            Ok(r) => return Ok(r),
            Err(err @ Error::IO(_)) | Err(err @ Error::DecodeError(_)) => {
                debug_print_file(format!("IPC error for {}: {:?}\n", debug_msg, err));
                // clear IPC
                IPC.with(|ipc| {
                    ipc.borrow_mut().take();
                });
                continue;
            }
            Err(e) => return Err(e),
        }
    }
}

struct QueuedEventState {
    deadline: Instant,
    evt: SessionEvent,
}

fn event_sender_thread(evt_channel: Receiver<NHEvent>) {
    let mut deadline_by_name_and_str: HashMap<(String, String), QueuedEventState> = HashMap::new();
    loop {
        if unsafe { core::ptr::read(&PLAYER_LOGIN_ID as *const Option<i32>) }.is_none() {
            std::thread::sleep(Duration::from_millis(100))
        }
        if unsafe { core::ptr::read(&SESSION_START_TIME as *const Option<i32>) }.is_none() {
            std::thread::sleep(Duration::from_millis(100))
        }
        let min_deadline = deadline_by_name_and_str.values().min_by_key(|s| s.deadline);
        let result = if let Some(state) = min_deadline {
            evt_channel.recv_timeout(state.deadline.saturating_duration_since(Instant::now()))
        } else {
            evt_channel
                .recv()
                .map_err(|_: RecvError| RecvTimeoutError::Disconnected)
        };
        match result {
            Ok(evt) => match evt {
                NHEvent::Session(evt) => {
                    let _ = until_io_success("send session event", |ipc| ipc.send_session_event(evt.clone()));
                }
                NHEvent::Timed(evt, min_delay) => {
                    let entry = deadline_by_name_and_str
                        .entry((evt.name.clone(), evt.string_value.clone()));
                    entry
                        .and_modify(|state: &mut QueuedEventState| {
                            state.evt.value = evt.value;
                            if evt.value == 0 {
                                state.deadline = Instant::now();
                            }
                        })
                        .or_insert_with(|| QueuedEventState {
                            evt: evt.clone(),
                            deadline: Instant::now().add(Duration::from_secs(min_delay as u64)),
                        });
                }
                NHEvent::Coconut(evt) => {
                    let _ = until_io_success("send coconut", |ipc| ipc.coconut_song(evt.clone()));
                }
            },
            Err(RecvTimeoutError::Timeout) => {
                let mut to_remove = Vec::new();
                for (id, state) in &deadline_by_name_and_str {
                    if state.deadline <= Instant::now() {
                        to_remove.push(id.clone());
                    }
                }
                for id in to_remove {
                    let state = deadline_by_name_and_str.remove(&id).unwrap();
                    let _ = until_io_success("send session event with timeout", |ipc| ipc.send_session_event(state.evt.clone()));
                }
            }
            Err(RecvTimeoutError::Disconnected) => return,
        }
    }
}

#[no_mangle]
pub unsafe extern "C" fn rust_clear_gems() {
    let _ = until_io_success("clear gems", |ipc| ipc.wealth_tax());
}

#[no_mangle]
pub unsafe extern "C" fn rust_ipc_init(id: i32, session_starttime: i32) {}

#[no_mangle]
pub unsafe extern "C" fn bag_of_sharing_add(o: *mut obj) {
    let o = &*o;

    let obj_data = obj_to_obj_data(o);

    let _ = until_io_success("bag add", |ipc| ipc.bag_add(&obj_data));
}

pub(crate) unsafe fn obj_to_obj_data(o: &obj) -> ObjData {
    let name = if o.oextra != null_mut() && (&*o.oextra).oname != null_mut() {
        std::ffi::CStr::from_ptr((&*o.oextra).oname).to_string_lossy()
    } else {
        "".into()
    };
    ObjData {
        otyp: o.otyp as i32,
        quan: o.quan as i32,
        spe: o.spe as i32,
        oclass: o.oclass as i32,
        bitflags: o._bitfield_1.get(0, 32),
        corpsenm: o.corpsenm,
        usecount: o.usecount,
        oeaten: o.oeaten,
        age: o.age as i32,
        name: name.into(),
    }
}

#[no_mangle]
pub unsafe extern "C" fn bag_of_sharing_sync_all() {
    let mut iter = nethack_rs::g.invent;
    while iter != null_mut() {
        if nethack_rs::BAG_OF_SHARING as i16 == (&*iter).otyp {
            bag_of_sharing_sync(iter);
            break;
        }
        iter = (&*iter).nobj;
    }
}

unsafe fn obj_data_to_obj(obj_data: &ObjData) -> *mut obj {
    let obj_ptr = nethack_rs::mksobj(obj_data.otyp, 0, 0);
    if obj_ptr == null_mut() {
        return obj_ptr;
    }
    let obj = &mut *obj_ptr;
    obj.quan = obj_data.quan as c_long;

    obj.spe = obj_data.spe as i8;
    obj.oclass = obj_data.oclass as i8;
    obj._bitfield_1.set(0, 32, obj_data.bitflags);
    obj.corpsenm = obj_data.corpsenm;
    obj.usecount = obj_data.usecount;
    obj.oeaten = obj_data.oeaten;
    obj.age = obj_data.age as c_long;
    obj.owt = nethack_rs::weight(obj) as u32;
    obj.where_ = nethack_rs::OBJ_CONTAINED as i8;
    if obj_data.name != "" {
        let c_str = std::ffi::CString::new(obj_data.name.as_str()).unwrap();
        nethack_rs::oname(obj_ptr, c_str.as_ptr());
    }
    obj_ptr
}

#[no_mangle]
pub unsafe extern "C" fn bag_of_sharing_sync(bag_ptr: *mut obj) {
    let items = until_io_success("get_bag", |ipc| ipc.get_bag()).expect("sync error");

    let mut bag = &mut *bag_ptr;
    let mut otmp = null_mut();
    while bag.cobj != null_mut() {
        otmp = bag.cobj;
        (&mut *otmp).dbid = 0;
        nethack_rs::obj_extract_self(otmp);
        nethack_rs::obfree(otmp, null_mut());
    }
    for (dbid, obj_data) in items {
        let obj_ptr = obj_data_to_obj(&obj_data);
        let mut obj = &mut *obj_ptr;
        obj.dbid = dbid as c_long;
        obj.v.v_ocontainer = bag_ptr;
        obj.nobj = bag.cobj;
        bag.cobj = obj_ptr;
    }
    bag.owt = nethack_rs::weight(bag_ptr) as u32;
}

#[no_mangle]
pub unsafe extern "C" fn bag_of_sharing_remove(o: *mut obj) -> i32 {
    let o = &*o;
    let success = until_io_success("bag_remove", |ipc| ipc.bag_remove(o.dbid as i32)).expect("remove error");
    if success {
        0
    } else {
        1
    }
}

#[no_mangle]
pub unsafe extern "C" fn task_complete(category: *const c_char, name: *const c_char) {
    let category = CStr::from_ptr(category);
    let task_name = if name == null() {
        category.to_string_lossy().to_string()
    } else {
        let name = CStr::from_ptr(name);
        format!("{}_{}", category.to_string_lossy(), name.to_string_lossy())
    };
    let reward = until_io_success("task_complete", |ipc| ipc.task_complete(task_name.to_string()));
    if let Err(e) = reward {
        let result_line = format!("{:?}", e);
        let c_str = CString::new(result_line).unwrap();
        nethack_rs::pline(c_str.as_ptr());
    }
}

#[no_mangle]
pub unsafe extern "C" fn open_lootbox(rarity: i32) -> i32 /* number of gems gained */ {
    let reward = until_io_success("open_lootbox", |ipc| ipc.open_lootbox(rarity));
    match reward {
        Err(e) => {
            let result_line = format!("{:?}", e);
            let c_str = CString::new(result_line).unwrap();
            nethack_rs::pline(c_str.as_ptr());
            0
        }
        Ok(reward) => reward.reward,
    }
}

static mut LAST_CLAN_POWERS: Option<nethack_rs::team_bonus> = None;

#[no_mangle]
pub unsafe extern "C" fn get_clan_powers_delta(bonus: *mut nethack_rs::team_bonus) {
    let old_powers = LAST_CLAN_POWERS;
    get_clan_powers(bonus);
    LAST_CLAN_POWERS = Some(*bonus);
    if let Some(old) = old_powers {
        let mut bonus = &mut *bonus;
        bonus.hp = bonus.hp - old.hp;
        bonus.pw = bonus.pw - old.pw;
        bonus.ac = bonus.ac - old.ac;
        for i in 0..bonus.stats.len() {
            bonus.stats[i] = bonus.stats[i] - old.stats[i];
        }
    }
}

static mut CACHED_CLAN_POWERS: Option<nethack_rs::team_bonus> = None;
static mut CACHED_CLAN_POWERS_TIME: Option<Instant> = None;

#[no_mangle]
pub unsafe extern "C" fn get_clan_powers(bonus: *mut nethack_rs::team_bonus) {
    if let Some(cache_time) = CACHED_CLAN_POWERS_TIME {
        if Instant::now().saturating_duration_since(cache_time) < Duration::from_secs(1) {
            *bonus = CACHED_CLAN_POWERS.unwrap();
            return;
        }
    }
    let powers = until_io_success("get_clan_powers", |ipc| ipc.get_clan_powers());
    match powers {
        Err(e) => {
            let result_line = format!("{:?}", e);
            let c_str = CString::new(result_line).unwrap();
            nethack_rs::pline(c_str.as_ptr());
        }
        Ok(powers) => {
            *bonus = std::mem::zeroed::<nethack_rs::team_bonus>();
            let mut bonus = &mut *bonus;
            for power in powers.powers {
                match power.name.as_str() {
                    "hp" => bonus.hp = power.num,
                    "pw" => bonus.pw = power.num,
                    "ac" => bonus.ac = power.num,
                    "str" => bonus.stats[0] = power.num,
                    "int" => bonus.stats[1] = power.num,
                    "wis" => bonus.stats[2] = power.num,
                    "dex" => bonus.stats[3] = power.num,
                    "con" => bonus.stats[4] = power.num,
                    "cha" => bonus.stats[5] = power.num,
                    "ads" => bonus.ads = power.num,
                    "helm" => bonus.helm = power.num,
                    "body" => bonus.body = power.num,
                    "gloves" => bonus.gloves = power.num,
                    "boots" => bonus.boots = power.num,
                    "cloak" => bonus.cloak = power.num,
                    "bag" => bonus.bag = power.num,
                    name => panic!("wat is {}", name),
                }
            }
            CACHED_CLAN_POWERS = Some(*bonus);
            CACHED_CLAN_POWERS_TIME = Some(Instant::now());
        }
    }
}

#[no_mangle]
pub unsafe extern "C" fn save_equipment(item: *mut obj, slot: i32) {
    let obj_data = obj_to_obj_data(&*item);
    let status = until_io_success("save_equipment", |ipc| ipc.save_equipment(slot, &obj_data));
    match status {
        Err(e) => {
            let result_line = format!("{:?}", e);
            let c_str = CString::new(result_line).unwrap();
            nethack_rs::pline(c_str.as_ptr());
        }
        Ok(_) => {}
    }
}

#[no_mangle]
pub unsafe extern "C" fn load_saved_equipments(callback: extern "C" fn(i32, *mut obj)) {
    let equipments = until_io_success("saved_equipment", |ipc| ipc.get_saved_equipment());
    if let Ok(equipments) = equipments {
        for (slot, eq) in equipments.iter() {
            let obj_ptr = obj_data_to_obj(eq);
            let mut obj = &mut *obj_ptr;
            obj.where_ = nethack_rs::OBJ_FREE as i8;
            callback(*slot, obj_ptr)
        }
    }
}

#[no_mangle]
pub unsafe extern "C" fn send_session_event(
    evt_name: *const c_char,
    value: i32,
    previous_value: i32,
    string_value: *const c_char,
) {
    let evt = make_session_event(
        evt_name,
        string_value,
        previous_value,
        value,
        null(),
        null(),
    );
    enqueue_event(NHEvent::Session(evt));
}

#[no_mangle]
pub unsafe extern "C" fn send_session_event_fat(
    evt_name: *const c_char,
    value: i32,
    previous_value: i32,
    string_value: *const c_char,
    caused_by: *const c_char,
    action_name: *const c_char,
) {
    let evt = make_session_event(
        evt_name,
        string_value,
        previous_value,
        value,
        caused_by,
        action_name,
    );
    enqueue_event(NHEvent::Session(evt));
}

unsafe fn make_session_event(
    evt_name: *const i8,
    string_value: *const i8,
    previous_value: i32,
    value: i32,
    caused_by: *const c_char,
    action_name: *const c_char,
) -> SessionEvent {
    let evt_name = if evt_name != null_mut() {
        std::ffi::CStr::from_ptr(evt_name)
            .to_string_lossy()
            .to_string()
    } else {
        "".into()
    };
    let string_value = if string_value != null_mut() {
        std::ffi::CStr::from_ptr(string_value)
            .to_string_lossy()
            .to_string()
    } else {
        "".into()
    };
    let caused_by = if caused_by != null_mut() {
        std::ffi::CStr::from_ptr(caused_by)
            .to_string_lossy()
            .to_string()
    } else {
        "".into()
    };
    let action_name = if action_name != null_mut() {
        std::ffi::CStr::from_ptr(action_name)
            .to_string_lossy()
            .to_string()
    } else {
        "".into()
    };
    let evt = SessionEvent {
        session_turn: g.moves as i32,
        name: evt_name,
        previous_value,
        value,
        string_value,
        caused_by,
        action_name,
    };
    evt
}

unsafe fn enqueue_event(evt: NHEvent) {
    if EVENT_SENDER_THREAD.is_none() {
        let (sender, receiver) = channel();
        EVENT_SENDER.with(|evt_sender| {
            evt_sender.borrow_mut().replace(sender);
        });
        EVENT_SENDER_THREAD = Some(std::thread::spawn(|| event_sender_thread(receiver)));
    }
    EVENT_SENDER.with(|sender| {
        let _ = sender.borrow().as_ref().unwrap().send(evt);
    })
}

#[no_mangle]
pub unsafe extern "C" fn send_session_event_timed(
    evt_name: *const c_char,
    new_value: i32,
    previous_value: i32,
    string_value: *const c_char,
    min_delay_seconds: i32,
) {
    let evt = make_session_event(
        evt_name,
        string_value,
        previous_value,
        new_value,
        null(),
        null(),
    );
    enqueue_event(NHEvent::Timed(evt, min_delay_seconds));
}

#[no_mangle]
pub unsafe extern "C" fn coconut_handle_pline(text: *const c_char) {
    let text = if text != null_mut() {
        std::ffi::CStr::from_ptr(text).to_string_lossy().to_string()
    } else {
        "".into()
    };
    if text == "" {
        return;
    }
    if PLINES.is_none() {
        PLINES = Some(Vec::new());
    }
    let plines = PLINES.as_mut().unwrap();
    if plines.last() != Some(&text) {
        if plines.len() > 50 {
            plines.remove(0);
        }
        plines.push(text.to_string());
    }
}

static mut COCONUT_LINES_LAST_SEND_TIME: Option<Instant> = None;

#[no_mangle]
pub unsafe extern "C" fn maybe_send_coconut_plines() {
    if let Some(cache_time) = COCONUT_LINES_LAST_SEND_TIME {
        if Instant::now().saturating_duration_since(cache_time) < Duration::from_secs(3) {
            return;
        }
    }

    COCONUT_LINES_LAST_SEND_TIME = Some(Instant::now());

    send_coconut_song_request(false);
}

#[no_mangle]
pub unsafe extern "C" fn send_coconut_song_request(is_death_event: bool) {
    if let Some(plines) = PLINES.as_ref() {
        if plines.len() > 10 {
            let monsters_around = oracle::get_monster_list().into_iter().map(|m| m.name).collect::<Vec<_>>();
            let items_around = oracle::get_map_item_list().into_iter().map(|m| m.name).collect::<Vec<_>>();
            let mut iter = nethack_rs::g.invent;
            let mut equipped_items = Vec::new();
            while iter != null_mut() {
                let item = &*iter;
                if (item.owornmask & nethack_rs::W_ARM as i64 ) != 0 /* Body armor */
                    || (item.owornmask & nethack_rs::W_ARMC as i64 ) != 0 /* Cloak */ 
                    || (item.owornmask & nethack_rs::W_ARMH as i64 ) != 0 /* Helmet/hat */
                    || (item.owornmask & nethack_rs::W_ARMS as i64 ) != 0 /* Shield */
                    || (item.owornmask & nethack_rs::W_ARMG as i64 ) != 0 /* Gloves/gauntlets */
                    || (item.owornmask & nethack_rs::W_ARMF as i64 ) != 0 /* Footwear */
                    || (item.owornmask & nethack_rs::W_ARMU as i64 ) != 0 /* Undershirt */
                    || (item.owornmask & nethack_rs::W_WEP as i64 ) != 0 /* Wielded weapon */
                {
                    equipped_items.push(obj_to_obj_data(item).name);
                }
                iter = (&*iter).nobj;

            }
            debug_print(format!("{} sending coconuts!", is_death_event));
            enqueue_event(NHEvent::Coconut(CoconutSong {
                plines: plines.clone(),
                equipped_items,
                monsters_around,
                items_around,
                is_death_event,
            }));
        }
    }
}
