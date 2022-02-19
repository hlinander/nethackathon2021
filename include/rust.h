#pragma once

#include <stdarg.h>
#include <stdbool.h>
#include <stdint.h>
#include <stdlib.h>
#include "hack.h"
#define obj struct obj

void rust_ipc_init(int32_t id, int32_t session_starttime);

void bag_of_sharing_add(obj *o);

void bag_of_sharing_sync_all(void);

void bag_of_sharing_sync(obj *bag_ptr);

int32_t bag_of_sharing_remove(obj *o);

void task_complete(const char *category, const char *name);

int32_t open_lootbox(int32_t rarity);

void get_clan_powers_delta(team_bonus *bonus);

void get_clan_powers(team_bonus *bonus);

void save_equipment(obj *item, int32_t slot);

void load_saved_equipments(void (*callback)(int32_t, obj*));

#undef obj
