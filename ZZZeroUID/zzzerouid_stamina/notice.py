from typing import Dict

from gsuid_core.gss import gss
from gsuid_core.logger import logger
from gsuid_core.utils.database.models import GsUser
from gsuid_core.sv import get_plugin_available_prefix

from ..utils.zzzero_api import zzz_api
from ..utils.api.models import ZZZNoteResp
from ..utils.database.model import ZzzPush
from ..zzzerouid_config.zzzero_config import ZZZ_CONFIG

prefix = get_plugin_available_prefix("ZZZeroUID")
ZZZ_NOTICE = f'\n可发送[{prefix}便签]或者[{prefix}每日]来查看更多信息!'


async def get_notice_list() -> Dict[str, Dict[str, Dict]]:
    msg_dict: Dict[str, Dict[str, Dict]] = {}
    for _ in gss.active_bot:
        user_list = await GsUser.get_push_user_list('zzz')
        for user in user_list:
            if user.zzz_uid is not None:
                raw_data = await zzz_api.get_zzz_note_info(user.zzz_uid)
                if isinstance(raw_data, int):
                    logger.error(f"[zzz推送提醒]获取{user.zzz_uid}的数据失败!")
                    continue
                push_data = await ZzzPush.select_data_by_uid(
                    user.zzz_uid, "zzz"
                )
                if push_data is None:
                    continue
                msg_dict = await all_check(
                    user.bot_id,
                    raw_data,
                    push_data.__dict__,
                    msg_dict,
                    user.user_id,
                    user.zzz_uid,
                )
    return msg_dict


async def all_check(
    bot_id: str,
    raw_data: ZZZNoteResp,
    push_data: Dict,
    msg_dict: Dict[str, Dict[str, Dict]],
    user_id: str,
    uid: str,
) -> Dict[str, Dict[str, Dict]]:
    _check = await check(
        raw_data,
        push_data.get("energy_value", 0),
    )

    # 检查条件
    if push_data["energy_is_push"] == "on":
        if not ZZZ_CONFIG.get_config("CrazyNotice").data:
            if not _check:
                await ZzzPush.update_data_by_uid(
                    uid, bot_id, "zzz", **{"energy_is_push": "off"}
                )

    # 准备推送
    if _check:
        if push_data["energy_push"] == "off":
            pass
        else:
            notice = _check
            # 初始化
            if bot_id not in msg_dict:
                msg_dict[bot_id] = {"direct": {}, "group": {}}
                direct_data = msg_dict[bot_id]["direct"]
                group_data = msg_dict[bot_id]["group"]

            # on 推送到私聊
            if push_data["energy_push"] == "on":
                # 添加私聊信息
                if user_id not in direct_data:
                    direct_data[user_id] = notice
                else:
                    direct_data[user_id] += notice
            # 群号推送到群聊
            else:
                # 初始化
                gid = push_data["energy_push"]
                if gid not in group_data:
                    group_data[gid] = {}

                if user_id not in group_data[gid]:
                    group_data[gid][user_id] = notice
                else:
                    group_data[gid][user_id] += notice

            await ZzzPush.update_data_by_uid(
                uid, bot_id, 'zzz', **{"energy_is_push": "on"}
            )
    return msg_dict


async def check(data: ZZZNoteResp, limit: int) -> str:
    energy_data = data['energy']
    progress = energy_data['progress']
    current = progress['current']
    max_power = progress['max']
    base_notice = '[绝区零] 你的电量'
    if current >= max_power:
        return base_notice + '已满！' + ZZZ_NOTICE
    if current >= limit:
        current_status = f'当前{current}/{max_power}，将于'
        if energy_data['day_type'] == 1:
            current_status += '今'
        else:
            current_status += '明'
        minute = str(energy_data['minute']).zfill(2)
        current_status += f'日{energy_data["hour"]}:{minute}回满'
        return base_notice + '已达提醒阈值！\n' + current_status + ZZZ_NOTICE
    return ''
