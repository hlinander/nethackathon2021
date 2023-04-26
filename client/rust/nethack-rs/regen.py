import os
import subprocess

data = subprocess.check_output(["bindgen", "../../../client/NetHack/include/hack.h"]) 

s = data.decode()

search = """pub fn new_bitfield_1(
        flags: ::std::os::raw::c_uint,
        horizontal: ::std::os::raw::c_uint,
        lit: ::std::os::raw::c_uint,
        waslit: ::std::os::raw::c_uint,
        roomno: ::std::os::raw::c_uint,
        edge: ::std::os::raw::c_uint,
        candig: ::std::os::raw::c_uint,
    ) -> __BindgenBitfieldUnit<[u8; 2usize]> {
        let mut __bindgen_bitfield_unit: __BindgenBitfieldUnit<[u8; 2usize]> = Default::default();
        __bindgen_bitfield_unit.set(0usize, 5u8, {
            let flags: u32 = unsafe { ::std::mem::transmute(flags) };
            flags as u64
        });"""

replacement = """pub fn new_bitfield_1(
        flags_: ::std::os::raw::c_uint,
        horizontal: ::std::os::raw::c_uint,
        lit: ::std::os::raw::c_uint,
        waslit: ::std::os::raw::c_uint,
        roomno: ::std::os::raw::c_uint,
        edge: ::std::os::raw::c_uint,
        candig: ::std::os::raw::c_uint,
    ) -> __BindgenBitfieldUnit<[u8; 2usize]> {
        let mut __bindgen_bitfield_unit: __BindgenBitfieldUnit<[u8; 2usize]> = Default::default();
        __bindgen_bitfield_unit.set(0usize, 5u8, {
            let flags_: u32 = unsafe { ::std::mem::transmute(flags_) };
            flags_ as u64
        });"""

s = s.replace(search, replacement)


os.makedirs("src", exist_ok=True)
open("src/lib.rs", 'w').write(s)
