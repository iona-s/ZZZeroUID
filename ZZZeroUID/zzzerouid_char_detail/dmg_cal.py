from typing import Dict, List

from ..utils.zzz_map import skill_param


def to_bl(char_dict: dict) -> Dict[str, float]:
    if str(char_dict['id']) not in skill_param:
        return {}

    result = {}

    skill_p = skill_param[str(char_dict['id'])]

    skill_list = char_dict['skills']
    for skill in skill_list:
        skill_level: int = skill['level']
        for item in skill['items']:
            item_title: str = item['title']
            if item_title not in skill_p:
                continue

            for all_sub in skill_p[item_title]:
                bl = skill_p[item_title][all_sub]

                name = f'{item_title} - {all_sub}'
                name = name.replace('普通攻击', '普攻')
                name = name.replace('蓄力', '')
                name = name.replace('伤害倍率', '')
                name = name.strip()

                if name.endswith(' -'):
                    name = name[:-2]

                result[name] = (bl[0] + bl[1] * (skill_level - 1)) / 10000

    return result


def to_dmg(char_dict: dict, bl_dict: Dict[str, float]) -> Dict[str, List[str]]:
    char_p: List[Dict] = char_dict['properties']
    char_level: int = char_dict['level']
    enemy_level = 70

    atk = 0
    dmg_bouns = 0
    crit_dmg = 0
    crit_rate = 0
    ct_value = 0
    ct_percent = 0
    def_add = 1
    resist = 1
    easy_dmg = 1

    self_def: float = 0.1551 * char_level**2 + 3.141 * char_level + 47.2039
    enemy_def = 0.1551 * enemy_level**2 + 3.141 * enemy_level + 47.2039

    result = {'动作名称': ['暴击值', '期望值', '普通值']}

    for p in char_p:
        if p['property_id'] == 2:
            atk = float(p['final'])
        elif p['property_id'] == 6:
            crit_dmg = float(p['final'][:-1]) / 100
        elif p['property_id'] == 232:
            ct_value = float(p['final'])
        elif p['property_id'] == 9:
            ct_percent = float(p['final'][:-1]) / 100
        elif p['property_id'] == 5:
            crit_rate = float(p['final'][:-1]) / 100
        elif 310 < p['property_id'] < 320:
            dmg_bouns = float(p['final'][:-1]) / 100

    enemy_def = enemy_def * def_add * (1 - ct_percent) - ct_value
    enemy_def = enemy_def if enemy_def > 0 else 0

    def_area: float = self_def / (self_def + enemy_def)

    for bl in bl_dict:
        name = bl
        base = (
            bl_dict[bl] * atk * (1 + dmg_bouns) * def_area * resist * easy_dmg
        )
        result[name] = [
            '{:.2f}'.format(base * (1 + crit_dmg)),
            '{:.2f}'.format(
                base * (1 + crit_dmg) * crit_rate + base * (1 - crit_rate)
            ),
            '{:.2f}'.format(base),
        ]

    return result


def get_dmg(char_dict: dict) -> Dict[str, List[str]]:
    bl_dict = to_bl(char_dict)
    dmg_dict = to_dmg(char_dict, bl_dict)
    return dmg_dict
