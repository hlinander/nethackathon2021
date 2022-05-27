#include <stdio.h>

#ifdef __clang__
/* clang's gcc emulation is sufficient for nethack's usage */
#error IN CLANG
#ifndef __GNUC__
#define __GNUC__ 4
#endif
#endif

#ifndef __GNUC__
#error HOOOOOOOOOOP
#else
#error GNUC DEFINED
#endif

#define __warn_unused_result__ /*empty*/
#if __GNUC_PREREQ (3,4) || __glibc_has_attribute (__warn_unused_result__)
#endif

void main() {}
