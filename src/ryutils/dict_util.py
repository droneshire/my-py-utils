import typing as T


def get_typeddict_keys(typeddict_type: T.Type) -> T.Set[str]:
    return set(T.get_type_hints(typeddict_type))


def populate_typeddict_recursive(data: T.Dict[str, T.Any], data_type: T.Any) -> T.Any:
    required_keys = get_typeddict_keys(data_type)
    keys = set(data.keys())

    for key in required_keys:
        if key not in keys:
            return None

        if isinstance(data[key], dict):
            if populate_typeddict_recursive(data[key], data_type.__annotations__[key]) is None:
                return None

    return data_type(**data)


def check_dict_keys_recursive(
    dict1: T.Dict[T.Any, T.Any], dict2: T.Dict[T.Any, T.Any]
) -> T.List[T.Any]:
    missing_keys = []
    for key in dict1.keys():
        if key not in dict2.keys():
            missing_keys.append(key)
        elif isinstance(dict1[key], dict):
            missing_keys += check_dict_keys_recursive(dict1[key], dict2[key])
    return missing_keys


def patch_missing_keys_recursive(
    dict1: T.Dict[T.Any, T.Any], dict2: T.Dict[T.Any, T.Any]
) -> T.Dict[T.Any, T.Any]:
    for key in dict1.keys():
        if key not in dict2.keys():
            dict2[key] = dict1[key]
        elif isinstance(dict1[key], dict):
            patch_missing_keys_recursive(dict1[key], dict2[key])
    return dict2


def safe_get(dictionary: T.Dict[T.Any, T.Any], keys: T.List[T.Any], default: T.Any = None) -> T.Any:
    if default is None:
        default = {}

    for key in keys:
        dictionary = dictionary.get(key, {})
    return dictionary if dictionary else default


def flatten_dict(
    dictionary: T.Dict[T.Any, T.Any], parent_key: str = "", sep: str = "."
) -> T.Dict[T.Any, T.Any]:
    items = {}
    for key, value in dictionary.items():
        new_key = f"{parent_key}{sep}{key}" if parent_key else key
        if isinstance(value, dict):
            items.update(flatten_dict(value, new_key, sep=sep))
        else:
            items[new_key] = value
    return items


def find_in_nested_dict(data: T.Any, key: str) -> T.Any:
    """Helper function to search for a key in a nested dictionary/list structure."""
    if isinstance(data, dict):
        for ikey, value in data.items():
            if ikey == key:
                return value
            if isinstance(value, (dict, list)):
                result = find_in_nested_dict(value, key)
                if result is not None:
                    return result
    if isinstance(data, list):
        for item in data:
            result = find_in_nested_dict(item, key)
            if result is not None:
                return result
    return None
