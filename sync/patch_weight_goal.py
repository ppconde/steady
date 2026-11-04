"""Build-time patch: make garmin-grafana also store the Garmin weight goal as WeightGoal.goal_kg."""
import sys

FUNC = '''
def get_weight_goal_points(date_str):
    """Steady patch: the weight goal in effect on this day."""
    try:
        raw = garmin_obj.get_weight_goal(date_str, date_str)
    except Exception as err:
        logging.warning(f"Weight goal unavailable for {date_str}: {err}")
        return []

    # ponytail: response shape unverified, so take the first positive goal-like number anywhere in it
    def find(o):
        if isinstance(o, dict):
            for k in ("goalValue", "weightGoal", "value"):
                if isinstance(o.get(k), (int, float)) and o[k] > 0:
                    return o[k]
            o = list(o.values())
        if isinstance(o, list):
            for v in o:
                g = find(v)
                if g:
                    return g
        return None

    goal = find(raw)
    if not goal:
        logging.info(f"No weight goal for {date_str}: {str(raw)[:200]}")
        return []
    return [{"measurement": "WeightGoal",
             "time": datetime.strptime(date_str, "%Y-%m-%d").replace(hour=0, tzinfo=pytz.UTC).isoformat(),
             "tags": {"Device": GARMIN_DEVICENAME, "Database_Name": INFLUXDB_DATABASE},
             "fields": {"goal_kg": float(goal / 1000 if goal > 500 else goal)}}]  # Garmin uses grams

'''
CALL_AT = "        write_points_to_influxdb(get_body_composition(date_str))\n"

path = sys.argv[1]
src = open(path).read()
assert src.count("def get_body_composition(") == 1 and src.count(CALL_AT) == 1, "garmin_fetch.py changed upstream"
src = src.replace("def get_body_composition(", FUNC.lstrip("\n") + "\ndef get_body_composition(")
src = src.replace(CALL_AT, CALL_AT + "        write_points_to_influxdb(get_weight_goal_points(date_str))\n")
open(path, "w").write(src)
