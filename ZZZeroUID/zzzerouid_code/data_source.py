import json
from time import time
from re import sub, compile, findall
from typing import List, Union, Literal
from datetime import datetime, timezone, timedelta

from httpx import AsyncClient

TZ = timezone(timedelta(hours=8))


async def get_data(
    type: Literal["activity", "index", "code"], data: dict = {}
) -> dict:
    """米哈游接口请求"""

    url = {
        "activity": "https://bbs-api.miyoushe.com/apihub/api/home/new?gids=8&parts=1%2C3%2C4&device=OnePlus%20IN2025&cpu=placeholder&version=3",
        "index": "https://api-takumi.mihoyo.com/event/miyolive/index",
        "code": "https://api-takumi-static.mihoyo.com/event/miyolive/refreshCode",
    }
    async with AsyncClient() as client:
        try:
            if type == "index":
                res = await client.get(
                    url[type], headers={"x-rpc-act_id": data.get("actId", "")}
                )
            elif type == "code":
                res = await client.get(
                    url[type],
                    params={
                        "version": data.get("version", ""),
                        "time": f"{int(time())}",
                    },
                    headers={"x-rpc-act_id": data.get("actId", "")},
                )
            else:
                res = await client.get(url[type])
            return res.json()
        except Exception as e:
            return {"error": f"[{e.__class__.__name__}] {type} 接口请求错误"}


async def get_act_id() -> str:
    """获取 ``act_id``"""

    ret = await get_data("activity")
    if ret.get("error") or ret.get("retcode") != 0:
        return ""

    act_id = ""
    keywords = ["前瞻直播"]
    for nav in ret["data"]["navigator"]:
        name = nav.get("name")
        if not name:
            continue
        if not all(word in name for word in keywords):
            continue
        app_path = nav.get("app_path")
        matched = findall(r"act_id=(.*?)\&", app_path)
        if matched:
            act_id = matched[0]
        if act_id:
            break

    return act_id


async def get_live_data(act_id: str) -> dict:
    """获取直播数据，尤其是 ``code_ver``"""

    ret = await get_data("index", {"actId": act_id})
    if ret.get("error") or ret.get("retcode") != 0:
        return {"error": ret.get("error") or "前瞻直播数据异常"}

    live_raw = ret["data"]["live"]
    live_temp = json.loads(ret["data"]["template"])
    live_data = {
        "code_ver": live_raw["code_ver"],
        "title": live_raw["title"].replace("特别直播", ""),
        "header": live_temp["kvDesktop"],
        "room": live_temp["liveConfig"][0]["desktop"],
    }
    if live_raw["is_end"]:
        live_data["review"] = live_temp["reviewUrl"]["args"]["post_id"]
    else:
        now = datetime.fromtimestamp(time(), TZ)
        start = datetime.strptime(
            live_raw["start"], "%Y-%m-%d %H:%M:%S"
        ).replace(tzinfo=TZ)
        if now < start:
            live_data["start"] = live_raw["start"]

    return live_data


async def get_code(version: str, act_id: str) -> Union[dict, List[dict]]:
    """获取兑换码"""

    ret = await get_data("code", {"version": version, "actId": act_id})
    if ret.get("error") or ret.get("retcode") != 0:
        return {"error": ret.get("error") or "兑换码数据异常"}
    code_data = []
    for code_info in ret["data"]["code_list"]:
        remove_tag = compile("<.*?>")
        code_data.append(
            {
                "items": sub(remove_tag, "", code_info["title"]),
                "code": code_info["code"],
            }
        )
    return code_data


async def get_code_msg() -> str:
    """生成最新前瞻直播兑换码消息"""

    act_id = await get_act_id()
    if not act_id:
        return "暂无前瞻直播资讯！"

    live_data = await get_live_data(act_id)
    if live_data.get("error"):
        return live_data["error"]

    code_data = await get_code(live_data["code_ver"], act_id)
    if isinstance(code_data, dict):
        return code_data["error"]

    code_msg = f'{live_data["title"]}\n'
    # 只有一个兑换码，直接取第0个
    try:
        code = code_data[0]
        code_msg += f'{code["items"]}:\n{code["code"]}\n'
        return code_msg.strip()
    except:  # noqa: E722
        return "获取兑换码失败！"
