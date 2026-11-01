REDACTED = "**redacted**"

redacted_fields = ["email", "password"]


def dict_redact_fields_1(i_dict):
    for k, v in i_dict.items():
        if isinstance(v, dict):
            i_dict[k] = dict_redact_fields_1(v)
        elif isinstance(v, list):
            i_dict[k] = [dict_redact_fields_1(i) for i in v]
    for field in redacted_fields:
        if field in i_dict:
            i_dict[field] = REDACTED
    return i_dict


def dict_redact_fields(i_dict):
    if i_dict is None:
        return None
    mydict = {}
    for k, v in i_dict.items():
        if k in redacted_fields:
            mydict[k] = REDACTED
        else:
            mydict[k] = v
    return mydict


def redact_email(email: str) -> str:
    red = ""
    for i in range(len(email)):
        if i > 4 and i % 3 == 0 and email[i] != "@" and email[i] != ".":
            red = red + "_"
        else:
            red = red + email[i]
    return red
