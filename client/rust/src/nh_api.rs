use crate::ipc::Ipc;
use crate::nh_proto::ObjData;
use core::ptr::null_mut;
use nethack_rs::obj;
use std::cell::RefCell;
use std::io::Result;

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

fn until_success<R, F: FnMut(&mut Ipc) -> Result<R>>(mut f: F) -> R {
    loop {
        let mut ipc_ref = ipc();
        match f(&mut *ipc_ref) {
            Ok(r) => return r,
            Err(_) => {
                // clear IPC
                unsafe {
                    IPC = None;
                }
                // reconnect IPC
                ipc_ref = ipc();
            }
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
        quan: o.quan,
        spe: o.spe as i32,
        oclass: o.oclass as i32,
        bitflags: o._bitfield_1.get(0, 32),
        corpsenm: o.corpsenm,
        usecount: o.usecount,
        oeaten: o.oeaten,
        age: o.age,
        name: name.into(),
    };

    until_success(|ipc| ipc.bag_add(&obj_data));
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
    let items = until_success(|ipc| ipc.get_bag());
    // debug_print(format!("sync bag {:?}", items));

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
        obj.dbid = dbid;
        obj.quan = obj_data.quan;

        obj.spe = obj_data.spe as i8;
        obj.oclass = obj_data.oclass as i8;
        obj._bitfield_1.set(0, 32, obj_data.bitflags);
        obj.corpsenm = obj_data.corpsenm;
        obj.usecount = obj_data.usecount;
        obj.oeaten = obj_data.oeaten;
        obj.age = obj_data.age;
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
    let success = until_success(|ipc| ipc.bag_remove(o.dbid));
    if success {
        0
    } else {
        1
    }
}
