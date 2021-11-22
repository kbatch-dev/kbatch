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
        if field not in d and field in model.attribute_map:
            # node_affinity -> nodeAffinity
            field = model.attribute_map[field]
        value = d.get(field, None)  # is this a good default?
        if field == "containers" and value is None:
            # evidently that's not a good default for V1PodSpec at least.
            value = []
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

        # rewrite
        reverse_map = {v: k for k, v in model.attribute_map.items()}
        parsed = {reverse_map.get(k, k): v for k, v in parsed.items()}

    return model(**parsed)


def validate_namespace(d: kubernetes.client.models.V1Job):
    pass


def merge_json_objects(a, b):
    """Merge two JSON objects recursively.
    - If a dict, keys are merged, preferring ``b``'s values
    - If a list, values from ``b`` are appended to ``a``
    Copying is minimized. No input collection will be mutated, but a deep copy
    is not performed.
    Parameters
    ----------
    a, b : dict
        JSON objects to be merged.
    Returns
    -------
    merged : dict
    """
    # see https://github.com/dask/dask-gateway/blob/7d1659db8b2122d1a861ea820a459fd045fc3f02/
    # dask-gateway-server/dask_gateway_server/backends/kubernetes/utils.py#L220
    if b:
        # Use a shallow copy here to avoid needlessly copying
        a = a.copy()
        for key, b_val in b.items():
            if key in a:
                a_val = a[key]
                if isinstance(a_val, dict) and isinstance(b_val, dict):
                    a[key] = merge_json_objects(a_val, b_val)
                elif isinstance(a_val, list) and isinstance(b_val, list):
                    a[key] = a_val + b_val
                else:
                    a[key] = b_val
            else:
                a[key] = b_val
    return a


def remove_nulls(d):
    remove = set()
    for k, v in d.items():
        if v is None or v == [] or v == {}:
            remove.add(k)
        elif isinstance(v, dict):
            remove_nulls(v)
    for k in remove:
        del d[k]
