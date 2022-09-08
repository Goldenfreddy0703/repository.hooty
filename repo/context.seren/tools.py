import json
import sys

try:
    # Try to get Python 3 versions
    from urllib.parse import (
        parse_qsl,
        urlencode,
        quote_plus,
        parse_qs,
        quote,
        unquote,
        urlparse,
        urlunparse,
        urljoin,
    )
except ImportError:
    # Fall back on future.backports to ensure we get unicode compatible PY3 versions in PY2
    from future.backports.urllib.parse import (
        parse_qsl,
        urlencode,
        quote_plus,
        parse_qs,
        quote,
        unquote,
        urlparse,
        urlunparse,
        urljoin,
    )


def get_current_list_item():
    """
    Get the currently selected list item

    :return: The list item
    """
    return sys.listitem  # pylint: disable=no-member


def get_current_list_item_path():
    """
    Get the currently selected list item's path

    :return: The path of the list item
    :rtype: str|unicode
    """
    item = get_current_list_item()
    if item:
        return item.getPath()
    return None


def get_current_list_item_action_args():
    """
    Get the currently selected list item's action_args

    :return: The action_args of the list item
    :rtype: dict
    """
    path = get_current_list_item_path()
    if path:
        return get_action_args(path)
    return {}


def get_query_params(url):
    """
    Get the query parameters from a URL

    :param url: The URL to parse the query parameters from
    :return: A dictionary of query parameters
    :rtype: dict
    """
    query_string = urlparse(url).query
    if query_string:
        return dict(parse_qsl(query_string))
    return {}


def get_action_args(url):
    """
    Get the action_args parameter from a URL string as a dict

    :param url: The URL to parse action_args from
    :type url: str|unicode
    :return: The decoded and parsed action_args
    :rtype: dict
    """
    query_parameters = get_query_params(url)
    if query_parameters:
        action_arg_str = query_parameters.get("action_args")
        if action_arg_str:
            try:
                action_args = json.loads(unquote(action_arg_str))
                if action_args and isinstance(action_args, dict):
                    return action_args
            except json.JSONDecodeError:
                pass
    return {}


def url_quoted_action_args(action_args):
    """
    Returns the action_args json dumped and url quoted

    :param action_args: The action_args to dump and url quote
    :type action_args: dict
    :return: The encoded action_args string value
    :rtype: str|unicode
    """
    return quote(json.dumps(action_args))


def action_replace(url, action_map):
    """
    Replace the action parameter value in a URL based on a defined dictionary mapping of values

    :param url: The url to replace the action parameter value in
    :type url: str|unicode
    :param action_map: A dictionary mapping of the action URL parameter values to replacement values
    :type action_map: dict
    :return: The modified URL or the original URL if the URL does not have the action parameter or
             if the action parameter value is not found in the action_map
    :rtype: str|unicode
    """
    if not action_map or not isinstance(action_map, dict):
        return url

    query_parameters = get_query_params(url)
    if query_parameters:
        action = query_parameters.get("action")
        if action:
            replacement = action_map.get(action)
            if replacement:
                return update_query_params(url, {"action": replacement})
    return url


def pop_query_param(url, param):
    """
    Safely remove a query parameter from a url handling encoding and decoding of parameters

    :param url: The url to remove the query parameter from
    :type url: str|unicode
    :param param: The paramter to remove from the query string in the url
    :type url: str|unicode
    :return: The modified URL or the original URL if the param provided does not exist
    :rtype: str|unicode
    """
    if not url or not param:
        return url

    query_parameters = get_query_params(url)
    if query_parameters:
        popped = query_parameters.pop(param, None)
        if popped is not None:
            parsed_url_parts = list(urlparse(url))
            parsed_url_parts[4] = str(urlencode(query_parameters))
            return urlunparse(parsed_url_parts)
    return url


def update_query_params(url, params):
    """
    Safely update query parameters in a url handling encoding and decoding of parameters
    Parameters already existing will have their values updated.  New values will be added.
    If a query string did not exist in the url, a query string will be added

    :param url: The url to remove the query parameter from
    :type url: str|unicode
    :param params: A dictionary of parameters and their associated values
    :type params: dict
    :return: The modified URL or the original URL if the params provided are invalid
    :rtype: str|unicode
    """
    if not url or not params or not isinstance(params, dict):
        return url
    query_parameters = get_query_params(url)
    query_parameters.update(params)
    parsed_url_parts = list(urlparse(url))
    parsed_url_parts[4] = str(urlencode(query_parameters))
    return urlunparse(parsed_url_parts)
