from constants import TZs
from typing import Tuple


def TZ(current: str, plus_hour: bool = None) -> Tuple[str, int, int]:
    if TZs.count(current) == 1:
        ind = TZs.index(current)
        if plus_hour == True:
            ind = 0 if ind == 26 else ind + 1
        elif plus_hour == False:
            ind = 26 if ind == 0 else ind - 1
        curr = TZs[ind]
    else:
        curr = "+08:00"
    # op = operator.add if ind>11 else operator.sub
    hours, minutes = map(int, curr.split(":"))
    return (curr, hours, minutes)
