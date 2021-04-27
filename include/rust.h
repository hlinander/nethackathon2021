#pragma once

#include <stdarg.h>
#include <stdbool.h>
#include <stdint.h>
#include <stdlib.h>
#include "hack.h"
#define obj struct obj

void bag_of_sharing_add(obj *o);

#undef obj
