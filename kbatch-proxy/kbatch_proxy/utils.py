import re
import kubernetes.client.models

basic_types = {
    "str",
    # TODO: figure out if we have to parse these
    "dict(str, str)",
    "datetime",
    "int",
    "list[str]",
}
xpr = re.compile(r"\w+\[(\w+)\]")


def parse(d, model):
    """
    Parse a dictionary of JSON types into their Kubernetes types.
    """
    parsed = {}

    for field, type_ in model.openapi_types.items():
        value = d[field]
        if value is None:
            parsed[field] = value
        elif type_ in basic_types:
            parsed[field] = d[field]
        elif type_.startswith("list["):
            m = xpr.match(type_)
            parsed[field] = [
                parse(v, getattr(kubernetes.client, m.group(1))) for v in value
            ]
        elif type_.startswith("dict["):
            raise NotImplementedError("TODO")
        else:
            parsed[field] = parse(d[field], getattr(kubernetes.client, type_))
    return model(**parsed)


def validate_namespace(d: kubernetes.client.models.V1Job):
    pass
