import re

FILTER_SEPARATOR_REGEX = "[re]"
FILTER_SEPARATOR_EQUALS = "[eq]"
FILTER_SEPARATOR_NOT_EQUALS = "[ne]"
FILTER_SEPARATOR_LESS_THAN = "[lt]"
FILTER_SEPARATOR_GREATER_THAN = "[gt]"
FILTER_SEPARATOR_LESS_THAN_OR_EQUALS = "[lte]"
FILTER_SEPARATOR_GREATER_THAN_OR_EQUALS = "[gte]"
FILTER_SEPARATOR_CONTAINS = "[contains]"
FILTER_SEPARATOR_NOT_CONTAINS = "[not_contains]"
FILTER_SEPARATOR_STARTS_WITH = "[starts_with]"
FILTER_SEPARATOR_ENDS_WITH = "[ends_with]"


class FilterEngine:
    def __init__(self, data: list[dict], filters: list[str], columns: list[str]):
        self.data = data
        self.columns = columns
        self.filter_rules = self._parse_filters(filters)

    def _parse_filters(self, filter_expr):
        filters = {}
        for expr in filter_expr:
            if FILTER_SEPARATOR_REGEX in expr: # regex match filter
                key, value = expr.split(FILTER_SEPARATOR_REGEX, 1)
                filter = {
                    "type": FILTER_SEPARATOR_REGEX,
                    "value": re.compile(value.strip())
                }
                filters[key.strip()] = filter
            elif FILTER_SEPARATOR_EQUALS in expr: # exact match filter
                key, value = expr.split(FILTER_SEPARATOR_EQUALS, 1)
                filter = {
                    "type": FILTER_SEPARATOR_EQUALS,
                    "value": value.strip()
                }
                filters[key.strip()] = filter
            elif FILTER_SEPARATOR_NOT_EQUALS in expr: # not equals filter
                key, value = expr.split(FILTER_SEPARATOR_NOT_EQUALS, 1)
                filter = {
                    "type": FILTER_SEPARATOR_NOT_EQUALS,
                    "value": value.strip()
                }
                filters[key.strip()] = filter
            elif FILTER_SEPARATOR_LESS_THAN in expr: # less than filter
                key, value = expr.split(FILTER_SEPARATOR_LESS_THAN, 1)
                filter = {
                    "type": FILTER_SEPARATOR_LESS_THAN,
                    "value": value.strip()
                }
                filters[key.strip()] = filter
            elif FILTER_SEPARATOR_GREATER_THAN in expr: # greater than filter
                key, value = expr.split(FILTER_SEPARATOR_GREATER_THAN, 1)
                filter = {
                    "type": FILTER_SEPARATOR_GREATER_THAN,
                    "value": value.strip()
                }
                filters[key.strip()] = filter
            elif FILTER_SEPARATOR_LESS_THAN_OR_EQUALS in expr: # less than or equals filter
                key, value = expr.split(FILTER_SEPARATOR_LESS_THAN_OR_EQUALS, 1)
                filter = {
                    "type": FILTER_SEPARATOR_LESS_THAN_OR_EQUALS,
                    "value": value.strip()
                }
                filters[key.strip()] = filter
            elif FILTER_SEPARATOR_GREATER_THAN_OR_EQUALS in expr: # greater than or equals filter
                key, value = expr.split(FILTER_SEPARATOR_GREATER_THAN_OR_EQUALS, 1)
                filter = {
                    "type": FILTER_SEPARATOR_GREATER_THAN_OR_EQUALS,
                    "value": value.strip()
                }
                filters[key.strip()] = filter
            elif FILTER_SEPARATOR_CONTAINS in expr: # contains filter
                key, value = expr.split(FILTER_SEPARATOR_CONTAINS, 1)
                filter = {
                    "type": FILTER_SEPARATOR_CONTAINS,
                    "value": value.strip()
                }
                filters[key.strip()] = filter
            elif FILTER_SEPARATOR_NOT_CONTAINS in expr: # not contains filter
                key, value = expr.split(FILTER_SEPARATOR_NOT_CONTAINS, 1)
                filter = {
                    "type": FILTER_SEPARATOR_NOT_CONTAINS,
                    "value": value.strip()
                }
                filters[key.strip()] = filter
            elif FILTER_SEPARATOR_STARTS_WITH in expr: # starts with filter
                key, value = expr.split(FILTER_SEPARATOR_STARTS_WITH, 1)
                filter = {
                    "type": FILTER_SEPARATOR_STARTS_WITH,
                    "value": value.strip()
                }
                filters[key.strip()] = filter
            elif FILTER_SEPARATOR_ENDS_WITH in expr: # ends with filter
                key, value = expr.split(FILTER_SEPARATOR_ENDS_WITH, 1)
                filter = {
                    "type": FILTER_SEPARATOR_ENDS_WITH,
                    "value": value.strip()
                }
                filters[key.strip()] = filter
        return filters

    def _filter_columns(self, item) -> list:
        return [item.get(col, "") for col in self.columns]

    def apply_filters(self) -> list[dict]:
        filtered_data = []

        if not self.filter_rules:
            for item in self.data:
                row = self._filter_columns(item)
                filtered_data.append(row)
            return filtered_data

        for item in self.data:
            keys = item.keys()
            if all(key in keys for key in self.filter_rules.keys()):
                match = False
                for key, filter in self.filter_rules.items():
                    value = str(item.get(key, ""))
                    if filter["type"] == FILTER_SEPARATOR_REGEX:
                        if filter["value"].search(value):
                            match = True
                            break
                    elif filter["type"] == FILTER_SEPARATOR_EQUALS:
                        if value == filter["value"]:
                            match = True
                            break
                    elif filter["type"] == FILTER_SEPARATOR_NOT_EQUALS:
                        if value != filter["value"]:
                            match = True
                            break
                    elif filter["type"] == FILTER_SEPARATOR_LESS_THAN:
                        if float(value) < float(filter["value"]):
                            match = True
                            break
                    elif filter["type"] == FILTER_SEPARATOR_GREATER_THAN:
                        if float(value) > float(filter["value"]):
                            match = True
                            break
                    elif filter["type"] == FILTER_SEPARATOR_LESS_THAN_OR_EQUALS:
                        if float(value) <= float(filter["value"]):
                            match = True
                            break
                    elif filter["type"] == FILTER_SEPARATOR_GREATER_THAN_OR_EQUALS:
                        if float(value) >= float(filter["value"]):
                            match = True
                            break
                    elif filter["type"] == FILTER_SEPARATOR_CONTAINS:
                        if filter["value"] in value:
                            match = True
                            break
                    elif filter["type"] == FILTER_SEPARATOR_NOT_CONTAINS:
                        if filter["value"] not in value:
                            match = True
                            break
                    elif filter["type"] == FILTER_SEPARATOR_STARTS_WITH:
                        if value.startswith(filter["value"]):
                            match = True
                            break
                    elif filter["type"] == FILTER_SEPARATOR_ENDS_WITH:
                        if value.endswith(filter["value"]):
                            match = True
                            break
                if match:
                    row = self._filter_columns(item)
                    filtered_data.append(row)
        return filtered_data
