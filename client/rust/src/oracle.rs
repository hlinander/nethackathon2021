use std::{
    io::{stdin, stdout, Read, Write},
    os::unix::prelude::AsFd,
    time::Duration,
};

use crossterm::{cursor::*, terminal::Clear, *};

#[no_mangle]
pub unsafe extern "C" fn oracle_prompt() -> i32 {
    let mut line = String::new();
    execute!(stdout(), MoveTo(0, 25), EnableBlinking).unwrap();
    loop {
        if let Some(c) = char::from_u32(nethackathon_getch() as u32) {
            if c == '\n' {
                execute!(stdout(), Clear(terminal::ClearType::CurrentLine)).unwrap();
                break;
            }
            line += &c.to_string();
            print!("{}", c);
            stdout().flush().unwrap();
        }
    }
    0
}

static mut COUNTER: i32 = 0;

#[no_mangle]
pub unsafe extern "C" fn nethackathon_getch() -> i32 {
    let mut needs_update = true;
    let mut update_ui = || {
        COUNTER += 1;
        needs_update = COUNTER % 1000 == 0;
        if needs_update {
            libc::fcntl(
                0,
                libc::F_SETFL,
                libc::fcntl(0, libc::F_GETFL) & !libc::O_NONBLOCK,
            );
            execute!(stdout(), SavePosition, MoveTo(0, 26)).unwrap();

            print!("hej {}", COUNTER);
            execute!(stdout(), RestorePosition).unwrap();
            stdout().flush().unwrap();
        }
    };

    let mut selector = selecting::Selector::new();
    selector.add_read(&stdin());
    update_ui();
    loop {
        libc::fcntl(
            0,
            libc::F_SETFL,
            libc::fcntl(0, libc::F_GETFL) | libc::O_NONBLOCK,
        );
        let mut byte = [0u8; 4];
        match stdin().lock().read(&mut byte) {
            Ok(len) => {
                if len > 0 {
                    libc::fcntl(
                        0,
                        libc::F_SETFL,
                        libc::fcntl(0, libc::F_GETFL) & !libc::O_NONBLOCK,
                    );
                    return i32::from_le_bytes(byte);
                } else {
                    update_ui();
                }
            }
            Err(err) if err.kind() == std::io::ErrorKind::WouldBlock => update_ui(),
            Err(err) => panic!("read error {:?}", err),
        }
        std::thread::sleep(Duration::from_millis(1));
        // match selector.select_timeout(Duration::from_millis(200)) {
        //     Ok(result) => {
        //         if result.is_read(&stdin()) {
        //             // let mut buf = [0u8; 4];
        //             // if libc::feof(stdin().lock().) > 0 {
        //             //     // let result = stdin().lock().read(&mut buf).unwrap();
        //             //     // return i32::from_le_bytes(buf);
        //             //     return libc::getchar();
        //             // }
        //         } else {
        //             update_ui();
        //         }
        //     }
        //     Err(err) if err.kind() == std::io::ErrorKind::TimedOut => {
        //         update_ui();
        //     }
        //     Err(err) => panic!("select error {:?}", err),
        // }
    }
}
