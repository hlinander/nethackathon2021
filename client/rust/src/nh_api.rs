use crate::ipc::{Error, Ipc, Result};
use crate::nh_proto::ObjData;
use core::ptr::null_mut;
use nethack_rs::obj;
use std::ptr::null;
use std::{cell::RefCell, os::raw::c_char};
use std::{
    ffi::{CStr, CString},
    os::raw::c_long,
};

static mut IPC: Option<RefCell<Ipc>> = None;
static mut PLAYER_LOGIN_ID: Option<i32> = None;

fn ipc() -> impl std::ops::DerefMut<Target = Ipc> {
    unsafe {
        if IPC.is_none() {
            loop {
                if let Ok(mut ipc) = Ipc::new() {
                    let auth =
                        ipc.auth(PLAYER_LOGIN_ID.expect("no player id when attempting IPC call"));
                    if let Ok(true) = auth {
                        IPC = Some(RefCell::new(ipc));
                        break;
                    }
                }
                std::thread::sleep_ms(500);
            }
        }
        IPC.as_ref().unwrap().borrow_mut()
    }
}

fn debug_print(f: String) {
    let c_str = std::ffi::CString::new(f.as_str()).unwrap();
    unsafe { nethack_rs::pline(c_str.as_ptr()) };
}

fn until_io_success<R, F: FnMut(&mut Ipc) -> Result<R>>(mut f: F) -> Result<R> {
    loop {
        let mut ipc_ref = ipc();
        match f(&mut *ipc_ref) {
            Ok(r) => return Ok(r),
            Err(Error::IO(_)) | Err(Error::DecodeError(_)) => {
                // clear IPC
                unsafe {
                    IPC = None;
                }
                // reconnect IPC
                drop(ipc_ref);
                ipc_ref = ipc();
            }
            Err(e) => return Err(e),
        }
    }
}

#[no_mangle]
pub unsafe extern "C" fn rust_ipc_init(id: i32) {
    PLAYER_LOGIN_ID = Some(id);
}

#[no_mangle]
pub unsafe extern "C" fn bag_of_sharing_add(o: *mut obj) {
    let o = &*o;

    let name = if o.oextra != null_mut() && (&*o.oextra).oname != null_mut() {
        std::ffi::CStr::from_ptr((&*o.oextra).oname).to_string_lossy()
    } else {
        "".into()
    };
    let obj_data = ObjData {
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
    };

    let _ = until_io_success(|ipc| ipc.bag_add(&obj_data));
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

#[no_mangle]
pub unsafe extern "C" fn bag_of_sharing_sync(bag_ptr: *mut obj) {
    let items = until_io_success(|ipc| ipc.get_bag()).expect("sync error");

    let mut bag = &mut *bag_ptr;
    let mut otmp = null_mut();
    while bag.cobj != null_mut() {
        otmp = bag.cobj;
        (&mut *otmp).dbid = 0;
        nethack_rs::obj_extract_self(otmp);
        nethack_rs::obfree(otmp, null_mut());
    }
    for (dbid, obj_data) in items {
        let obj_ptr = nethack_rs::mksobj(obj_data.otyp, 0, 0);
        if obj_ptr == null_mut() {
            continue;
        }
        let obj = &mut *obj_ptr;
        obj.dbid = dbid as c_long;
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
        obj.v.v_ocontainer = bag_ptr;
        obj.nobj = bag.cobj;
        if obj_data.name != "" {
            let c_str = std::ffi::CString::new(obj_data.name.as_str()).unwrap();
            nethack_rs::oname(obj_ptr, c_str.as_ptr());
        }
        bag.cobj = obj_ptr;
    }
    bag.owt = nethack_rs::weight(bag_ptr) as u32;
}

#[no_mangle]
pub unsafe extern "C" fn bag_of_sharing_remove(o: *mut obj) -> i32 {
    let o = &*o;
    let success = until_io_success(|ipc| ipc.bag_remove(o.dbid as i32)).expect("remove error");
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
    let reward = until_io_success(|ipc| ipc.task_complete(task_name.to_string()));
    if let Err(e) = reward {
        let result_line = format!("{:?}", e);
        let c_str = CString::new(result_line).unwrap();
        nethack_rs::pline(c_str.as_ptr());
    }
}

#[no_mangle]
pub unsafe extern "C" fn open_lootbox(rarity: i32) -> i32 /* number of gems gained */ {
    let reward = until_io_success(|ipc| ipc.open_lootbox(rarity));
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
        for i in 0..bonus.stats.len(){
            bonus.stats[i] = bonus.stats[i] - old.stats[i];
        }
    }
}

#[no_mangle]
pub unsafe extern "C" fn get_clan_powers(bonus: *mut nethack_rs::team_bonus) {
    let powers = until_io_success(|ipc| ipc.get_clan_powers());
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
                    name => panic!("wat is {}", name),
                }
            }
        },
    }
}

#[no_mangle]
pub unsafe extern "C" fn save_equipment(item: *mut obj) {

}

#[no_mangle]
pub unsafe extern "C" fn load_saved_equipments(callback: extern "C" fn(*mut obj)) {

}